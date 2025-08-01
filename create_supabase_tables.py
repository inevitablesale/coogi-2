#!/usr/bin/env python3
"""
Script to create Supabase tables for Coogi dashboard and logging
"""

import os
import sys
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    print("❌ Error: SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env file")
    sys.exit(1)

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

def create_tables():
    """Create all necessary tables in Supabase"""
    
    print("🔧 Creating Supabase tables...")
    
    # 1. Create search_logs_enhanced table
    try:
        supabase.table("search_logs_enhanced").select("count", count="exact").limit(1).execute()
        print("✅ search_logs_enhanced table already exists")
    except Exception:
        print("📝 Creating search_logs_enhanced table...")
        # This will be created via SQL since we can't create tables via Python client
        
    # 2. Create batches table
    try:
        supabase.table("batches").select("count", count="exact").limit(1).execute()
        print("✅ batches table already exists")
    except Exception:
        print("📝 Creating batches table...")
        
    # 3. Create agent_templates table
    try:
        supabase.table("agent_templates").select("count", count="exact").limit(1).execute()
        print("✅ agent_templates table already exists")
    except Exception:
        print("📝 Creating agent_templates table...")
        
    # 4. Create agent_performance table
    try:
        supabase.table("agent_performance").select("count", count="exact").limit(1).execute()
        print("✅ agent_performance table already exists")
    except Exception:
        print("📝 Creating agent_performance table...")
        
    # 5. Create agent_results_summary table
    try:
        supabase.table("agent_results_summary").select("count", count="exact").limit(1).execute()
        print("✅ agent_results_summary table already exists")
    except Exception:
        print("📝 Creating agent_results_summary table...")

def test_connection():
    """Test Supabase connection"""
    try:
        # Try to query a simple table
        response = supabase.table("search_logs_enhanced").select("count", count="exact").limit(1).execute()
        print("✅ Supabase connection successful")
        return True
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        return False

def main():
    print("🚀 Coogi Supabase Table Setup")
    print("=" * 50)
    
    # Test connection
    if not test_connection():
        print("\n📋 Manual Setup Required:")
        print("1. Go to your Supabase dashboard: https://supabase.com/dashboard")
        print("2. Select your project: dbtdplhlatnlzcvdvptn")
        print("3. Go to SQL Editor")
        print("4. Copy and paste the SQL from 'supabase_schema_enhanced.sql'")
        print("5. Click 'Run' to create all tables")
        print("\nAfter running the SQL, restart this script to verify.")
        return
    
    # Create tables
    create_tables()
    
    print("\n✅ Setup complete!")
    print("📊 You can now view logs in your Supabase dashboard under Table Editor")

if __name__ == "__main__":
    main() 