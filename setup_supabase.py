#!/usr/bin/env python3
"""
Supabase Database Setup Script
Creates all tables and views needed for Coogi
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_supabase():
    """Set up all Supabase tables and views"""
    
    # Get Supabase credentials
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        logger.error("❌ Supabase credentials not found in .env file")
        return False
    
    try:
        # Create Supabase client
        supabase: Client = create_client(supabase_url, supabase_key)
        logger.info("✅ Connected to Supabase")
        
        # Create tables one by one
        tables_to_create = [
            # Core tables
            """
            CREATE TABLE IF NOT EXISTS batches (
                batch_id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                status TEXT DEFAULT 'processing',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            """,
            
            """
            CREATE TABLE IF NOT EXISTS search_logs (
                id SERIAL PRIMARY KEY,
                batch_id TEXT NOT NULL,
                message TEXT NOT NULL,
                level TEXT DEFAULT 'info',
                timestamp TIMESTAMPTZ DEFAULT NOW()
            );
            """,
            
            """
            CREATE TABLE IF NOT EXISTS agent_templates (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                query TEXT NOT NULL,
                hours_old INTEGER DEFAULT 24,
                create_campaigns BOOLEAN DEFAULT FALSE,
                min_score FLOAT DEFAULT 0.5,
                cities TEXT[] DEFAULT ARRAY['United States'],
                is_default BOOLEAN DEFAULT FALSE,
                created_by TEXT DEFAULT 'system',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            """,
            
            """
            CREATE TABLE IF NOT EXISTS agent_performance (
                id SERIAL PRIMARY KEY,
                batch_id TEXT REFERENCES batches(batch_id),
                query TEXT NOT NULL,
                start_time TIMESTAMPTZ NOT NULL,
                end_time TIMESTAMPTZ,
                duration_seconds INTEGER,
                jobs_found INTEGER DEFAULT 0,
                companies_processed INTEGER DEFAULT 0,
                targets_found INTEGER DEFAULT 0,
                contacts_found INTEGER DEFAULT 0,
                campaigns_created INTEGER DEFAULT 0,
                success_rate FLOAT DEFAULT 0.0,
                error_count INTEGER DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """,
            
            """
            CREATE TABLE IF NOT EXISTS search_logs_enhanced (
                id SERIAL PRIMARY KEY,
                batch_id TEXT NOT NULL,
                message TEXT NOT NULL,
                level TEXT DEFAULT 'info',
                company TEXT,
                job_title TEXT,
                job_url TEXT,
                processing_stage TEXT,
                duration_ms INTEGER,
                metadata JSONB,
                timestamp TIMESTAMPTZ DEFAULT NOW()
            );
            """,
            
            """
            CREATE TABLE IF NOT EXISTS agent_results_summary (
                id SERIAL PRIMARY KEY,
                batch_id TEXT REFERENCES batches(batch_id),
                total_jobs INTEGER DEFAULT 0,
                total_companies INTEGER DEFAULT 0,
                target_companies INTEGER DEFAULT 0,
                skipped_companies INTEGER DEFAULT 0,
                total_contacts INTEGER DEFAULT 0,
                campaigns_created INTEGER DEFAULT 0,
                processing_time_seconds INTEGER DEFAULT 0,
                success_rate FLOAT DEFAULT 0.0,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        ]
        
        # Execute each table creation
        for i, sql in enumerate(tables_to_create):
            try:
                logger.info(f"Creating table {i+1}/{len(tables_to_create)}...")
                # Use raw SQL execution
                result = supabase.rpc('exec_sql', {'sql': sql}).execute()
                logger.info(f"✅ Table {i+1} created successfully")
            except Exception as e:
                logger.warning(f"⚠️  Table {i+1} creation failed (may already exist): {e}")
        
        # Insert default agent templates
        try:
            logger.info("Inserting default agent templates...")
            templates = [
                {
                    "name": "Healthcare - Nurses",
                    "description": "Find nursing positions across major cities",
                    "query": "nurse",
                    "hours_old": 24,
                    "create_campaigns": True,
                    "cities": ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"],
                    "is_default": True
                },
                {
                    "name": "Tech - Software Engineers",
                    "description": "Target software engineering roles",
                    "query": "software engineer",
                    "hours_old": 168,
                    "create_campaigns": True,
                    "cities": ["San Francisco", "New York", "Seattle", "Austin", "Boston"],
                    "is_default": True
                },
                {
                    "name": "Legal - Attorneys",
                    "description": "Find legal positions and law firms",
                    "query": "lawyer",
                    "hours_old": 720,
                    "create_campaigns": False,
                    "cities": ["New York", "Los Angeles", "Chicago", "Washington DC", "Boston"],
                    "is_default": True
                }
            ]
            
            for template in templates:
                supabase.table('agent_templates').insert(template).execute()
            
            logger.info("✅ Default templates inserted")
            
        except Exception as e:
            logger.warning(f"⚠️  Template insertion failed: {e}")
        
        logger.info("✅ Supabase setup completed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to set up Supabase: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Setting up Supabase database...")
    
    if setup_supabase():
        print("✅ Supabase setup completed successfully!")
    else:
        print("❌ Supabase setup failed!") 