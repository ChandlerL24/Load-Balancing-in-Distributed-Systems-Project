# Load Balancing Simulation

*MPCS 56430 Final Project*

## What This Is

Imagine you've got a website and a pile of incoming traffic. You don't run that
traffic through a single machine — you spread it across a bunch of servers. The
piece that decides *which* server each request goes to is called a **load
balancer**, and the rule it follows is its **strategy**.

This project is a little laboratory for those strategies. It spins up a virtual
cluster of servers, throws a realistic stream of requests at them, and measures
how well three different load balancing approaches hold up. The goal is to see —
with real numbers instead of hand-waving — which strategy keeps response times
low, keeps the servers evenly busy, and drops the fewest requests.

The three strategies we compare are:

- **Round-Robin** — just go down the line: server 1, server 2, server 3, back to
  1, and so on. Simple and fair, but it ignores how busy each server actually is.
- **Random** — pick a server at random for every request. Surprisingly decent in
  practice because the randomness tends to even out over time.
- **Least Connections** — look at how many requests each server is currently
  juggling and send the new one to whoever's least busy. The "smart" option,
  since it reacts to the actual state of the cluster.

(There's also a *Weighted Round-Robin* strategy in the code for servers with
different speeds, but the main comparison focuses on the three above.)

## How The Simulation Actually Works

Under the hood this is a **discrete-event simulation**. Rather than ticking
forward one tiny time-step at a time (which would be slow and wasteful), the
simulation jumps from one interesting *event* to the next. There are three kinds
of events:

1. **Arrival** — a new request shows up.
2. **Completion** — a server finishes the request it was working on.
3. **Snapshot** — a periodic checkpoint where we record how long every server's
   queue is, so we can chart how the cluster behaves over time.

All upcoming events live in a priority queue (a heap) ordered by time, so the
engine always processes whatever happens next. Here's the life of a single
request:

1. **It arrives.** Requests don't arrive on a neat schedule — they come in
   following a **Poisson process** at rate `λ` (lambda), which is the standard
   way to model random, bursty traffic like real web requests. The gap between
   arrivals is drawn from an exponential distribution.
2. **The load balancer picks a server.** This is where the chosen strategy does
   its thing. If every server's queue is full (when you set a queue limit), the
   request gets **rejected** and we count it.
3. **It waits in line, then gets processed.** Each server handles one request at
   a time. How long the work takes is drawn from an exponential distribution
   with service rate `μ` (mu), so some requests are quick and some are slow.
4. **It completes.** We record its **response time** (how long from arrival to
   finish) and **waiting time** (how long it sat in the queue before work
   started), then the server grabs the next request in line.

A useful number to keep in mind is the **system load**, written `ρ` (rho), which
is `λ / (number of servers × μ)`. If `ρ` is well under 1, the cluster keeps up
comfortably. As it creeps toward 1, queues grow and response times blow up. Past
1, the system is fundamentally overloaded — requests arrive faster than the
servers can ever clear them — and the simulation will warn you about it.

## What Gets Measured

After a run, for each strategy you get:

- **Throughput** — completed requests per unit of time.
- **Response time** — average, plus the p50 / p95 / p99 percentiles (the tail
  matters: p99 tells you about the slowest 1% of requests).
- **Waiting time** — how long requests sit in queues on average.
- **Server utilization** — how busy each individual server was, and how evenly
  the load was spread. A *low spread* across servers means good balancing.
- **Rejections** — how many requests got turned away (only relevant with a
  queue capacity set).

The simulation prints a tidy summary to the terminal and writes a
`results/summary.txt` file. There's also a visualization module that turns the
results into charts — response-time bars, utilization breakdowns, throughput
comparisons, distribution histograms, and a combined dashboard.

## Project Layout

```
src/load_balancing/
    server.py         - the Server and Request classes (queues, timing, state)
    load_balancer.py  - the load balancing strategies live here
    simulation.py     - the discrete-event engine + CLI entry point
    metrics.py        - collects stats during a run and computes the summary
    visualization.py  - matplotlib charts of the results

tests/
    test_simulation.py - sanity checks for the simulation

scripts/
    setup_env.sh           - one-shot environment setup (handy on a cluster)
    run_simulation.sbatch  - Slurm batch job for running on Midway

results/                   - where summaries and plots get written
```

The flow ties together like this: `simulation.py` is the conductor. It creates
`Server` objects, hands them to one of the balancers from `load_balancer.py`,
runs the event loop, and feeds everything it sees into the `MetricsCollector`
from `metrics.py`. When the run ends, the collector produces a
`SimulationMetrics` object, which `visualization.py` can turn into pictures.

## Setup

You'll need Python 3.10 or newer.

```bash
python3 --version

# On Midway, load the module first:
module load python/3.11

# Create and activate a virtual environment, then install everything:
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"

# Confirm it works:
pytest
```

There's also a helper script that does the cluster setup for you:

```bash
bash scripts/setup_env.sh
```

## Running It

### Locally

```bash
python -m load_balancing.simulation
```

You can tweak any of the parameters from the command line:

```bash
python -m load_balancing.simulation \
    --num-servers 5 \
    --arrival-rate 10.0 \
    --service-rate 3.0 \
    --duration 1000 \
    --queue-capacity -1 \
    --seed 42 \
    --output-dir results
```

| Flag | What it controls | Default |
|------|------------------|---------|
| `--num-servers` | how many servers in the cluster | 5 |
| `--arrival-rate` | λ, how fast requests come in | 10.0 |
| `--service-rate` | μ, how fast a server works | 3.0 |
| `--duration` | how long (in sim time) to run | 1000 |
| `--queue-capacity` | max queue per server (`-1` = unlimited) | -1 |
| `--seed` | random seed for reproducible runs | none |
| `--output-dir` | where to write results | results |

### On Midway (interactive)

```bash
sinteractive --partition=caslake --time=01:00:00 --mem=4G
module load python/3.11
source .venv/bin/activate
python -m load_balancing.simulation
```

### On Midway (batch)

```bash
sbatch scripts/run_simulation.sbatch
squeue -u $USER   # check on the job
```

## Handy Commands

```bash
pytest                              # run the tests
pytest -v                           # ...with more detail
python -m load_balancing.simulation # run the simulation
ruff check src tests                # lint the code
ruff check src tests --fix          # auto-fix what it can
```

## References

- Tanenbaum & Van Steen — *Distributed Systems*
- Mitzenmacher (2001) — *The Power of Two Choices in Randomized Load Balancing*
