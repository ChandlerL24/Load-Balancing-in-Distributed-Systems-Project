"""
Simulation engine for load balancing.
"""

import argparse
import heapq
import os
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict, Any
import numpy as np

from load_balancing.server import Server, Request
from load_balancing.load_balancer import (
    LoadBalancer,
    RoundRobinBalancer,
    RandomBalancer,
    LeastConnectionsBalancer,
)
from load_balancing.metrics import MetricsCollector, SimulationMetrics, print_metrics_summary


class EventType(Enum):
    ARRIVAL = 1
    COMPLETION = 2
    SNAPSHOT = 3


@dataclass(order=True)
class Event:
    """Simulation event - sorted by time."""
    time: float
    event_type: EventType
    server_id: Optional[int] = None
    request: Optional[Request] = None
    
    def __post_init__(self):
        self.request = self.request  # exclude from ordering


class Simulation:
    """
    Runs a discrete-event sim of servers handling requests.
    Uses Poisson arrivals and routes via the chosen load balancer.
    """
    
    def __init__(
        self,
        num_servers: int = 5,
        arrival_rate: float = 10.0,
        service_rate: float = 3.0,
        duration: float = 1000.0,
        queue_capacity: int = -1,
        seed: Optional[int] = None,
    ):
        self.num_servers = num_servers
        self.arrival_rate = arrival_rate
        self.service_rate = service_rate
        self.duration = duration
        self.queue_capacity = queue_capacity
        
        self._seed = seed
        self._rng = np.random.default_rng(seed)
        self._request_counter = 0
        
        self.servers = [
            Server(id=i, service_rate=service_rate, queue_capacity=queue_capacity)
            for i in range(num_servers)
        ]
        
        self.metrics = MetricsCollector(self.servers)
        self._event_queue: List[Event] = []
        self._current_time = 0.0
        self.load_balancer: Optional[LoadBalancer] = None
    
    def set_load_balancer(self, balancer: LoadBalancer):
        self.load_balancer = balancer
    
    def _generate_interarrival_time(self) -> float:
        return self._rng.exponential(1.0 / self.arrival_rate)
    
    def _generate_service_time(self) -> float:
        return self._rng.exponential(1.0 / self.service_rate)
    
    def _create_request(self, arrival_time: float) -> Request:
        self._request_counter += 1
        return Request(
            id=self._request_counter,
            arrival_time=arrival_time,
            service_time=self._generate_service_time(),
        )
    
    def _schedule_event(self, event: Event):
        heapq.heappush(self._event_queue, event)
    
    def _schedule_arrival(self, time: float):
        self._schedule_event(Event(time=time, event_type=EventType.ARRIVAL))
    
    def _schedule_completion(self, server: Server, request: Request):
        self._schedule_event(Event(
            time=server.busy_until,
            event_type=EventType.COMPLETION,
            server_id=server.id,
            request=request,
        ))
    
    def _schedule_snapshot(self, time: float):
        self._schedule_event(Event(time=time, event_type=EventType.SNAPSHOT))
    
    def _handle_arrival(self, event: Event):
        request = self._create_request(event.time)
        self.metrics.record_generation()
        
        if self.load_balancer is None:
            raise RuntimeError("Need to set a load balancer first")
        
        if not self.load_balancer.route_request(request):
            self.metrics.record_rejection()
        else:
            server = self.servers[request.server_id]
            if not server.is_busy(self._current_time):
                started = server.process_next(self._current_time)
                if started:
                    self._schedule_completion(server, started)
        
        next_arrival = self._current_time + self._generate_interarrival_time()
        if next_arrival < self.duration:
            self._schedule_arrival(next_arrival)
    
    def _handle_completion(self, event: Event):
        server = self.servers[event.server_id]
        
        completed = server.complete_current(self._current_time)
        if completed:
            self.metrics.record_completion(completed)
        
        next_req = server.process_next(self._current_time)
        if next_req:
            self._schedule_completion(server, next_req)
    
    def _handle_snapshot(self, event: Event):
        self.metrics.take_snapshot(self._current_time)
        
        interval = self.duration / 100
        next_snap = self._current_time + interval
        if next_snap < self.duration:
            self._schedule_snapshot(next_snap)
    
    def run(self) -> SimulationMetrics:
        if self.load_balancer is None:
            raise RuntimeError("Need to set a load balancer first")
        
        self._current_time = 0.0
        self._event_queue = []
        self._request_counter = 0
        
        for s in self.servers:
            s.reset()
        self.metrics.reset()
        self.load_balancer.reset()
        
        self._schedule_arrival(self._generate_interarrival_time())
        self._schedule_snapshot(self.duration / 100)
        
        while self._event_queue:
            event = heapq.heappop(self._event_queue)
            
            if event.time > self.duration:
                break
            
            self._current_time = event.time
            
            if event.event_type == EventType.ARRIVAL:
                self._handle_arrival(event)
            elif event.event_type == EventType.COMPLETION:
                self._handle_completion(event)
            elif event.event_type == EventType.SNAPSHOT:
                self._handle_snapshot(event)
        
        return self.metrics.compute_metrics(self.duration)
    
    def reset(self):
        self._current_time = 0.0
        self._event_queue = []
        self._request_counter = 0
        self._rng = np.random.default_rng(self._seed)
        
        for s in self.servers:
            s.reset()
        self.metrics.reset()
        
        if self.load_balancer:
            self.load_balancer.reset()


