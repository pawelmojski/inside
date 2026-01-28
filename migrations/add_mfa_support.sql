-- Migration: Add MFA support
-- Date: 2026-01-27
-- Description: Add MFA challenges table and mfa_required field to access_policies
-- Database: PostgreSQL

-- Add mfa_required column to access_policies
ALTER TABLE access_policies ADD COLUMN IF NOT EXISTS mfa_required BOOLEAN DEFAULT FALSE NOT NULL;

-- Create mfa_challenges table
CREATE TABLE IF NOT EXISTS mfa_challenges (
    id SERIAL PRIMARY KEY,
    token VARCHAR(64) UNIQUE NOT NULL,
    gate_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    grant_id INTEGER NOT NULL,
    ssh_username VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    verified BOOLEAN DEFAULT FALSE NOT NULL,
    verified_at TIMESTAMP,
    saml_email VARCHAR(255),
    FOREIGN KEY (gate_id) REFERENCES gates(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (grant_id) REFERENCES access_policies(id) ON DELETE CASCADE
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_mfa_challenges_token ON mfa_challenges(token);
CREATE INDEX IF NOT EXISTS idx_mfa_challenges_gate_user ON mfa_challenges(gate_id, user_id);
CREATE INDEX IF NOT EXISTS idx_mfa_challenges_verified ON mfa_challenges(verified, expires_at);

-- Cleanup expired challenges (optional, can be run via cron)
-- DELETE FROM mfa_challenges WHERE expires_at < CURRENT_TIMESTAMP AND verified = FALSE;

