#!/usr/bin/env python3
"""
Test moving leads to a campaign in Instantly.ai
"""

import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_move_leads():
    """Test moving leads to a campaign"""
    
    api_key = os.getenv("INSTANTLY_API_KEY")
    base_url = "https://api.instantly.ai/api/v2"
    
    print("🧪 Testing lead movement to campaign...")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # First, get all leads
    try:
        response = requests.post(
            f"{base_url}/leads/list",
            headers=headers,
            json={
                "limit": 50
            }
        )
        
        if response.ok:
            data = response.json()
            leads = data.get('items', [])
            print(f"📊 Found {len(leads)} total leads")
            
            if leads:
                # Get the first few lead IDs
                lead_ids = [lead['id'] for lead in leads[:5]]
                print(f"📝 Using lead IDs: {lead_ids}")
                
                # Get campaigns
                campaigns_response = requests.get(f"{base_url}/campaigns", headers=headers)
                print(f"📥 Campaigns response status: {campaigns_response.status_code}")
                
                if campaigns_response.ok:
                    campaigns_data = campaigns_response.json()
                    campaigns = campaigns_data.get('campaigns', [])
                    print(f"📊 Found {len(campaigns)} campaigns")
                    
                    # Try to get the specific campaign we just created
                    specific_campaign_id = "863c6b76-8da9-4eda-88fb-c7b123cf82a9"
                    print(f"🔍 Trying to get specific campaign: {specific_campaign_id}")
                    
                    specific_campaign_response = requests.get(f"{base_url}/campaigns/{specific_campaign_id}", headers=headers)
                    print(f"📥 Specific campaign response status: {specific_campaign_response.status_code}")
                    
                    if specific_campaign_response.ok:
                        specific_campaign = specific_campaign_response.json()
                        print(f"✅ Found specific campaign: {specific_campaign.get('name', 'N/A')}")
                        print(f"   Status: {specific_campaign.get('status', 'N/A')}")
                        
                        # Use this campaign for the move test
                        campaign_id = specific_campaign_id
                        campaign_name = specific_campaign.get('name', 'N/A')
                        print(f"🎯 Moving leads to campaign: {campaign_name} (ID: {campaign_id})")
                        
                        # Try to move leads
                        move_response = requests.post(
                            f"{base_url}/leads/move",
                            headers=headers,
                            json={
                                "ids": lead_ids,
                                "to_campaign_id": campaign_id,
                                "check_duplicates": True
                            }
                        )
                        
                        print(f"📥 Move response status: {move_response.status_code}")
                        
                        if move_response.ok:
                            move_data = move_response.json()
                            print(f"✅ Move job started: {move_data}")
                            
                            # Check if leads are now in the campaign
                            print(f"\n🔍 Checking if leads were moved...")
                            
                            # Wait a moment for the move to process
                            import time
                            time.sleep(2)
                            
                            # Check leads in the campaign
                            campaign_leads_response = requests.post(
                                f"{base_url}/leads/list",
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
                            print(f"❌ Failed to move leads: {move_response.status_code}")
                            print(f"   Response: {move_response.text}")
                    else:
                        print(f"❌ Failed to get specific campaign: {specific_campaign_response.status_code}")
                        print(f"   Response: {specific_campaign_response.text}")
                    
                    if campaigns:
                        print("   Available campaigns:")
                        for i, campaign in enumerate(campaigns):
                            print(f"     {i+1}. {campaign.get('name', 'N/A')} (ID: {campaign.get('id', 'N/A')}) - Status: {campaign.get('status', 'N/A')}")
                        
                        # Use the first campaign
                        campaign_id = campaigns[0]['id']
                        campaign_name = campaigns[0]['name']
                        print(f"🎯 Moving leads to campaign: {campaign_name} (ID: {campaign_id})")
                        
                        # Try to move leads
                        move_response = requests.post(
                            f"{base_url}/leads/move",
                            headers=headers,
                            json={
                                "ids": lead_ids,
                                "to_campaign_id": campaign_id,
                                "check_duplicates": True
                            }
                        )
                        
                        print(f"📥 Move response status: {move_response.status_code}")
                        
                        if move_response.ok:
                            move_data = move_response.json()
                            print(f"✅ Move job started: {move_data}")
                            
                            # Check if leads are now in the campaign
                            print(f"\n🔍 Checking if leads were moved...")
                            
                            # Wait a moment for the move to process
                            import time
                            time.sleep(2)
                            
                            # Check leads in the campaign
                            campaign_leads_response = requests.post(
                                f"{base_url}/leads/list",
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
                            print(f"❌ Failed to move leads: {move_response.status_code}")
                            print(f"   Response: {move_response.text}")
                    else:
                        print("❌ No campaigns found")
                else:
                    print(f"❌ Failed to get campaigns: {campaigns_response.status_code}")
            else:
                print("❌ No leads found")
        else:
            print(f"❌ Failed to get leads: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing move operation: {e}")

if __name__ == "__main__":
    test_move_leads() 