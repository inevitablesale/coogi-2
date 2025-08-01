-- Add user columns to agent_analytics table
-- Run this in your Supabase SQL editor

-- Add user columns to agent_analytics table
ALTER TABLE agent_analytics 
ADD COLUMN IF NOT EXISTS user_id TEXT DEFAULT 'default_user',
ADD COLUMN IF NOT EXISTS user_email TEXT DEFAULT 'default@example.com';

-- Create index for user_id for faster queries
CREATE INDEX IF NOT EXISTS idx_agent_analytics_user_id ON agent_analytics(user_id);

-- Update existing records to have default user
UPDATE agent_analytics 
SET user_id = 'default_user', user_email = 'default@example.com' 
WHERE user_id IS NULL OR user_email IS NULL;

-- Add user columns to other relevant tables
ALTER TABLE agent_performance 
ADD COLUMN IF NOT EXISTS user_id TEXT DEFAULT 'default_user',
ADD COLUMN IF NOT EXISTS user_email TEXT DEFAULT 'default@example.com';

ALTER TABLE agent_templates 
ADD COLUMN IF NOT EXISTS user_id TEXT DEFAULT 'default_user',
ADD COLUMN IF NOT EXISTS user_email TEXT DEFAULT 'default@example.com';

ALTER TABLE agent_schedules 
ADD COLUMN IF NOT EXISTS user_id TEXT DEFAULT 'default_user',
ADD COLUMN IF NOT EXISTS user_email TEXT DEFAULT 'default@example.com';

-- Create indexes for user filtering
CREATE INDEX IF NOT EXISTS idx_agent_performance_user_id ON agent_performance(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_templates_user_id ON agent_templates(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_schedules_user_id ON agent_schedules(user_id); 