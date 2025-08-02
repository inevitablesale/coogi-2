#!/usr/bin/env python3
"""
Test the batch endpoint to see if it returns hunter_emails data
"""

import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_batch_endpoint():
    """Test the batch endpoint"""
    
    batch_id = "batch_20250802_015816"
    
    print("🧪 Testing batch endpoint...")
    
    try:
        # Try local API first
        response = requests.get(f"http://localhost:8000/batch/{batch_id}", timeout=5)
        if response.ok:
            print("✅ Local API is running")
            data = response.json()
        else:
            print("❌ Local API not available, trying production...")
            # Try production API
            response = requests.get(f"https://coogi-api-production.up.railway.app/batch/{batch_id}", timeout=10)
            if response.ok:
                print("✅ Production API is running")
                data = response.json()
            else:
                print(f"❌ Both APIs failed: {response.status_code}")
                return
    except Exception as e:
        print(f"❌ Error testing API: {e}")
        return
    
    print(f"\n📊 Batch Response:")
    print(f"   Status: {data.get('status', 'N/A')}")
    print(f"   Total logs: {data.get('total_logs', 0)}")
    print(f"   Total hunter_emails: {data.get('total_hunter_emails', 0)}")
    
    hunter_emails = data.get('hunter_emails', [])
    print(f"   Hunter emails found: {len(hunter_emails)}")
    
    if hunter_emails:
        print(f"\n📧 First hunter email record:")
        first_record = hunter_emails[0]
        print(f"   Company: {first_record.get('company', 'N/A')}")
        print(f"   Emails found: {first_record.get('emails_found', 0)}")
        print(f"   Search success: {first_record.get('search_success', False)}")
        
        email_list = first_record.get('email_list', [])
        print(f"   Email list length: {len(email_list)}")
        
        if email_list:
            first_contact = email_list[0]
            print(f"   First contact:")
            print(f"     - Name: {first_contact.get('name', 'N/A')}")
            print(f"     - Email: {first_contact.get('email', 'N/A')}")
            print(f"     - Title: {first_contact.get('title', 'N/A')}")
            print(f"     - Company: {first_contact.get('company', 'N/A')}")
    else:
        print("❌ No hunter_emails data found")

if __name__ == "__main__":
    test_batch_endpoint() 