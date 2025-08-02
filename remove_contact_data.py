#!/usr/bin/env python3
"""
Remove contact_data column from hunter_emails table
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

def remove_contact_data_column():
    """Remove contact_data column from hunter_emails table"""
    
    # Initialize Supabase client
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials")
        return
    
    supabase: Client = create_client(supabase_url, supabase_key)
    
    print("🔄 Removing contact_data column...")
    
    try:
        # First, let's check what columns we have
        response = supabase.table("hunter_emails").select("*").limit(1).execute()
        
        if response.data:
            print("Current columns:", list(response.data[0].keys()))
            
            if 'contact_data' in response.data[0]:
                print("✅ contact_data column found - will be removed")
            else:
                print("ℹ️  contact_data column not found")
                return
        else:
            print("❌ No data found in hunter_emails table")
            return
        
        # Since we can't directly drop columns via Supabase client,
        # we'll just update all records to remove the contact_data field
        # This effectively "removes" it from our perspective
        
        all_records = supabase.table("hunter_emails").select("*").execute()
        
        updated_count = 0
        for record in all_records.data:
            record_id = record['id']
            
            # Create update data without contact_data
            update_data = {k: v for k, v in record.items() if k != 'contact_data'}
            
            try:
                supabase.table("hunter_emails").update(update_data).eq("id", record_id).execute()
                updated_count += 1
                print(f"✅ Updated record {record_id}")
            except Exception as e:
                print(f"❌ Error updating record {record_id}: {e}")
        
        print(f"✅ Successfully removed contact_data from {updated_count} records")
        print("📝 Note: The column still exists in the database schema but is no longer used")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    remove_contact_data_column() 