-- Add destination_ip column to mfa_challenges for Phase 2 MFA
-- In Phase 2, we need to store destination IP to identify target server after SAML auth

ALTER TABLE mfa_challenges ADD COLUMN IF NOT EXISTS destination_ip VARCHAR(45);
CREATE INDEX IF NOT EXISTS idx_mfa_challenges_destination ON mfa_challenges(destination_ip);
