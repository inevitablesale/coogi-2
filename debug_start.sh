#!/bin/bash

echo "=== RAILWAY DEPLOYMENT DEBUG ==="
echo "Timestamp: $(date)"
echo "Current directory: $(pwd)"
echo "Directory contents:"
ls -la

echo ""
echo "=== PYTHON ENVIRONMENT ==="
echo "Python3 path: $(which python3 2>/dev/null || echo 'NOT FOUND')"
echo "Python path: $(which python 2>/dev/null || echo 'NOT FOUND')"
echo "Pip3 path: $(which pip3 2>/dev/null || echo 'NOT FOUND')"
echo "Pip path: $(which pip 2>/dev/null || echo 'NOT FOUND')"

echo ""
echo "=== PYTHON VERSIONS ==="
if command -v python3 &> /dev/null; then
    echo "Python3 version: $(python3 --version 2>&1)"
else
    echo "Python3 not found"
fi

if command -v python &> /dev/null; then
    echo "Python version: $(python --version 2>&1)"
else
    echo "Python not found"
fi

echo ""
echo "=== ENVIRONMENT VARIABLES ==="
echo "PORT: $PORT"
echo "PATH: $PATH"
echo "PYTHONPATH: $PYTHONPATH"

echo ""
echo "=== CHECKING REQUIREMENTS.TXT ==="
if [ -f "requirements.txt" ]; then
    echo "requirements.txt exists"
    echo "Contents:"
    cat requirements.txt
else
    echo "requirements.txt NOT FOUND"
fi

echo ""
echo "=== CHECKING API.PY ==="
if [ -f "api.py" ]; then
    echo "api.py exists"
    echo "First 10 lines:"
    head -10 api.py
else
    echo "api.py NOT FOUND"
fi

echo ""
echo "=== CHECKING RUN.PY ==="
if [ -f "run.py" ]; then
    echo "run.py exists"
    echo "Contents:"
    cat run.py
else
    echo "run.py NOT FOUND"
fi

echo ""
echo "=== TRYING TO INSTALL DEPENDENCIES ==="
if command -v pip3 &> /dev/null; then
    echo "Installing with pip3..."
    pip3 install -r requirements.txt 2>&1
elif command -v pip &> /dev/null; then
    echo "Installing with pip..."
    pip install -r requirements.txt 2>&1
else
    echo "No pip found!"
fi

echo ""
echo "=== CHECKING IF UVICORN IS INSTALLED ==="
if command -v python3 &> /dev/null; then
    echo "Trying: python3 -c 'import uvicorn; print(\"uvicorn found\")'"
    python3 -c "import uvicorn; print('uvicorn found')" 2>&1 || echo "uvicorn import failed"
elif command -v python &> /dev/null; then
    echo "Trying: python -c 'import uvicorn; print(\"uvicorn found\")'"
    python -c "import uvicorn; print('uvicorn found')" 2>&1 || echo "uvicorn import failed"
else
    echo "No Python found!"
fi

echo ""
echo "=== TRYING TO START SERVER ==="
if command -v python3 &> /dev/null; then
    echo "Starting with python3 run.py..."
    python3 run.py 2>&1
elif command -v python &> /dev/null; then
    echo "Starting with python run.py..."
    python run.py 2>&1
else
    echo "No Python found!"
    exit 1
fi 