#!/bin/bash
#SBATCH --job-name=load_balancing
#SBATCH --output=results/simulation_%j.out
#SBATCH --error=results/simulation_%j.err
#SBATCH --partition=caslake
#SBATCH --account=mpcs56430
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=02:00:00

module load python/3.11.9
source .venv/bin/activate

echo "Starting sim - $(date)"
echo "Node: $(hostname), Job: $SLURM_JOB_ID"
echo ""

python -m load_balancing.simulation \
    --num-servers 5 \
    --arrival-rate 10.0 \
    --service-rate 3.0 \
    --duration 1000 \
    --output-dir results

echo ""
echo "Done - $(date)"
