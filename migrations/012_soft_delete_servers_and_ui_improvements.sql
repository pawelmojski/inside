-- Migration 012: Soft Delete for Servers + UI Improvements
-- Date: 2026-02-18
-- Description: Add soft-delete columns to servers table for history preservation

BEGIN;

-- Add soft-delete columns to servers
ALTER TABLE servers 
  ADD COLUMN deleted BOOLEAN DEFAULT FALSE NOT NULL,
  ADD COLUMN deleted_at TIMESTAMP,
  ADD COLUMN deleted_by_user_id INTEGER REFERENCES users(id);

-- Index for fast filtering of active servers
CREATE INDEX idx_servers_deleted ON servers(deleted) WHERE deleted = FALSE;

-- Add comments
COMMENT ON COLUMN servers.deleted IS 'Soft delete flag - preserves history for stays/sessions';
COMMENT ON COLUMN servers.deleted_at IS 'Timestamp when server was deleted';
COMMENT ON COLUMN servers.deleted_by_user_id IS 'Admin user who deleted this server';

COMMIT;
