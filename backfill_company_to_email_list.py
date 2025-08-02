#!/usr/bin/env python3
"""
Backfill company information into email_list records
"""

import os
import json
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

def backfill_company_to_email_list():
    """Backfill company information into email_list records"""
    
    # Initialize Supabase client
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials")
        return
    
    supabase: Client = create_client(supabase_url, supabase_key)
    
    print("🔄 Starting company backfill to email_list...")
    
    try:
        # Get all hunter_emails records
        response = supabase.table("hunter_emails").select("*").execute()
        
        if not response.data:
            print("❌ No hunter_emails records found")
            return
        
        print(f"📊 Found {len(response.data)} records to process")
        
        updated_count = 0
        
        for record in response.data:
            record_id = record['id']
            company = record.get('company', '')
            email_list = record.get('email_list', [])
            
            if not email_list:
                print(f"⚠️  Skipping {company}: No email_list data")
                continue
            
            # Check if any email objects already have company info
            needs_update = False
            updated_email_list = []
            
            for email_obj in email_list:
                if isinstance(email_obj, dict) and 'company' not in email_obj:
                    # Add company information
                    email_obj['company'] = company
                    needs_update = True
                updated_email_list.append(email_obj)
            
            if needs_update:
                try:
                    # Update the record with company information added to email_list
                    supabase.table("hunter_emails").update({
                        "email_list": updated_email_list
                    }).eq("id", record_id).execute()
                    
                    print(f"✅ Updated {company}: Added company to {len(email_list)} email objects")
                    updated_count += 1
                except Exception as e:
                    print(f"❌ Error updating {company}: {e}")
            else:
                print(f"ℹ️  Skipping {company}: Already has company info")
        
        print(f"✅ Company backfill complete! Updated {updated_count} records")
        
    except Exception as e:
        print(f"❌ Error during backfill: {e}")

if __name__ == "__main__":
    backfill_company_to_email_list() 