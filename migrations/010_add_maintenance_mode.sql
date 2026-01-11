-- Migration 010: Add maintenance mode support
-- Date: 2026-01-11
-- Description: Adds in_maintenance fields and maintenance_access table

-- Add maintenance columns to gates
ALTER TABLE gates ADD COLUMN in_maintenance BOOLEAN DEFAULT FALSE;
ALTER TABLE gates ADD COLUMN maintenance_scheduled_at TIMESTAMP;
ALTER TABLE gates ADD COLUMN maintenance_reason TEXT;
ALTER TABLE gates ADD COLUMN maintenance_grace_minutes INTEGER DEFAULT 15;

-- Add maintenance columns to servers
ALTER TABLE servers ADD COLUMN in_maintenance BOOLEAN DEFAULT FALSE;
ALTER TABLE servers ADD COLUMN maintenance_scheduled_at TIMESTAMP;
ALTER TABLE servers ADD COLUMN maintenance_reason TEXT;
ALTER TABLE servers ADD COLUMN maintenance_grace_minutes INTEGER DEFAULT 15;

-- Create maintenance_access table for personnel with access during maintenance
CREATE TABLE maintenance_access (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(10) CHECK (entity_type IN ('gate', 'server')) NOT NULL,
    entity_id INTEGER NOT NULL,
    person_id INTEGER REFERENCES users(id) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(entity_type, entity_id, person_id)
);

-- Create index for fast lookups during authentication
CREATE INDEX idx_maintenance_access_lookup ON maintenance_access(entity_type, entity_id, person_id);

-- Reset any gates that were set to is_active=False for maintenance testing
UPDATE gates SET is_active = TRUE WHERE name = 'gate-localhost' AND is_active = FALSE;

-- Clear any lingering maintenance-related termination reasons from test sessions
UPDATE sessions SET termination_reason = NULL, denial_details = NULL 
WHERE termination_reason IN ('gate_maintenance', 'backend_maintenance') AND is_active = FALSE;
