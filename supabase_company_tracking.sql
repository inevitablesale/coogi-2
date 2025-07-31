-- Company Processing Flow Tracking Tables
-- Run this in your Supabase SQL editor

-- 1. Domain Search Results
CREATE TABLE IF NOT EXISTS domain_search_results (
    id SERIAL PRIMARY KEY,
    batch_id TEXT NOT NULL,
    company TEXT NOT NULL,
    domain TEXT,
    search_success BOOLEAN DEFAULT FALSE,
    search_error TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 2. LinkedIn Page Resolution
CREATE TABLE IF NOT EXISTS linkedin_resolution (
    id SERIAL PRIMARY KEY,
    batch_id TEXT NOT NULL,
    company TEXT NOT NULL,
    linkedin_identifier TEXT,
    resolution_success BOOLEAN DEFAULT FALSE,
    resolution_error TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 3. RapidAPI Analysis Results
CREATE TABLE IF NOT EXISTS rapidapi_analysis (
    id SERIAL PRIMARY KEY,
    batch_id TEXT NOT NULL,
    company TEXT NOT NULL,
    has_ta_team BOOLEAN DEFAULT FALSE,
    contacts_found INTEGER DEFAULT 0,
    top_contacts JSONB,
    employee_roles JSONB,
    company_found BOOLEAN DEFAULT FALSE,
    analysis_success BOOLEAN DEFAULT FALSE,
    analysis_error TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Hunter.io Email Results
CREATE TABLE IF NOT EXISTS hunter_emails (
    id SERIAL PRIMARY KEY,
    batch_id TEXT NOT NULL,
    company TEXT NOT NULL,
    job_title TEXT,
    job_url TEXT,
    emails_found INTEGER DEFAULT 0,
    email_list JSONB,
    search_success BOOLEAN DEFAULT FALSE,
    search_error TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Instantly.ai Campaign Results
CREATE TABLE IF NOT EXISTS instantly_campaigns (
    id SERIAL PRIMARY KEY,
    batch_id TEXT NOT NULL,
    company TEXT NOT NULL,
    campaign_id TEXT,
    campaign_name TEXT,
    leads_added INTEGER DEFAULT 0,
    campaign_success BOOLEAN DEFAULT FALSE,
    campaign_error TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Company Processing Summary
CREATE TABLE IF NOT EXISTS company_processing_summary (
    id SERIAL PRIMARY KEY,
    batch_id TEXT NOT NULL,
    company TEXT NOT NULL,
    job_title TEXT,
    job_url TEXT,
    domain_found BOOLEAN DEFAULT FALSE,
    linkedin_resolved BOOLEAN DEFAULT FALSE,
    rapidapi_analyzed BOOLEAN DEFAULT FALSE,
    hunter_emails_found BOOLEAN DEFAULT FALSE,
    instantly_campaign_created BOOLEAN DEFAULT FALSE,
    final_recommendation TEXT,
    processing_success BOOLEAN DEFAULT FALSE,
    processing_error TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_domain_search_batch_id ON domain_search_results(batch_id);
CREATE INDEX IF NOT EXISTS idx_domain_search_company ON domain_search_results(company);
CREATE INDEX IF NOT EXISTS idx_linkedin_resolution_batch_id ON linkedin_resolution(batch_id);
CREATE INDEX IF NOT EXISTS idx_linkedin_resolution_company ON linkedin_resolution(company);
CREATE INDEX IF NOT EXISTS idx_rapidapi_analysis_batch_id ON rapidapi_analysis(batch_id);
CREATE INDEX IF NOT EXISTS idx_rapidapi_analysis_company ON rapidapi_analysis(company);
CREATE INDEX IF NOT EXISTS idx_hunter_emails_batch_id ON hunter_emails(batch_id);
CREATE INDEX IF NOT EXISTS idx_hunter_emails_company ON hunter_emails(company);
CREATE INDEX IF NOT EXISTS idx_instantly_campaigns_batch_id ON instantly_campaigns(batch_id);
CREATE INDEX IF NOT EXISTS idx_instantly_campaigns_company ON instantly_campaigns(company);
CREATE INDEX IF NOT EXISTS idx_company_processing_summary_batch_id ON company_processing_summary(batch_id);
CREATE INDEX IF NOT EXISTS idx_company_processing_summary_company ON company_processing_summary(company);

-- Create a view for easy querying of the complete flow
CREATE OR REPLACE VIEW company_processing_flow AS
SELECT 
    cps.batch_id,
    cps.company,
    cps.job_title,
    cps.job_url,
    cps.final_recommendation,
    cps.processing_success,
    cps.processing_error,
    dsr.domain,
    dsr.search_success as domain_found,
    lr.linkedin_identifier,
    lr.resolution_success as linkedin_resolved,
    ra.has_ta_team,
    ra.contacts_found,
    ra.company_found as rapidapi_company_found,
    he.emails_found,
    he.search_success as hunter_success,
    ic.campaign_id,
    ic.leads_added,
    ic.campaign_success as instantly_success,
    cps.timestamp
FROM company_processing_summary cps
LEFT JOIN domain_search_results dsr ON cps.batch_id = dsr.batch_id AND cps.company = dsr.company
LEFT JOIN linkedin_resolution lr ON cps.batch_id = lr.batch_id AND cps.company = lr.company
LEFT JOIN rapidapi_analysis ra ON cps.batch_id = ra.batch_id AND cps.company = ra.company
LEFT JOIN hunter_emails he ON cps.batch_id = he.batch_id AND cps.company = he.company
LEFT JOIN instantly_campaigns ic ON cps.batch_id = ic.batch_id AND cps.company = ic.company
ORDER BY cps.timestamp DESC; 