def run_comparison(
    num_servers: int = 5,
    arrival_rate: float = 10.0,
    service_rate: float = 3.0,
    duration: float = 1000.0,
    queue_capacity: int = -1,
    seed: Optional[int] = None,
) -> Dict[str, SimulationMetrics]:
    """Run all three strategies and compare them."""
    results = {}
    
    strategies = [
        ("Round-Robin", RoundRobinBalancer),
        ("Random", RandomBalancer),
        ("Least-Connections", LeastConnectionsBalancer),
    ]
    
    for name, balancer_cls in strategies:
        print(f"\nRunning {name}...")
        
        sim = Simulation(
            num_servers=num_servers,
            arrival_rate=arrival_rate,
            service_rate=service_rate,
            duration=duration,
            queue_capacity=queue_capacity,
            seed=seed,
        )
        
        if name == "Random":
            balancer = balancer_cls(sim.servers, seed=seed)
        else:
            balancer = balancer_cls(sim.servers)
        
        sim.set_load_balancer(balancer)
        metrics = sim.run()
        results[name] = metrics
        
        print_metrics_summary(metrics, name)
    
    return results


def save_results(
    results: Dict[str, SimulationMetrics],
    output_dir: str,
    params: Dict[str, Any],
):
    """Dump results to a text file."""
    os.makedirs(output_dir, exist_ok=True)
    
    with open(os.path.join(output_dir, "summary.txt"), "w") as f:
        f.write("Load Balancing Results\n")
        f.write("=" * 50 + "\n\n")
        
        f.write("Params:\n")
        for k, v in params.items():
            f.write(f"  {k}: {v}\n")
        f.write("\n")
        
        for name, m in results.items():
            f.write(f"\n{name}:\n")
            f.write(f"  Completed: {m.completed_requests}\n")
            f.write(f"  Rejected: {m.rejected_requests}\n")
            f.write(f"  Throughput: {m.throughput:.2f}\n")
            f.write(f"  Avg response: {m.avg_response_time:.4f}\n")
            f.write(f"  Avg wait: {m.avg_waiting_time:.4f}\n")
            f.write(f"  P95 response: {m.p95_response_time:.4f}\n")
            f.write(f"  Avg util: {np.mean(m.server_utilizations):.2%}\n")
    
    print(f"\nSaved to {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Load balancing sim")
    parser.add_argument("--num-servers", type=int, default=5)
    parser.add_argument("--arrival-rate", type=float, default=10.0)
    parser.add_argument("--service-rate", type=float, default=3.0)
    parser.add_argument("--duration", type=float, default=1000.0)
    parser.add_argument("--queue-capacity", type=int, default=-1)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--output-dir", type=str, default="results")
    
    args = parser.parse_args()
    
    print("Load Balancing Simulation")
    print("=" * 50)
    print(f"Servers: {args.num_servers}")
    print(f"λ = {args.arrival_rate}, μ = {args.service_rate}")
    print(f"Duration: {args.duration}")
    print(f"Queue cap: {'unlimited' if args.queue_capacity == -1 else args.queue_capacity}")
    
    rho = args.arrival_rate / (args.num_servers * args.service_rate)
    print(f"\nSystem load ρ = {rho:.2%}")
    if rho >= 1:
        print("WARNING: overloaded system!")
    
    results = run_comparison(
        num_servers=args.num_servers,
        arrival_rate=args.arrival_rate,
        service_rate=args.service_rate,
        duration=args.duration,
        queue_capacity=args.queue_capacity,
        seed=args.seed,
    )
    
    params = {
        "num_servers": args.num_servers,
        "arrival_rate": args.arrival_rate,
        "service_rate": args.service_rate,
        "duration": args.duration,
        "queue_capacity": args.queue_capacity,
        "seed": args.seed,
    }
    save_results(results, args.output_dir, params)


if __name__ == "__main__":
    main()
