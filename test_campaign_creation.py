#!/usr/bin/env python3
"""
Test Instantly.ai campaign creation API
"""

import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_campaign_creation():
    """Test creating a campaign in Instantly.ai"""
    
    api_key = os.getenv("INSTANTLY_API_KEY")
    base_url = "https://api.instantly.ai/api/v2"
    
    print("🧪 Testing Instantly.ai campaign creation...")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # First, let's check what campaigns exist
    try:
        response = requests.get(f"{base_url}/campaigns", headers=headers)
        print(f"📊 Campaigns response: {response.status_code}")
        
        if response.ok:
            data = response.json()
            print(f"✅ Found {len(data.get('campaigns', []))} campaigns")
            for campaign in data.get('campaigns', [])[:3]:  # Show first 3
                print(f"   - {campaign.get('name', 'N/A')} (ID: {campaign.get('id', 'N/A')})")
        else:
            print(f"❌ Failed to get campaigns: {response.text}")
    except Exception as e:
        print(f"❌ Error getting campaigns: {e}")
    
    # Now try to create a campaign
    campaign_data = {
        "name": "Coogi Test Campaign",
        "campaign_schedule": {
            "schedules": [
                {
                    "name": "Coogi Schedule",
                    "timing": {
                        "from": "09:00",
                        "to": "17:00"
                    },
                    "days": {
                        0: True,  # Monday
                        1: True,  # Tuesday
                        2: True,  # Wednesday
                        3: True,  # Thursday
                        4: True,  # Friday
                        5: False, # Saturday
                        6: False  # Sunday
                    },
                    "timezone": "America/Chicago"
                }
            ],
            "start_date": "2025-08-02T00:00:00.000Z",
            "end_date": "2025-09-01T00:00:00.000Z"
        },
        "sequences": [
            {
                "steps": [
                    {
                        "type": "email",
                        "subject": "Opportunity at {{company_name}}",
                        "body": "Hi {{first_name}},\n\nI noticed your role at {{company_name}} and thought you might be interested in a new opportunity.\n\nBest regards,\n{{sender_name}}",
                        "delay": 0,
                        "variants": [
                            {
                                "subject": "Opportunity at {{company_name}}",
                                "body": "Hi {{first_name}},\n\nI noticed your role at {{company_name}} and thought you might be interested in a new opportunity.\n\nBest regards,\n{{sender_name}}"
                            }
                        ]
                    }
                ]
            }
        ],
        "email_list": ["chuck@liacgroupagency.com"],
        "daily_limit": 50,
        "stop_on_reply": True,
        "link_tracking": True,
        "open_tracking": True
    }
    
    print(f"\n📤 Creating campaign with data: {json.dumps(campaign_data, indent=2)}")
    
    try:
        response = requests.post(f"{base_url}/campaigns", headers=headers, json=campaign_data)
        print(f"📥 Campaign creation response: {response.status_code}")
        
        if response.ok:
            data = response.json()
            print(f"✅ Campaign created: {data}")
        else:
            print(f"❌ Failed to create campaign: {response.text}")
    except Exception as e:
        print(f"❌ Error creating campaign: {e}")

if __name__ == "__main__":
    test_campaign_creation() 