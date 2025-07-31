#!/bin/bash

# Debug: Check what's available
echo "=== Environment Debug ==="
echo "Current directory: $(pwd)"
echo "Python3 available: $(which python3)"
echo "Python available: $(which python)"
echo "Pip available: $(which pip)"
echo "Pip3 available: $(which pip3)"

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