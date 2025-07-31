#!/usr/bin/env python3
"""
Test script for the proxy system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.job_scraper import JobScraper, ProxyManager
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_proxy_manager():
    """Test the proxy manager"""
    print("🧪 Testing Proxy Manager...")
    
    proxy_manager = ProxyManager()
    
    print(f"📊 Loaded {len(proxy_manager.proxies)} proxies")
    
    # Test getting proxies
    for i in range(5):
        proxy = proxy_manager.get_next_proxy()
        if proxy:
            print(f"🔄 Proxy {i+1}: {list(proxy.values())[0]}")
        else:
            print(f"❌ No proxy available for {i+1}")
    
    return len(proxy_manager.proxies) > 0

def test_jobspy_with_proxies():
    """Test JobSpy API with proxy rotation"""
    print("\n🧪 Testing JobSpy API with proxies...")
    
    job_scraper = JobScraper()
    
    # Test a simple search
    try:
        jobs = job_scraper._call_jobspy_api("software engineer", "New York, NY", hours_old=1)
        print(f"✅ JobSpy API test successful: {len(jobs)} jobs found")
        return True
    except Exception as e:
        print(f"❌ JobSpy API test failed: {e}")
        return False

def test_domain_finding_with_proxies():
    """Test domain finding with proxy rotation"""
    print("\n🧪 Testing domain finding with proxies...")
    
    job_scraper = JobScraper()
    
    # Test domain finding
    test_companies = ["Microsoft", "Apple", "Google"]
    
    for company in test_companies:
        try:
            domain = job_scraper._find_company_domain(company)
            if domain:
                print(f"✅ Found domain for {company}: {domain}")
            else:
                print(f"⚠️  No domain found for {company}")
        except Exception as e:
            print(f"❌ Domain finding failed for {company}: {e}")

if __name__ == "__main__":
    print("🚀 Starting Proxy System Tests...\n")
    
    # Test 1: Proxy Manager
    proxy_test = test_proxy_manager()
    
    # Test 2: JobSpy with proxies
    jobspy_test = test_jobspy_with_proxies()
    
    # Test 3: Domain finding with proxies
    test_domain_finding_with_proxies()
    
    print(f"\n📊 Test Results:")
    print(f"   Proxy Manager: {'✅ PASS' if proxy_test else '❌ FAIL'}")
    print(f"   JobSpy API: {'✅ PASS' if jobspy_test else '❌ FAIL'}")
    
    if proxy_test and jobspy_test:
        print("\n🎉 All tests passed! Proxy system is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the logs above for details.") 