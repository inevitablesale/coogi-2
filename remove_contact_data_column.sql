-- Remove contact_data column from hunter_emails table
-- Since email_list now has all the same data plus more (confidence, LinkedIn URLs)

-- Drop the contact_data column
ALTER TABLE hunter_emails DROP COLUMN IF EXISTS contact_data;

-- Drop the index for contact_data
DROP INDEX IF EXISTS idx_hunter_emails_contact_data;

-- Verify the table structure is clean
-- email_list will be our single source of truth for contact data 