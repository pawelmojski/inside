-- Manual migration: Add inactivity_timeout_minutes to access_policies
-- Date: 2026-01-22
-- Version: v1.10.9

-- Add inactivity_timeout_minutes column (default 60 minutes)
ALTER TABLE access_policies 
ADD COLUMN inactivity_timeout_minutes INTEGER DEFAULT 60;

-- Comment for documentation
COMMENT ON COLUMN access_policies.inactivity_timeout_minutes IS 
'Inactivity timeout in minutes. NULL or 0 = disabled. Session disconnects after this period of no data transmission.';

-- Verify the change
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'access_policies' 
AND column_name = 'inactivity_timeout_minutes';
