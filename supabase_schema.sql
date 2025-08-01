-- Coogi Supabase Schema
-- Run this in your Supabase SQL editor

-- Create batches table
CREATE TABLE IF NOT EXISTS batches (
    id SERIAL PRIMARY KEY,
    batch_id TEXT UNIQUE NOT NULL,
    summary JSONB,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    status TEXT DEFAULT 'processing'
);

-- Create company_analysis table
CREATE TABLE IF NOT EXISTS company_analysis (
    id SERIAL PRIMARY KEY,
    batch_id TEXT REFERENCES batches(batch_id),
    company TEXT NOT NULL,
    job_title TEXT,
    job_url TEXT,
    has_ta_team BOOLEAN DEFAULT FALSE,
    contacts_found INTEGER DEFAULT 0,
    top_contacts JSONB,
    recommendation TEXT,
    hunter_emails TEXT[],
    instantly_campaign_id TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Create search_logs table for real-time logging
CREATE TABLE IF NOT EXISTS search_logs (
    id SERIAL PRIMARY KEY,
    batch_id TEXT NOT NULL,
    message TEXT NOT NULL,
    level TEXT DEFAULT 'info',
    company TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_batches_batch_id ON batches(batch_id);
CREATE INDEX IF NOT EXISTS idx_company_analysis_batch_id ON company_analysis(batch_id);
CREATE INDEX IF NOT EXISTS idx_company_analysis_recommendation ON company_analysis(recommendation);
CREATE INDEX IF NOT EXISTS idx_search_logs_batch_id ON search_logs(batch_id);
CREATE INDEX IF NOT EXISTS idx_search_logs_timestamp ON search_logs(timestamp);

-- Enable Row Level Security (RLS)
ALTER TABLE batches ENABLE ROW LEVEL SECURITY;
ALTER TABLE company_analysis ENABLE ROW LEVEL SECURITY;
ALTER TABLE search_logs ENABLE ROW LEVEL SECURITY;

-- Create policies for public read access (adjust as needed for your security requirements)
CREATE POLICY "Allow public read access to batches" ON batches FOR SELECT USING (true);
CREATE POLICY "Allow public read access to company_analysis" ON company_analysis FOR SELECT USING (true);
CREATE POLICY "Allow public read access to search_logs" ON search_logs FOR SELECT USING (true);

-- Create policies for insert access (for the API)
CREATE POLICY "Allow insert access to batches" ON batches FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow insert access to company_analysis" ON company_analysis FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow insert access to search_logs" ON search_logs FOR INSERT WITH CHECK (true);

-- Create a view for easy querying of search results
CREATE OR REPLACE VIEW search_results AS
SELECT 
    b.batch_id,
    b.timestamp as search_timestamp,
    b.status as search_status,
    ca.company,
    ca.job_title,
    ca.job_url,
    ca.has_ta_team,
    ca.contacts_found,
    ca.recommendation,
    ca.hunter_emails,
    ca.instantly_campaign_id,
    ca.timestamp as analysis_timestamp
FROM batches b
LEFT JOIN company_analysis ca ON b.batch_id = ca.batch_id
ORDER BY b.timestamp DESC, ca.timestamp DESC;

-- Create a view for search logs with batch info
CREATE OR REPLACE VIEW search_logs_with_batch AS
SELECT 
    sl.*,
    b.status as batch_status,
    b.summary as batch_summary
FROM search_logs sl
LEFT JOIN batches b ON sl.batch_id = b.batch_id
ORDER BY sl.timestamp DESC;

-- Insert some sample data for testing (optional)
-- INSERT INTO batches (batch_id, summary, status) VALUES 
-- ('batch_20250127_123456', '{"total_jobs": 25, "total_processed": 10}', 'completed');

-- INSERT INTO search_logs (batch_id, message, level, company) VALUES 
-- ('batch_20250127_123456', '🚀 Starting job search processing for 25 jobs', 'info', NULL),
-- ('batch_20250127_123456', '🔍 Analyzing company: TechCorp - Software Engineer', 'info', 'TechCorp'),
-- ('batch_20250127_123456', '✅ Found 5 Hunter.io emails for TechCorp', 'success', 'TechCorp'); 