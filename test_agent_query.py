#!/usr/bin/env python3
"""
Test to check agent query for a batch
"""

import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_agent_query():
    """Test getting agent query for a batch"""
    
    batch_id = "batch_20250802_015816"
    
    print(f"🔍 Checking agent query for batch: {batch_id}")
    
    try:
        # Get agent information from the API
        response = requests.get(f"https://coogi-2-production.up.railway.app/batch/{batch_id}")
        
        if response.ok:
            data = response.json()
            agent = data.get('agent', {})
            
            print(f"📊 Agent data:")
            print(f"   Query: {agent.get('query', 'N/A')}")
            print(f"   Status: {agent.get('status', 'N/A')}")
            print(f"   Total jobs found: {agent.get('total_jobs_found', 'N/A')}")
            print(f"   Processed companies: {agent.get('processed_companies', 'N/A')}")
            
            # Extract a meaningful name from the query
            query = agent.get('query', '')
            if query:
                words = query.split(' ')[:3]
                agent_name = ' '.join(words)
                print(f"   Extracted agent name: {agent_name}")
            else:
                print(f"   No query found, using batch ID suffix: Agent-{batch_id[-8:]}")
        else:
            print(f"❌ Failed to get agent data: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_agent_query() 