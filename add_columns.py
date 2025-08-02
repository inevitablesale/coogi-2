#!/usr/bin/env python3
"""
Add columns to hunter_emails table
"""

import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def add_columns():
    """Add columns to hunter_emails table"""
    
    # Get database connection details from Supabase URL
    supabase_url = os.getenv("SUPABASE_URL")
    if not supabase_url:
        print("❌ SUPABASE_URL not found")
        return
    
    # Extract connection details from Supabase URL
    # Format: https://project.supabase.co
    host = supabase_url.replace("https://", "").replace("http://", "")
    database = "postgres"
    user = "postgres"
    password = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not password:
        print("❌ SUPABASE_SERVICE_ROLE_KEY not found")
        return
    
    try:
        # Connect to database
        conn = psycopg2.connect(
            host=host,
            database=database,
            user=user,
            password=password
        )
        
        cursor = conn.cursor()
        
        # Add columns
        sql = """
        ALTER TABLE hunter_emails 
        ADD COLUMN IF NOT EXISTS first_name TEXT,
        ADD COLUMN IF NOT EXISTS last_name TEXT,
        ADD COLUMN IF NOT EXISTS full_name TEXT,
        ADD COLUMN IF NOT EXISTS title TEXT,
        ADD COLUMN IF NOT EXISTS linkedin_url TEXT,
        ADD COLUMN IF NOT EXISTS confidence INTEGER;
        """
        
        cursor.execute(sql)
        conn.commit()
        
        print("✅ Columns added successfully to hunter_emails table")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error adding columns: {e}")

if __name__ == "__main__":
    add_columns() 