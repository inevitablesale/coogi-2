#!/usr/bin/env python3
"""
Supabase Database Checker
Checks the current state of all tables in the Coogi database
"""

import os
import sys
from datetime import datetime
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
        print("Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY")
        sys.exit(1)
    
    return create_client(url, key)

def check_table_data(supabase: Client, table_name: str, limit: int = 10):
    """Check data in a specific table"""
    try:
        print(f"\n📊 Checking {table_name} table...")
        response = supabase.table(table_name).select("*").limit(limit).execute()
        
        if response.data:
            print(f"✅ Found {len(response.data)} records in {table_name}")
            for i, record in enumerate(response.data[:3]):  # Show first 3 records
                print(f"  Record {i+1}:")
                for key, value in record.items():
                    if isinstance(value, dict) or isinstance(value, list):
                        print(f"    {key}: {type(value).__name__} with {len(value)} items")
                    else:
                        print(f"    {key}: {value}")
        else:
            print(f"⚠️  No data found in {table_name}")
            
    except Exception as e:
        print(f"❌ Error checking {table_name}: {e}")

def check_hunter_emails(supabase: Client):
    """Specifically check Hunter.io emails data"""
    try:
        print(f"\n🎯 Checking Hunter.io emails data...")
        response = supabase.table("hunter_emails").select("*").order("timestamp", desc=True).limit(5).execute()
        
        if response.data:
            print(f"✅ Found {len(response.data)} Hunter.io email records")
            for record in response.data:
                print(f"  📧 {record.get('company', 'Unknown')}: {record.get('emails_found', 0)} emails found")
                print(f"     Batch: {record.get('batch_id', 'Unknown')}")
                print(f"     Success: {record.get('search_success', False)}")
                if record.get('email_list'):
                    print(f"     Emails: {len(record['email_list'])} emails in list")
                print(f"     Time: {record.get('timestamp', 'Unknown')}")
                print()
        else:
            print("⚠️  No Hunter.io email records found")
            
    except Exception as e:
        print(f"❌ Error checking Hunter.io emails: {e}")

def check_agents(supabase: Client):
    """Check agents table"""
    try:
        print(f"\n🤖 Checking agents table...")
        response = supabase.table("agents").select("*").order("created_at", desc=True).limit(5).execute()
        
        if response.data:
            print(f"✅ Found {len(response.data)} agent records")
            for record in response.data:
                print(f"  🤖 Agent: {record.get('query', 'Unknown')}")
                print(f"     Status: {record.get('status', 'Unknown')}")
                print(f"     Batch ID: {record.get('batch_id', 'Unknown')}")
                print(f"     User: {record.get('user_email', 'Unknown')}")
                print(f"     Created: {record.get('created_at', 'Unknown')}")
                print()
        else:
            print("⚠️  No agent records found")
            
    except Exception as e:
        print(f"❌ Error checking agents: {e}")

def check_instantly_campaigns(supabase: Client):
    """Check Instantly.ai campaigns"""
    try:
        print(f"\n🚀 Checking Instantly.ai campaigns...")
        response = supabase.table("instantly_campaigns").select("*").order("timestamp", desc=True).limit(5).execute()
        
        if response.data:
            print(f"✅ Found {len(response.data)} campaign records")
            for record in response.data:
                print(f"  🚀 Campaign: {record.get('campaign_name', 'Unknown')}")
                print(f"     Company: {record.get('company', 'Unknown')}")
                print(f"     Leads Added: {record.get('leads_added', 0)}")
                print(f"     Success: {record.get('campaign_success', False)}")
                print(f"     Time: {record.get('timestamp', 'Unknown')}")
                print()
        else:
            print("⚠️  No Instantly.ai campaign records found")
            
    except Exception as e:
        print(f"❌ Error checking Instantly campaigns: {e}")

def check_company_processing(supabase: Client):
    """Check company processing summary"""
    try:
        print(f"\n🏢 Checking company processing summary...")
        response = supabase.table("company_processing_summary").select("*").order("timestamp", desc=True).limit(5).execute()
        
        if response.data:
            print(f"✅ Found {len(response.data)} company processing records")
            for record in response.data:
                print(f"  🏢 Company: {record.get('company', 'Unknown')}")
                print(f"     Hunter Emails Found: {record.get('hunter_emails_found', False)}")
                print(f"     Instantly Campaign Created: {record.get('instantly_campaign_created', False)}")
                print(f"     Recommendation: {record.get('final_recommendation', 'Unknown')}")
                print(f"     Time: {record.get('timestamp', 'Unknown')}")
                print()
        else:
            print("⚠️  No company processing records found")
            
    except Exception as e:
        print(f"❌ Error checking company processing: {e}")

def check_table_schemas(supabase: Client):
    """Check what tables exist"""
    try:
        print(f"\n📋 Checking available tables...")
        
        # List of tables we expect to exist
        expected_tables = [
            "agents",
            "hunter_emails", 
            "instantly_campaigns",
            "company_processing_summary",
            "search_logs_enhanced",
            "company_analysis",
            "domain_search_results",
            "linkedin_resolution",
            "rapidapi_analysis"
        ]
        
        for table in expected_tables:
            try:
                response = supabase.table(table).select("id").limit(1).execute()
                print(f"✅ Table '{table}' exists")
            except Exception as e:
                print(f"❌ Table '{table}' not found or error: {e}")
                
    except Exception as e:
        print(f"❌ Error checking table schemas: {e}")

def main():
    """Main function to check Supabase database"""
    print("🔍 Coogi Supabase Database Checker")
    print("=" * 50)
    
    # Initialize Supabase client
    supabase = get_supabase_client()
    print("✅ Connected to Supabase")
    
    # Check table schemas first
    check_table_schemas(supabase)
    
    # Check specific data tables
    check_agents(supabase)
    check_hunter_emails(supabase)
    check_instantly_campaigns(supabase)
    check_company_processing(supabase)
    
    # Check other important tables
    check_table_data(supabase, "search_logs_enhanced", 5)
    check_table_data(supabase, "company_analysis", 5)
    
    print("\n" + "=" * 50)
    print("✅ Supabase database check complete!")

if __name__ == "__main__":
    main() 