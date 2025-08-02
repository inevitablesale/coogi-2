#!/usr/bin/env python3
"""
Check agent data in the database
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

def check_agent_data():
    """Check agent data in the database"""
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    supabase: Client = create_client(supabase_url, supabase_key)
    
    print(f"🔍 Checking database tables...")
    
    try:
        # Check agents table - get all columns
        print(f"\n📊 Checking agents table structure...")
        agents_response = supabase.table("agents").select("*").execute()
        
        if agents_response.data:
            print(f"✅ Found {len(agents_response.data)} agents:")
            for i, agent in enumerate(agents_response.data):
                print(f"\n   Agent {i+1}:")
                print(f"     Batch ID: {agent.get('batch_id', 'N/A')}")
                print(f"     Name: {agent.get('name', 'N/A')}")
                print(f"     Query: {agent.get('query', 'N/A')}")
                print(f"     Status: {agent.get('status', 'N/A')}")
                print(f"     All fields: {list(agent.keys())}")
        else:
            print(f"❌ No agents found in agents table")
        
        # Check if our specific batch_id exists in agents
        batch_id = "batch_20250802_015816"
        print(f"\n🔍 Checking for specific batch_id: {batch_id}")
        specific_agent = supabase.table("agents").select("*").eq("batch_id", batch_id).execute()
        
        if specific_agent.data:
            print(f"✅ Found agent for batch_id {batch_id}:")
            agent = specific_agent.data[0]
            print(f"     Name: {agent.get('name', 'N/A')}")
            print(f"     Query: {agent.get('query', 'N/A')}")
        else:
            print(f"❌ No agent found for batch_id {batch_id}")
            
    except Exception as e:
        print(f"❌ Error checking data: {e}")

if __name__ == "__main__":
    check_agent_data() 