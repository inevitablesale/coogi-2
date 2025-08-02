#!/usr/bin/env python3
"""
Backfill contact data from logs into hunter_emails table
"""

import os
import re
import json
from datetime import datetime
from typing import List, Dict, Any
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_supabase_client() -> Client:
    """Initialize Supabase client"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    
    if not url or not key:
        print("❌ Error: Missing Supabase credentials")
        return None
    
    return create_client(url, key)

def extract_contact_from_log(log_message: str) -> Dict[str, Any]:
    """Extract contact information from log message"""
    
    # Pattern: "📝 Created lead for Company: Full Name (Title) - email@company.com"
    pattern = r'📝 Created lead for ([^:]+): ([^(]+) \(([^)]+)\) - ([^@]+@[^@]+)'
    match = re.match(pattern, log_message)
    
    if match:
        company = match.group(1).strip()
        full_name = match.group(2).strip()
        title = match.group(3).strip()
        email = match.group(4).strip()
        
        # Split full name into first and last name
        name_parts = full_name.split(' ')
        first_name = name_parts[0] if name_parts else ''
        last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
        
        return {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "full_name": full_name,
            "title": title,
            "company": company,
            "source": "log_extraction"
        }
    
    return None

def get_logs_for_batch(supabase: Client, batch_id: str) -> List[Dict[str, Any]]:
    """Get all logs for a specific batch"""
    try:
        response = supabase.table("search_logs_enhanced").select("*").eq("batch_id", batch_id).execute()
        return response.data
    except Exception as e:
        print(f"❌ Error getting logs for batch {batch_id}: {e}")
        return []

def update_hunter_emails_with_contacts(supabase: Client, batch_id: str, company: str, contact_data: List[Dict[str, Any]]):
    """Update hunter_emails record with contact data"""
    try:
        # Find the hunter_emails record for this batch and company
        response = supabase.table("hunter_emails").select("*").eq("batch_id", batch_id).eq("company", company).execute()
        
        if response.data:
            record = response.data[0]
            record_id = record['id']
            
            # Update with contact data (individual columns don't exist yet)
            update_data = {
                "contact_data": contact_data
            }
            
            supabase.table("hunter_emails").update(update_data).eq("id", record_id).execute()
            
            print(f"✅ Updated {company} with {len(contact_data)} contacts")
            if contact_data:
                print(f"   📧 First contact: {contact_data[0].get('first_name', '')} {contact_data[0].get('last_name', '')} - {contact_data[0].get('title', '')}")
        else:
            print(f"⚠️  No hunter_emails record found for {company} in batch {batch_id}")
            
    except Exception as e:
        print(f"❌ Error updating hunter_emails for {company}: {e}")

def backfill_contacts_for_batch(supabase: Client, batch_id: str):
    """Backfill contact data for a specific batch"""
    print(f"🔄 Processing batch: {batch_id}")
    
    # Get all logs for this batch
    logs = get_logs_for_batch(supabase, batch_id)
    
    # Group contacts by company
    company_contacts = {}
    
    for log in logs:
        if not log.get('message'):
            continue
            
        message = log['message']
        
        # Look for contact creation logs
        if '📝 Created lead for' in message:
            contact = extract_contact_from_log(message)
            if contact:
                company = contact['company']
                if company not in company_contacts:
                    company_contacts[company] = []
                company_contacts[company].append(contact)
    
    # Update hunter_emails records
    for company, contacts in company_contacts.items():
        update_hunter_emails_with_contacts(supabase, batch_id, company, contacts)
    
    print(f"✅ Processed {len(company_contacts)} companies for batch {batch_id}")

def get_all_batches(supabase: Client) -> List[str]:
    """Get all unique batch IDs from hunter_emails table"""
    try:
        response = supabase.table("hunter_emails").select("batch_id").execute()
        batch_ids = list(set([record['batch_id'] for record in response.data]))
        return batch_ids
    except Exception as e:
        print(f"❌ Error getting batch IDs: {e}")
        return []

def main():
    """Main backfill function"""
    print("🔄 Starting contact data backfill...")
    
    # Initialize Supabase client
    supabase = get_supabase_client()
    if not supabase:
        return
    
    # Get all batch IDs
    batch_ids = get_all_batches(supabase)
    print(f"📊 Found {len(batch_ids)} batches to process")
    
    # Process each batch
    for batch_id in batch_ids:
        backfill_contacts_for_batch(supabase, batch_id)
    
    print("✅ Contact data backfill complete!")

if __name__ == "__main__":
    main() 