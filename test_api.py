#!/usr/bin/env python3
"""
Simple API test script for MCP Platform
"""
import requests
import json

BASE_URL = "http://localhost:5000"

def test_health_check():
    """Test the health check endpoint"""
    print("Testing health check...")
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print("-" * 50)

def test_job_search():
    """Test job search endpoint"""
    print("Testing job search...")
    payload = {
        "query": "Find me software engineer jobs in San Francisco",
        "max_leads": 2,
        "hours_old": 24,
        "enforce_salary": True,
        "auto_generate_messages": True
    }
    
    response = requests.post(f"{BASE_URL}/search-jobs", json=payload)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Found {len(data['leads'])} leads from {data['jobs_found']} jobs")
        
        # Show first lead if available
        if data['leads']:
            lead = data['leads'][0]
            print(f"Sample lead: {lead['name']} ({lead['title']}) at {lead['company']}")
            if lead['message']:
                print(f"Generated message preview: {lead['message'][:100]}...")
    else:
        print(f"Error: {response.text}")
    
    print("-" * 50)

def test_message_generation():
    """Test message generation endpoint"""
    print("Testing message generation...")
    payload = {
        "job_title": "Senior Software Engineer",
        "company": "TechCorp",
        "contact_title": "VP of Engineering", 
        "job_url": "https://techcorp.com/jobs/123",
        "tone": "professional"
    }
    
    response = requests.post(f"{BASE_URL}/generate-message", json=payload)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Subject: {data['subject_line']}")
        print(f"Message: {data['message']}")
    else:
        print(f"Error: {response.text}")
    
    print("-" * 50)

def test_memory_stats():
    """Test memory stats endpoint"""
    print("Testing memory stats...")
    response = requests.get(f"{BASE_URL}/memory-stats")
    print(f"Status: {response.status_code}")
    print(f"Memory stats: {json.dumps(response.json(), indent=2)}")
    print("-" * 50)

if __name__ == "__main__":
    print("🎯 MCP API Test Suite")
    print("=" * 50)
    
    try:
        test_health_check()
        test_job_search()
        test_message_generation()
        test_memory_stats()
        print("✅ All tests completed!")
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API. Make sure the server is running on port 5000.")
    except Exception as e:
        print(f"❌ Test failed: {e}")