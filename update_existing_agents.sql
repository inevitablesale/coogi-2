-- Update existing agents to have the correct user ID
-- This will fix the user association for existing agents

-- First, let's see what user_id values currently exist
SELECT DISTINCT user_id, user_email, COUNT(*) as count 
FROM agents 
GROUP BY user_id, user_email;

-- Update existing agents to have the correct user ID
-- Replace 'ac5d2e48-c813-498a-a328-a9b32971364f' with the actual user ID from the logs
UPDATE agents 
SET 
    user_id = 'ac5d2e48-c813-498a-a328-a9b32971364f',
    user_email = 'christabb@gmail.com'
WHERE user_id = 'default_user' OR user_email = 'user@example.com';

-- Verify the update
SELECT id, user_id, user_email, status, created_at 
FROM agents 
ORDER BY created_at DESC;

-- Check if the agents are now visible for the user
SELECT COUNT(*) as agent_count 
FROM agents 
WHERE user_id = 'ac5d2e48-c813-498a-a328-a9b32971364f'; 