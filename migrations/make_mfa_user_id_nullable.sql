-- Migration: Make user_id nullable in mfa_challenges for Phase 2 MFA
-- In Phase 2, user is identified via SAML email AFTER challenge is created

ALTER TABLE mfa_challenges ALTER COLUMN user_id DROP NOT NULL;
ALTER TABLE mfa_challenges ALTER COLUMN grant_id DROP NOT NULL;

-- Drop the existing index and recreate it to allow NULL values
DROP INDEX IF EXISTS idx_mfa_challenges_gate_user;
CREATE INDEX idx_mfa_challenges_gate_user ON mfa_challenges(gate_id, user_id) WHERE user_id IS NOT NULL;

-- Add index for token lookup (primary lookup method)
CREATE INDEX IF NOT EXISTS idx_mfa_challenges_token ON mfa_challenges(token);
