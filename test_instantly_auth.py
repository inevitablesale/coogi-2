#!/usr/bin/env python3
"""
Test Instantly API authentication and basic connectivity
"""

import os
import sys
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_instantly_auth():
    """Test Instantly API authentication"""
    
    # Get API key from environment
    api_key = os.getenv('INSTANTLY_API_KEY')
    if not api_key:
        print("❌ No INSTANTLY_API_KEY found in environment")
        return False
    
    base_url = "https://api.instantly.ai"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    print("🧪 Testing Instantly API authentication...")
    print(f"🔑 API Key: {api_key[:20]}...")
    print(f"🌐 Base URL: {base_url}")
    
    # Test 1: Get lead lists (should work if authenticated)
    print("\n1️⃣ Testing GET /api/v2/lead-lists...")
    try:
        response = requests.get(f"{base_url}/api/v2/lead-lists", headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Found {len(data)} lead lists")
            return True
        else:
            print(f"❌ Failed: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_instantly_auth()
    if success:
        print("\n🎯 Authentication test passed!")
    else:
        print("\n💥 Authentication test failed!")
        sys.exit(1) 