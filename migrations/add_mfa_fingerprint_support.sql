-- Migration: Add MFA fingerprint-based session support
-- Date: 2026-01-27
-- Description: Add ssh_key_fingerprint to stays and mfa_enabled to gates

-- Add MFA enabled flag to gates
ALTER TABLE gates ADD COLUMN mfa_enabled BOOLEAN DEFAULT FALSE NOT NULL;
COMMENT ON COLUMN gates.mfa_enabled IS 'If true, gate uses MFA for unknown IPs with fingerprint-based sessions';

-- Add SSH key fingerprint to stays for session persistence
ALTER TABLE stays ADD COLUMN ssh_key_fingerprint VARCHAR(255);
COMMENT ON COLUMN stays.ssh_key_fingerprint IS 'SSH public key fingerprint (SHA256) used for session identification across IPs';

-- Index for fast fingerprint lookups
CREATE INDEX idx_stays_fingerprint ON stays(ssh_key_fingerprint, is_active) WHERE ssh_key_fingerprint IS NOT NULL;

-- Show results
SELECT 'Gates MFA enabled column added' AS status;
SELECT 'Stays fingerprint column added' AS status;
SELECT 'Fingerprint index created' AS status;
