#!/bin/bash

set -e

echo "Setting up environment..."

module load python/3.11.9

if [ ! -d ".venv" ]; then
    echo "Creating venv..."
    python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"

echo ""
echo "Done! Now run:"
echo "  source .venv/bin/activate"
echo "  pytest"
