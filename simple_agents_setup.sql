-- Simple Agents Table Setup Script
-- This script avoids ON CONFLICT issues by using a simpler approach

-- 1. Check current state
SELECT 'Current table structure:' as info;
SELECT 
    column_name, 
    data_type, 
    is_nullable 
FROM information_schema.columns 
WHERE table_name = 'agents' 
ORDER BY ordinal_position;

SELECT 'Current data count:' as info;
SELECT COUNT(*) as total_agents FROM agents;

-- 2. Create agents table if it doesn't exist
CREATE TABLE IF NOT EXISTS agents (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    batch_id TEXT,
    user_id UUID NOT NULL,
    user_email TEXT,
    query TEXT,
    status TEXT DEFAULT 'created',
    start_time TIMESTAMPTZ DEFAULT NOW(),
    end_time TIMESTAMPTZ,
    total_cities INTEGER DEFAULT 55,
    processed_cities INTEGER DEFAULT 0,
    processed_companies INTEGER DEFAULT 0,
    total_jobs_found INTEGER DEFAULT 0,
    hours_old INTEGER DEFAULT 720,
    create_campaigns BOOLEAN DEFAULT false,
    enforce_salary BOOLEAN DEFAULT true,
    auto_generate_messages BOOLEAN DEFAULT false,
    min_score DOUBLE PRECISION DEFAULT 0.5,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    -- Legacy columns for compatibility
    name TEXT,
    prompt TEXT,
    last_run_at TIMESTAMPTZ,
    search_lookback_hours INTEGER DEFAULT 720,
    max_results INTEGER DEFAULT 50,
    job_type TEXT DEFAULT 'fulltime',
    is_remote BOOLEAN DEFAULT true,
    country TEXT DEFAULT 'us',
    site_names TEXT[] DEFAULT ARRAY['indeed', 'linkedin', 'zip_recruiter', 'google', 'glassdoor'],
    distance INTEGER DEFAULT 25,
    is_active BOOLEAN DEFAULT true,
    autonomy_level TEXT DEFAULT 'semi-automatic',
    run_frequency TEXT DEFAULT 'Manual'
);

-- 3. Add missing columns
ALTER TABLE agents ADD COLUMN IF NOT EXISTS batch_id TEXT;
ALTER TABLE agents ADD COLUMN IF NOT EXISTS user_email TEXT;
ALTER TABLE agents ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'created';
ALTER TABLE agents ADD COLUMN IF NOT EXISTS end_time TIMESTAMPTZ;
ALTER TABLE agents ADD COLUMN IF NOT EXISTS total_cities INTEGER DEFAULT 55;
ALTER TABLE agents ADD COLUMN IF NOT EXISTS processed_cities INTEGER DEFAULT 0;
ALTER TABLE agents ADD COLUMN IF NOT EXISTS processed_companies INTEGER DEFAULT 0;
ALTER TABLE agents ADD COLUMN IF NOT EXISTS total_jobs_found INTEGER DEFAULT 0;
ALTER TABLE agents ADD COLUMN IF NOT EXISTS hours_old INTEGER DEFAULT 720;
ALTER TABLE agents ADD COLUMN IF NOT EXISTS create_campaigns BOOLEAN DEFAULT false;
ALTER TABLE agents ADD COLUMN IF NOT EXISTS enforce_salary BOOLEAN DEFAULT true;
ALTER TABLE agents ADD COLUMN IF NOT EXISTS auto_generate_messages BOOLEAN DEFAULT false;
ALTER TABLE agents ADD COLUMN IF NOT EXISTS min_score DOUBLE PRECISION DEFAULT 0.5;
ALTER TABLE agents ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE agents ADD COLUMN IF NOT EXISTS start_time TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE agents ADD COLUMN IF NOT EXISTS query TEXT;

-- 4. Create indexes
CREATE INDEX IF NOT EXISTS idx_agents_user_id ON agents(user_id);
CREATE INDEX IF NOT EXISTS idx_agents_batch_id ON agents(batch_id);
CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);
CREATE INDEX IF NOT EXISTS idx_agents_created_at ON agents(created_at);

-- 5. Enable RLS
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;

-- 6. Create RLS policies
DROP POLICY IF EXISTS "Users can view their own agents" ON agents;
CREATE POLICY "Users can view their own agents" ON agents
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert their own agents" ON agents;
CREATE POLICY "Users can insert their own agents" ON agents
    FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update their own agents" ON agents;
CREATE POLICY "Users can update their own agents" ON agents
    FOR UPDATE USING (auth.uid() = user_id);

-- 7. Insert sample data (only if no data exists for this user)
INSERT INTO agents (
    batch_id,
    user_id,
    user_email,
    query,
    status,
    start_time,
    created_at,
    total_cities,
    processed_cities,
    processed_companies,
    total_jobs_found,
    hours_old,
    create_campaigns,
    enforce_salary,
    auto_generate_messages,
    min_score,
    name,
    prompt,
    search_lookback_hours,
    max_results
) 
SELECT 
    'batch_20250801_test_001',
    'ac5d2e48-c813-498a-a328-a9b32971364f',
    'christabb@gmail.com',
    'software engineer',
    'completed',
    NOW(),
    NOW(),
    55,
    10,
    25,
    150,
    24,
    true,
    true,
    false,
    0.5,
    'Agent: software engineer',
    'software engineer',
    24,
    50
WHERE NOT EXISTS (
    SELECT 1 FROM agents 
    WHERE user_id = 'ac5d2e48-c813-498a-a328-a9b32971364f' 
    AND batch_id = 'batch_20250801_test_001'
);

-- 8. Verify results
SELECT 'Final table structure:' as info;
SELECT 
    column_name, 
    data_type, 
    is_nullable 
FROM information_schema.columns 
WHERE table_name = 'agents' 
ORDER BY ordinal_position;

SELECT 'Final data count:' as info;
SELECT COUNT(*) as total_agents FROM agents;

SELECT 'Sample agent data:' as info;
SELECT 
    batch_id,
    user_id,
    user_email,
    query,
    status,
    created_at,
    total_cities,
    processed_cities,
    processed_companies,
    total_jobs_found
FROM agents 
WHERE user_id = 'ac5d2e48-c813-498a-a328-a9b32971364f'; 