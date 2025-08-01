-- Enhanced Coogi Supabase Schema
-- Run this in your Supabase SQL editor

-- Create agent_templates table for reusable search configurations
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

-- Create agent_performance table for tracking metrics
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

-- Create agent_analytics table for detailed metrics
CREATE TABLE IF NOT EXISTS agent_analytics (
    id SERIAL PRIMARY KEY,
    batch_id TEXT REFERENCES batches(batch_id),
    metric_name TEXT NOT NULL,
    metric_value JSONB,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Create enhanced search_logs table with better structure
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

-- Create agent_suggestions table for smart recommendations
CREATE TABLE IF NOT EXISTS agent_suggestions (
    id SERIAL PRIMARY KEY,
    query TEXT NOT NULL,
    suggestion_type TEXT NOT NULL, -- 'keyword', 'parameter', 'timing'
    suggestion TEXT NOT NULL,
    reason TEXT,
    confidence FLOAT DEFAULT 0.5,
    applied BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create agent_schedules table for scheduled runs
CREATE TABLE IF NOT EXISTS agent_schedules (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    query TEXT NOT NULL,
    hours_old INTEGER DEFAULT 24,
    create_campaigns BOOLEAN DEFAULT FALSE,
    schedule_cron TEXT NOT NULL, -- cron expression
    is_active BOOLEAN DEFAULT TRUE,
    last_run TIMESTAMPTZ,
    next_run TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create agent_results_summary table for quick stats
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

-- Insert default agent templates
INSERT INTO agent_templates (name, description, query, hours_old, create_campaigns, cities, is_default) VALUES
('Healthcare - Nurses', 'Find nursing positions across major cities', 'nurse', 24, TRUE, ARRAY['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix'], TRUE),
('Tech - Software Engineers', 'Target software engineering roles', 'software engineer', 168, TRUE, ARRAY['San Francisco', 'New York', 'Seattle', 'Austin', 'Boston'], TRUE),
('Legal - Attorneys', 'Find legal positions and law firms', 'lawyer', 720, FALSE, ARRAY['New York', 'Los Angeles', 'Chicago', 'Washington DC', 'Boston'], TRUE),
('Sales - Account Executives', 'Target sales and business development roles', 'account executive', 168, TRUE, ARRAY['New York', 'Los Angeles', 'Chicago', 'Atlanta', 'Dallas'], FALSE),
('Marketing - Digital Marketing', 'Find marketing and growth positions', 'digital marketing', 168, TRUE, ARRAY['New York', 'Los Angeles', 'Chicago', 'Austin', 'Denver'], FALSE);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_agent_templates_name ON agent_templates(name);
CREATE INDEX IF NOT EXISTS idx_agent_performance_batch_id ON agent_performance(batch_id);
CREATE INDEX IF NOT EXISTS idx_agent_performance_query ON agent_performance(query);
CREATE INDEX IF NOT EXISTS idx_agent_analytics_batch_id ON agent_analytics(batch_id);
CREATE INDEX IF NOT EXISTS idx_search_logs_enhanced_batch_id ON search_logs_enhanced(batch_id);
CREATE INDEX IF NOT EXISTS idx_search_logs_enhanced_timestamp ON search_logs_enhanced(timestamp);
CREATE INDEX IF NOT EXISTS idx_agent_suggestions_query ON agent_suggestions(query);
CREATE INDEX IF NOT EXISTS idx_agent_schedules_active ON agent_schedules(is_active);
CREATE INDEX IF NOT EXISTS idx_agent_results_summary_batch_id ON agent_results_summary(batch_id);

-- Enable Row Level Security (RLS)
ALTER TABLE agent_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_performance ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_analytics ENABLE ROW LEVEL SECURITY;
ALTER TABLE search_logs_enhanced ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_suggestions ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_results_summary ENABLE ROW LEVEL SECURITY;

-- Create policies for public read access
CREATE POLICY "Allow public read access to agent_templates" ON agent_templates FOR SELECT USING (true);
CREATE POLICY "Allow public read access to agent_performance" ON agent_performance FOR SELECT USING (true);
CREATE POLICY "Allow public read access to agent_analytics" ON agent_analytics FOR SELECT USING (true);
CREATE POLICY "Allow public read access to search_logs_enhanced" ON search_logs_enhanced FOR SELECT USING (true);
CREATE POLICY "Allow public read access to agent_suggestions" ON agent_suggestions FOR SELECT USING (true);
CREATE POLICY "Allow public read access to agent_schedules" ON agent_schedules FOR SELECT USING (true);
CREATE POLICY "Allow public read access to agent_results_summary" ON agent_results_summary FOR SELECT USING (true);

-- Create policies for insert access (for the API)
CREATE POLICY "Allow insert access to agent_templates" ON agent_templates FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow insert access to agent_performance" ON agent_performance FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow insert access to agent_analytics" ON agent_analytics FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow insert access to search_logs_enhanced" ON search_logs_enhanced FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow insert access to agent_suggestions" ON agent_suggestions FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow insert access to agent_schedules" ON agent_schedules FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow insert access to agent_results_summary" ON agent_results_summary FOR INSERT WITH CHECK (true);

-- Create views for easy querying
CREATE OR REPLACE VIEW agent_dashboard_stats AS
SELECT 
    COUNT(DISTINCT batch_id) as active_agents,
    COUNT(*) as total_runs,
    SUM(jobs_found) as total_jobs,
    AVG(success_rate) as avg_success_rate,
    AVG(duration_seconds) as avg_duration
FROM agent_performance;

CREATE OR REPLACE VIEW agent_performance_summary AS
SELECT 
    query,
    COUNT(*) as run_count,
    AVG(duration_seconds) as avg_duration,
    AVG(success_rate) as avg_success_rate,
    SUM(jobs_found) as total_jobs_found,
    MAX(created_at) as last_run
FROM agent_performance 
GROUP BY query 
ORDER BY run_count DESC;

CREATE OR REPLACE VIEW recent_agent_activity AS
SELECT 
    ap.batch_id,
    ap.query,
    ap.start_time,
    ap.duration_seconds,
    ap.jobs_found,
    ap.success_rate,
    b.status as batch_status
FROM agent_performance ap
LEFT JOIN batches b ON ap.batch_id = b.batch_id
ORDER BY ap.start_time DESC
LIMIT 20; 