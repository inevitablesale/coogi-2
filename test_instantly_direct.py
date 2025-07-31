#!/usr/bin/env python3
"""
Direct test of Instantly API integration
"""

import os
import sys
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the utils directory to the path
sys.path.append('utils')

from instantly_manager import InstantlyManager

def test_instantly_direct():
    """Test Instantly API directly with minimal data"""
    
    # Initialize Instantly manager
    instantly = InstantlyManager()
    
    # Test data
    test_leads = [
        {
            "email": "test@example.com",
            "name": "John Doe",
            "company": "Test Company",
            "job_title": "Software Engineer",
            "title": "Senior Developer",
            "job_url": "https://example.com/job",
            "score": 85,
            "hunter_emails": ["john@testcompany.com"],
            "company_website": "testcompany.com"
        }
    ]
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print("🧪 Testing Instantly API directly...")
    print(f"📧 Test lead: {test_leads[0]['email']}")
    
    # Step 1: Create lead list
    print("\n1️⃣ Creating lead list...")
    lead_list_name = f"Test_Leads_{timestamp}"
    lead_list_id = instantly.create_lead_list(lead_list_name, test_leads)
    
    if not lead_list_id:
        print("❌ Failed to create lead list")
        return False
    
    print(f"✅ Lead list created: {lead_list_id}")
    
    # Step 2: Create campaign
    print("\n2️⃣ Creating campaign...")
    campaign_name = f"Test_Campaign_{timestamp}"
    
    # Simple email template
    subject_line = "Recruiting Partnership"
    message_template = "Hi {contact_name},\n\nI hope this finds you well. I'm reaching out regarding potential recruiting opportunities.\n\nBest regards,\nRecruiting Team"
    
    # Let's also test the campaign creation directly to see the exact error
    print("\n🔍 Testing campaign creation directly...")
    
    # Direct API call to see the exact error
    api_key = os.getenv('INSTANTLY_API_KEY')
    base_url = "https://api.instantly.ai"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin"
    }
    
    campaign_payload = {
        "name": campaign_name,
        "status": 0,  # 0 = Draft status
        "campaign_schedule": {
            "schedules": [
                {
                    "name": "Default Schedule",
                    "timing": {
                        "from": "09:00",
                        "to": "17:00"
                    },
                    "days": {
                        "0": True,  # Monday
                        "1": True,  # Tuesday
                        "2": True,  # Wednesday
                        "3": True,  # Thursday
                        "4": True,  # Friday
                        "5": False, # Saturday
                        "6": False  # Sunday
                    },
                    "timezone": "America/Chicago"
                }
            ]
        },
        "sequences": [
            {
                "steps": [
                    {
                        "type": "email",
                        "delay": 0,
                        "variants": [
                            {
                                "subject": subject_line,
                                "body": message_template,
                                "sender_email": "test@recruiting.com",
                                "sender_name": "Test Recruiter"
                            }
                        ]
                    }
                ]
            }
        ],
        "list_id": lead_list_id
    }
    
    try:
        response = requests.post(f"{base_url}/api/v2/campaigns", headers=headers, json=campaign_payload, timeout=30)
        print(f"Direct API Status: {response.status_code}")
        print(f"Direct API Response: {response.text[:500]}")
        
        if response.status_code == 200:
            data = response.json()
            campaign_id = data.get("id")
            print(f"✅ Direct campaign creation successful: {campaign_id}")
            return True
        else:
            print(f"❌ Direct campaign creation failed")
            return False
    except Exception as e:
        print(f"❌ Direct API error: {e}")
        return False

if __name__ == "__main__":
    success = test_instantly_direct()
    if success:
        print("\n🎯 Direct test completed successfully!")
    else:
        print("\n💥 Direct test failed!")
        sys.exit(1) 