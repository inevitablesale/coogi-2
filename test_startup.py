#!/usr/bin/env python3
"""
Simple startup test to check if the app can import without external calls
"""

import os
import sys

# Set environment variables for testing
os.environ["OPENAI_API_KEY"] = "test"
os.environ["RAPIDAPI_KEY"] = "test"
os.environ["HUNTER_API_KEY"] = "test"
os.environ["INSTANTLY_API_KEY"] = "test"
os.environ["CLEAROUT_API_KEY"] = "test"

def test_basic_imports():
    """Test basic imports without external calls"""
    try:
        print("🧪 Testing basic imports...")
        
        # Test utils imports
        from utils.job_scraper import JobScraper
        print("✅ JobScraper imported")
        
        from utils.contact_finder import ContactFinder
        print("✅ ContactFinder imported")
        
        from utils.email_generator import EmailGenerator
        print("✅ EmailGenerator imported")
        
        from utils.memory_manager import MemoryManager
        print("✅ MemoryManager imported")
        
        from utils.contract_analyzer import ContractAnalyzer
        print("✅ ContractAnalyzer imported")
        
        from utils.instantly_manager import InstantlyManager
        print("✅ InstantlyManager imported")
        
        print("🎉 All basic imports successful!")
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_app_creation():
    """Test if the FastAPI app can be created"""
    try:
        print("\n🧪 Testing FastAPI app creation...")
        
        # Import the app
        from api import app
        print("✅ FastAPI app imported")
        
        # Test basic app properties
        print(f"✅ App title: {app.title}")
        print(f"✅ App version: {app.version}")
        
        print("🎉 App creation successful!")
        return True
        
    except Exception as e:
        print(f"❌ App creation failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting MindGlimpse Startup Test...\n")
    
    # Test 1: Basic imports
    import_test = test_basic_imports()
    
    # Test 2: App creation
    app_test = test_app_creation()
    
    print(f"\n📊 Test Results:")
    print(f"   Basic Imports: {'✅ PASS' if import_test else '❌ FAIL'}")
    print(f"   App Creation: {'✅ PASS' if app_test else '❌ FAIL'}")
    
    if import_test and app_test:
        print("\n🎉 All startup tests passed! App should deploy successfully.")
    else:
        print("\n⚠️  Some startup tests failed. Check the errors above.") 