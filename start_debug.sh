#!/bin/bash

echo "=== RUNTIME DEBUG ==="
echo "Current directory: $(pwd)"
echo "Directory contents:"
ls -la

echo ""
echo "=== PATH ==="
echo $PATH

echo ""
echo "=== PYTHON SEARCH ==="
echo "Looking for Python in PATH..."
which python3 2>/dev/null || echo "python3 not found in PATH"
which python 2>/dev/null || echo "python not found in PATH"

echo ""
echo "=== NIX ENVIRONMENT ==="
echo "NIX_PATH: $NIX_PATH"
echo "NIX_PROFILES: $NIX_PROFILES"

echo ""
echo "=== TRYING DIFFERENT PYTHON COMMANDS ==="
echo "Trying: /nix/store/*/bin/python3"
find /nix/store -name "python3" -type f 2>/dev/null | head -5

echo ""
echo "=== TRYING TO START WITH ABSOLUTE PATH ==="
PYTHON_PATH=$(find /nix/store -name "python3" -type f 2>/dev/null | head -1)
if [ -n "$PYTHON_PATH" ]; then
    echo "Found Python at: $PYTHON_PATH"
    echo "Trying to start server..."
    $PYTHON_PATH -m uvicorn api:app --host 0.0.0.0 --port $PORT
else
    echo "No Python found in /nix/store"
    exit 1
fi 