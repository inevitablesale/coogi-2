#!/bin/bash

# Debug: Check what's available
echo "=== Environment Debug ==="
echo "Current directory: $(pwd)"
echo "Python3 available: $(which python3)"
echo "Python available: $(which python)"
echo "Pip available: $(which pip)"
echo "Pip3 available: $(which pip3)"

# Try to install dependencies if needed
if command -v pip3 &> /dev/null; then
    echo "Installing dependencies with pip3..."
    pip3 install -r requirements.txt
elif command -v pip &> /dev/null; then
    echo "Installing dependencies with pip..."
    pip install -r requirements.txt
else
    echo "No pip found!"
fi

# Start the server
echo "Starting server..."
if command -v python3 &> /dev/null; then
    echo "Using python3"
    python3 -m uvicorn api:app --host 0.0.0.0 --port $PORT
elif command -v python &> /dev/null; then
    echo "Using python"
    python -m uvicorn api:app --host 0.0.0.0 --port $PORT
else
    echo "No Python found!"
    exit 1
fi 