#!/usr/bin/env python3

import sys
import os
import subprocess

print("=== MINIMAL PYTHON TEST ===")
print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")
print(f"Environment variables:")
for key, value in os.environ.items():
    if 'PATH' in key or 'PYTHON' in key or 'NIX' in key:
        print(f"  {key}: {value}")

print("\n=== TESTING BASIC IMPORTS ===")
try:
    import os
    print("✅ os module works")
except Exception as e:
    print(f"❌ os module failed: {e}")

try:
    import sys
    print("✅ sys module works")
except Exception as e:
    print(f"❌ sys module failed: {e}")

print("\n=== TESTING SUBPROCESS ===")
try:
    result = subprocess.run([sys.executable, "--version"], capture_output=True, text=True)
    print(f"✅ Python subprocess works: {result.stdout.strip()}")
except Exception as e:
    print(f"❌ Python subprocess failed: {e}")

print("\n=== TESTING PIP ===")
try:
    result = subprocess.run([sys.executable, "-m", "pip", "--version"], capture_output=True, text=True)
    print(f"✅ pip works: {result.stdout.strip()}")
except Exception as e:
    print(f"❌ pip failed: {e}")

print("\n=== TESTING UVICORN ===")
try:
    import uvicorn
    print("✅ uvicorn import works")
except ImportError:
    print("❌ uvicorn not available")
except Exception as e:
    print(f"❌ uvicorn import failed: {e}")

print("\n=== TESTING FASTAPI ===")
try:
    import fastapi
    print("✅ fastapi import works")
except ImportError:
    print("❌ fastapi not available")
except Exception as e:
    print(f"❌ fastapi import failed: {e}")

print("\n=== TESTING API IMPORT ===")
try:
    from api import app
    print("✅ api import works")
except ImportError as e:
    print(f"❌ api import failed: {e}")
except Exception as e:
    print(f"❌ api import failed: {e}")

print("\n=== MINIMAL TEST COMPLETE ===") 