#!/usr/bin/env python3

import subprocess
import sys
import os

def install_dependencies():
    """Install dependencies if needed"""
    try:
        import fastapi
        import uvicorn
        print("✅ Dependencies already available")
        return True
    except ImportError:
        print("⚠️ Dependencies not found, trying to install...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
            print("✅ Dependencies installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install dependencies: {e}")
            return False

def start_server():
    """Start the uvicorn server"""
    try:
        import uvicorn
        from api import app
        
        port = int(os.environ.get("PORT", 8080))
        print(f"🚀 Starting server on port {port}")
        
        uvicorn.run(app, host="0.0.0.0", port=port)
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("=== Coogi Server Startup ===")
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version}")
    
    if install_dependencies():
        start_server()
    else:
        print("❌ Cannot start server due to missing dependencies")
        sys.exit(1) 