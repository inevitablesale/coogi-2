-- Fix missing columns in agents table
-- This script will add any missing columns that the API expects

-- Check what columns currently exist
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'agents' 
ORDER BY ordinal_position;

-- Add missing columns that the API expects
ALTER TABLE agents ADD COLUMN IF NOT EXISTS start_time TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE agents ADD COLUMN IF NOT EXISTS end_time TIMESTAMPTZ;
ALTER TABLE agents ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'created';
ALTER TABLE agents ADD COLUMN IF NOT EXISTS batch_id TEXT;
ALTER TABLE agents ADD COLUMN IF NOT EXISTS user_email TEXT;
ALTER TABLE agents ADD COLUMN IF NOT EXISTS query TEXT;
ALTER TABLE agents ADD COLUMN IF NOT EXISTS total_cities INTEGER DEFAULT 55;
ALTER TABLE agents ADD COLUMN IF NOT EXISTS processed_cities INTEGER DEFAULT 0;
ALTER TABLE agents ADD COLUMN IF NOT EXISTS processed_companies INTEGER DEFAULT 0;
ALTER TABLE agents ADD COLUMN IF NOT EXISTS total_jobs_found INTEGER DEFAULT 0;
ALTER TABLE agents ADD COLUMN IF NOT EXISTS hours_old INTEGER DEFAULT 24;
ALTER TABLE agents ADD COLUMN IF NOT EXISTS create_campaigns BOOLEAN DEFAULT FALSE;
ALTER TABLE agents ADD COLUMN IF NOT EXISTS enforce_salary BOOLEAN DEFAULT TRUE;
ALTER TABLE agents ADD COLUMN IF NOT EXISTS auto_generate_messages BOOLEAN DEFAULT FALSE;
ALTER TABLE agents ADD COLUMN IF NOT EXISTS min_score FLOAT DEFAULT 0.5;
ALTER TABLE agents ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Update existing records to have proper values
UPDATE agents SET 
    start_time = created_at,
    status = CASE 
        WHEN last_run_at IS NOT NULL THEN 'completed'
        ELSE 'created'
    END,
    query = prompt,
    user_email = 'user@example.com'
WHERE start_time IS NULL OR status IS NULL OR query IS NULL OR user_email IS NULL;

-- Create indexes for the new columns
CREATE INDEX IF NOT EXISTS idx_agents_start_time ON agents(start_time);
CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);
CREATE INDEX IF NOT EXISTS idx_agents_batch_id ON agents(batch_id);

-- Show the final table structure
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'agents' 
ORDER BY ordinal_position; 