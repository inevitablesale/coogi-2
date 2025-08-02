#!/usr/bin/env python3
"""
Check if Hunter.io data is being saved to Supabase correctly
"""

import os
import json
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

def check_hunter_flow():
    """Check if Hunter.io data is being saved to Supabase correctly"""
    
    # Initialize Supabase client
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials")
        return
    
    supabase = create_client(supabase_url, supabase_key)
    
    print("🔍 Checking Hunter.io → Supabase flow...")
    
    try:
        # Get recent hunter_emails records
        response = supabase.table("hunter_emails").select("*").order("timestamp", desc=True).limit(5).execute()
        
        if not response.data:
            print("❌ No hunter_emails records found")
            return
        
        print(f"📊 Found {len(response.data)} recent records")
        
        for i, record in enumerate(response.data):
            company = record.get("company", "Unknown")
            timestamp = record.get("timestamp", "Unknown")
            emails_found = record.get("emails_found", 0)
            email_list = record.get("email_list", [])
            search_success = record.get("search_success", False)
            
            print(f"\n📧 Record {i+1}: {company}")
            print(f"   Timestamp: {timestamp}")
            print(f"   Emails found: {emails_found}")
            print(f"   Search success: {search_success}")
            
            if email_list:
                print(f"   Email list has {len(email_list)} contacts")
                # Show first contact details
                first_contact = email_list[0] if email_list else {}
                print(f"   First contact:")
                print(f"     - Name: {first_contact.get('name', 'N/A')}")
                print(f"     - Email: {first_contact.get('email', 'N/A')}")
                print(f"     - Title: {first_contact.get('title', 'N/A')}")
                print(f"     - Company: {first_contact.get('company', 'N/A')}")
                print(f"     - Confidence: {first_contact.get('confidence', 'N/A')}")
                print(f"     - LinkedIn: {first_contact.get('linkedin_url', 'N/A')}")
            else:
                print("   ❌ No email_list data")
        
        # Check if we have recent successful searches
        successful_searches = [r for r in response.data if r.get("search_success", False)]
        print(f"\n✅ Successful Hunter.io searches: {len(successful_searches)}")
        
        if successful_searches:
            print("🎉 Hunter.io → Supabase flow is working!")
        else:
            print("⚠️  No successful Hunter.io searches found")
            
    except Exception as e:
        print(f"❌ Error checking Hunter.io flow: {e}")

if __name__ == "__main__":
    check_hunter_flow() 