-- Update hunter_emails table to include individual contact data
-- Add new columns for structured contact data

-- Add individual contact columns
ALTER TABLE hunter_emails 
ADD COLUMN IF NOT EXISTS first_name TEXT,
ADD COLUMN IF NOT EXISTS last_name TEXT,
ADD COLUMN IF NOT EXISTS full_name TEXT,
ADD COLUMN IF NOT EXISTS title TEXT,
ADD COLUMN IF NOT EXISTS linkedin_url TEXT,
ADD COLUMN IF NOT EXISTS confidence INTEGER,
ADD COLUMN IF NOT EXISTS contact_data JSONB DEFAULT '[]';

-- Add index for the new JSONB column
CREATE INDEX IF NOT EXISTS idx_hunter_emails_contact_data ON hunter_emails USING GIN (contact_data);

-- Add indexes for the new columns
CREATE INDEX IF NOT EXISTS idx_hunter_emails_first_name ON hunter_emails(first_name);
CREATE INDEX IF NOT EXISTS idx_hunter_emails_last_name ON hunter_emails(last_name);
CREATE INDEX IF NOT EXISTS idx_hunter_emails_title ON hunter_emails(title);

-- Add comments for documentation
COMMENT ON COLUMN hunter_emails.first_name IS 'First name of the contact';
COMMENT ON COLUMN hunter_emails.last_name IS 'Last name of the contact';
COMMENT ON COLUMN hunter_emails.full_name IS 'Full name of the contact';
COMMENT ON COLUMN hunter_emails.title IS 'Job title of the contact';
COMMENT ON COLUMN hunter_emails.linkedin_url IS 'LinkedIn URL of the contact';
COMMENT ON COLUMN hunter_emails.confidence IS 'Confidence score from Hunter.io (0-100)';
COMMENT ON COLUMN hunter_emails.contact_data IS 'Array of structured contact objects with names, titles, LinkedIn URLs, etc.';

-- Example structure of contact_data:
-- [
--   {
--     "email": "jeimy.paredes@stjohns.edu",
--     "first_name": "Jeimy",
--     "last_name": "Paredes", 
--     "full_name": "Jeimy Paredes",
--     "title": "Executive Assistant",
--     "linkedin_url": "https://linkedin.com/in/jeimyparedes",
--     "confidence": 85
--   }
-- ] 