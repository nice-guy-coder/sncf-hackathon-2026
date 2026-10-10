#!/usr/bin/env bash

set -e

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/Scripts/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Done!"