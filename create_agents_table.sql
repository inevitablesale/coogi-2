-- Create agents table for storing agent records
CREATE TABLE IF NOT EXISTS agents (
    id SERIAL PRIMARY KEY,
    batch_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    user_email TEXT NOT NULL,
    query TEXT NOT NULL,
    status TEXT DEFAULT 'created', -- 'created', 'processing', 'completed', 'cancelled', 'failed'
    start_time TIMESTAMPTZ DEFAULT NOW(),
    end_time TIMESTAMPTZ,
    total_cities INTEGER DEFAULT 0,
    processed_cities INTEGER DEFAULT 0,
    processed_companies INTEGER DEFAULT 0,
    total_jobs_found INTEGER DEFAULT 0,
    hours_old INTEGER DEFAULT 24,
    create_campaigns BOOLEAN DEFAULT FALSE,
    enforce_salary BOOLEAN DEFAULT TRUE,
    auto_generate_messages BOOLEAN DEFAULT FALSE,
    min_score FLOAT DEFAULT 0.5,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_agents_user_id ON agents(user_id);
CREATE INDEX IF NOT EXISTS idx_agents_batch_id ON agents(batch_id);
CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);
CREATE INDEX IF NOT EXISTS idx_agents_start_time ON agents(start_time);

-- Enable Row Level Security (RLS)
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;

-- Create policies for user-specific access
CREATE POLICY "Users can view their own agents" ON agents FOR SELECT USING (user_id = current_user);
CREATE POLICY "Users can insert their own agents" ON agents FOR INSERT WITH CHECK (user_id = current_user);
CREATE POLICY "Users can update their own agents" ON agents FOR UPDATE USING (user_id = current_user);

-- Add user columns to existing tables if they don't exist
ALTER TABLE batches ADD COLUMN IF NOT EXISTS user_id TEXT DEFAULT 'default_user';
ALTER TABLE batches ADD COLUMN IF NOT EXISTS user_email TEXT DEFAULT 'default@example.com';

-- Update existing records to have default user
UPDATE batches SET user_id = 'default_user', user_email = 'default@example.com' WHERE user_id IS NULL OR user_email IS NULL; 