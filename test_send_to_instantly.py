#!/usr/bin/env python3
"""
Test sending leads to Instantly.ai using the Edge Function
"""

import os
import requests
import json
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

def test_send_to_instantly():
    """Test sending leads to Instantly.ai"""
    
    # Get environment variables
    supabase_url = os.getenv("SUPABASE_URL")
    edge_function_url = f"{supabase_url}/functions/v1/send-to-instantly"
    
    print("🧪 Testing Send to Instantly functionality...")
    
    # Test with a real batch_id that has data
    batch_id = "batch_20250802_015816"
    
    # Try a different batch if this one has all existing leads
    print("🔍 Checking if this batch has new contacts...")
    
    # First check what contacts are in this batch
    try:
        batch_response = requests.get(f"https://coogi-2-production.up.railway.app/batch/{batch_id}")
        if batch_response.ok:
            batch_data = batch_response.json()
            hunter_emails = batch_data.get('hunter_emails', [])
            print(f"📊 Batch has {len(hunter_emails)} hunter_emails records")
            
            total_contacts = 0
            for record in hunter_emails:
                email_list = record.get('email_list', [])
                total_contacts += len(email_list)
            
            print(f"📧 Total contacts in batch: {total_contacts}")
            
            # Test the Edge Function with agent campaign creation
            print("\n🧪 Testing Edge Function with agent campaign creation...")
            
            # Prepare the request payload
            payload = {
                "batch_id": batch_id,
                "action": "create_leads"
            }
            
            print(f"📤 Sending request to Edge Function:")
            print(f"   URL: {edge_function_url}")
            print(f"   Batch ID: {batch_id}")
            print(f"   Payload: {json.dumps(payload, indent=2)}")
            
            # Make the request
            response = requests.post(
                edge_function_url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {os.getenv('SUPABASE_ANON_KEY')}"
                },
                json=payload,
                timeout=30
            )
            
            print(f"\n📥 Response Status: {response.status_code}")
            
            if response.ok:
                result = response.json()
                print("✅ Success! Edge Function response:")
                print(json.dumps(result, indent=2))
                
                # Show summary
                if 'summary' in result:
                    summary = result['summary']
                    print(f"\n📊 Summary:")
                    print(f"   Total contacts: {summary.get('total_contacts', 0)}")
                    print(f"   Created leads: {summary.get('created', 0)}")
                    print(f"   Skipped: {summary.get('skipped', 0)}")
                    print(f"   Failed: {summary.get('failed', 0)}")
                    print(f"   Campaign ID: {summary.get('campaign_id', 'N/A')}")
                    
                    # Check if leads were moved to campaign
                    campaign_id = summary.get('campaign_id')
                    if campaign_id and campaign_id != 'N/A':
                        print(f"\n🔍 Checking if leads were moved to campaign {campaign_id}...")
                        
                        # Check campaign details
                        api_key = os.getenv("INSTANTLY_API_KEY")
                        headers = {
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json"
                        }
                        
                        # Get campaign details
                        campaign_response = requests.get(
                            f"https://api.instantly.ai/api/v2/campaigns/{campaign_id}",
                            headers=headers
                        )
                        
                        if campaign_response.ok:
                            campaign_data = campaign_response.json()
                            print(f"✅ Campaign found: {campaign_data.get('name', 'N/A')}")
                            print(f"   Status: {campaign_data.get('status', 'N/A')}")
                            print(f"   Created: {campaign_data.get('timestamp_created', 'N/A')}")
                            print(f"   Agent Name: {campaign_data.get('name', 'N/A').replace('Coogi Agent - ', '')}")
                        else:
                            print(f"❌ Failed to get campaign details: {campaign_response.status_code}")
                        
                        # Check leads in campaign
                        leads_response = requests.post(
                            "https://api.instantly.ai/api/v2/leads/list",
                            headers=headers,
                            json={
                                "campaign": campaign_id,
                                "limit": 50
                            }
                        )
                        
                        if leads_response.ok:
                            leads_data = leads_response.json()
                            leads = leads_data.get('items', [])
                            print(f"📧 Leads in campaign: {len(leads)}")
                            
                            if leads:
                                print("   First few leads:")
                                for i, lead in enumerate(leads[:3]):
                                    print(f"     {i+1}. {lead.get('email', 'N/A')} - {lead.get('first_name', '')} {lead.get('last_name', '')}")
                            else:
                                print("   ❌ No leads found in campaign")
                        else:
                            print(f"❌ Failed to get leads: {leads_response.status_code}")
                            print(f"   Response: {leads_response.text}")
                
                if 'created_leads' in result:
                    print(f"\n✅ Created leads with LinkedIn URLs and Websites:")
                    for lead in result['created_leads']:
                        contact = lead.get('contact', {})
                        lead_id = lead.get('lead_id', 'N/A')
                        linkedin = contact.get('linkedin_url', 'N/A')
                        website = contact.get('website', 'N/A')
                        print(f"   - {contact.get('email', 'N/A')} (ID: {lead_id})")
                        print(f"     LinkedIn: {linkedin}")
                        print(f"     Website: {website}")
                
                if 'errors' in result and result['errors']:
                    print(f"\n❌ Errors:")
                    for error in result['errors']:
                        contact = error.get('contact', {})
                        error_msg = error.get('error', 'Unknown error')
                        print(f"   - {contact.get('email', 'N/A')}: {error_msg}")
                        
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"Response: {response.text}")
            
            # Test direct lead creation with campaign assignment
            print("🧪 Testing direct lead creation with campaign assignment...")
            
            # Test direct lead creation
            api_key = os.getenv("INSTANTLY_API_KEY")
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # Get existing campaigns instead of creating new ones
            campaigns_response = requests.get("https://api.instantly.ai/api/v2/campaigns", headers=headers)
            if campaigns_response.ok:
                campaigns_data = campaigns_response.json()
                campaigns = campaigns_data.get('campaigns', [])
                
                if campaigns:
                    campaign_id = campaigns[0]['id']
                    campaign_name = campaigns[0]['name']
                    print(f"🎯 Using existing campaign: {campaign_name} (ID: {campaign_id})")
                    
                    # Create a test lead directly in the existing campaign
                    test_lead = {
                        "email": f"test-{int(time.time())}@example.com",
                        "first_name": "Test",
                        "last_name": "User",
                        "company_name": "Test Company",
                        "campaign": campaign_id
                    }
                    
                    print(f"📤 Creating test lead: {test_lead['email']}")
                    lead_response = requests.post("https://api.instantly.ai/api/v2/leads", headers=headers, json=test_lead)
                    print(f"📥 Test lead creation response: {lead_response.status_code}")
                    
                    if lead_response.ok:
                        lead_result = lead_response.json()
                        print(f"✅ Test lead created: {lead_result}")
                        
                        # Check if lead is in the campaign
                        print(f"\n🔍 Checking if lead is in campaign...")
                        time.sleep(2)
                        
                        campaign_leads_response = requests.post(
                            "https://api.instantly.ai/api/v2/leads/list",
                            headers=headers,
                            json={
                                "campaign": campaign_id,
                                "limit": 50
                            }
                        )
                        
                        if campaign_leads_response.ok:
                            campaign_leads_data = campaign_leads_response.json()
                            campaign_leads = campaign_leads_data.get('items', [])
                            print(f"📧 Leads in campaign: {len(campaign_leads)}")
                            
                            if campaign_leads:
                                print("   First few leads in campaign:")
                                for i, lead in enumerate(campaign_leads[:3]):
                                    print(f"     {i+1}. {lead.get('email', 'N/A')} - {lead.get('first_name', '')} {lead.get('last_name', '')}")
                            else:
                                print("   ❌ No leads found in campaign")
                        else:
                            print(f"❌ Failed to get campaign leads: {campaign_leads_response.status_code}")
                    else:
                        print(f"❌ Failed to create test lead: {lead_response.text}")
                else:
                    print("❌ No existing campaigns found")
            else:
                print(f"❌ Failed to get campaigns: {campaigns_response.status_code}")
            
            if total_contacts == 0:
                print("❌ No contacts in this batch, trying a different approach...")
                # Try to create a test contact directly
                print("🧪 Creating a test contact directly...")
                
                # Test direct lead creation
                api_key = os.getenv("INSTANTLY_API_KEY")
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                
                # Get or create a campaign
                campaigns_response = requests.get("https://api.instantly.ai/api/v2/campaigns", headers=headers)
                if campaigns_response.ok:
                    campaigns_data = campaigns_response.json()
                    campaigns = campaigns_data.get('campaigns', [])
                    
                    if campaigns:
                        campaign_id = campaigns[0]['id']
                    else:
                        # Create a test campaign
                        campaign_data = {
                            "name": "Test Campaign",
                            "campaign_schedule": {
                                "schedules": [{
                                    "name": "Test Schedule",
                                    "timing": {"from": "09:00", "to": "17:00"},
                                    "days": {"0": True, "1": True, "2": True, "3": True, "4": True, "5": False, "6": False},
                                    "timezone": "America/Chicago"
                                }],
                                "start_date": "2025-08-02T00:00:00.000Z",
                                "end_date": "2025-09-01T00:00:00.000Z"
                            },
                            "sequences": [{
                                "steps": [{
                                    "type": "email",
                                    "subject": "Test",
                                    "body": "Test",
                                    "delay": 0,
                                    "variants": [{"subject": "Test", "body": "Test"}]
                                }]
                            }],
                            "email_list": ["chuck@liacgroupagency.com"]
                        }
                        
                        campaign_response = requests.post("https://api.instantly.ai/api/v2/campaigns", headers=headers, json=campaign_data)
                        if campaign_response.ok:
                            campaign_result = campaign_response.json()
                            campaign_id = campaign_result['id']
                        else:
                            print(f"❌ Failed to create test campaign: {campaign_response.status_code}")
                            return
                    
                    # Create a test lead
                    test_lead = {
                        "email": f"test-{int(time.time())}@example.com",
                        "first_name": "Test",
                        "last_name": "User",
                        "company_name": "Test Company",
                        "campaign": campaign_id
                    }
                    
                    lead_response = requests.post("https://api.instantly.ai/api/v2/leads", headers=headers, json=test_lead)
                    print(f"📥 Test lead creation response: {lead_response.status_code}")
                    
                    if lead_response.ok:
                        lead_result = lead_response.json()
                        print(f"✅ Test lead created: {lead_result}")
                    else:
                        print(f"❌ Failed to create test lead: {lead_response.text}")
                else:
                    print(f"❌ Failed to get campaigns: {campaigns_response.status_code}")
        else:
            print(f"❌ Failed to get batch data: {batch_response.status_code}")
    except Exception as e:
        print(f"❌ Error checking batch: {e}")

if __name__ == "__main__":
    test_send_to_instantly() 