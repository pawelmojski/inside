-- Migration: Add auto-grant configuration to gates and permission levels to users
-- Version: v1.12.0
-- Date: 2026-02-18
-- Description: 
--   1. Add auto-grant configuration columns to gates table (per-gate control)
--   2. Add permission_level to users table (admin/user role system)

-- ============================================================================
-- PART 1: Gates Auto-Grant Configuration
-- ============================================================================

-- Add auto-grant configuration columns
-- NULL = inherit from global config (default behavior)
-- Non-NULL = override global config for this specific gate

ALTER TABLE gates 
    ADD COLUMN auto_grant_enabled BOOLEAN DEFAULT TRUE,
    ADD COLUMN auto_grant_duration_days INTEGER DEFAULT 7,
    ADD COLUMN auto_grant_inactivity_timeout_minutes INTEGER DEFAULT 60,
    ADD COLUMN auto_grant_port_forwarding BOOLEAN DEFAULT TRUE;

-- Add indexes for performance
CREATE INDEX idx_gates_auto_grant_enabled ON gates(auto_grant_enabled) 
    WHERE auto_grant_enabled IS NOT NULL;

-- Add column comments for documentation
COMMENT ON COLUMN gates.auto_grant_enabled IS 
    'Enable auto-grant creation for this gate. TRUE=enabled, FALSE=disabled. Default: TRUE.';
COMMENT ON COLUMN gates.auto_grant_duration_days IS 
    'Auto-grant duration in days. Default: 7 days. Min: 1, Max: 365.';
COMMENT ON COLUMN gates.auto_grant_inactivity_timeout_minutes IS 
    'Session inactivity timeout in minutes. Default: 60. 0 or NULL = disabled.';
COMMENT ON COLUMN gates.auto_grant_port_forwarding IS 
    'Allow port forwarding in auto-grants. TRUE=allowed, FALSE=denied. Default: TRUE.';

-- ============================================================================
-- PART 2: Users Permission Level System
-- ============================================================================

-- Add permission_level column to users table
-- Lower number = higher privileges
-- 0 = Super Admin (full access)
-- 100 = Admin (manage users, policies, gates)
-- 500 = Operator (view only, manage sessions)
-- 1000 = Regular User (no GUI access)

ALTER TABLE users 
    ADD COLUMN permission_level INTEGER DEFAULT 1000 NOT NULL;

-- Create index for permission checks
CREATE INDEX idx_users_permission_level ON users(permission_level);

-- Add column comment
COMMENT ON COLUMN users.permission_level IS 
    'Permission level: 0=SuperAdmin, 100=Admin, 500=Operator, 1000=User (no GUI). Lower = more privileges.';

-- Set existing admin user to super admin (if exists)
UPDATE users 
SET permission_level = 0 
WHERE username = 'admin' OR email LIKE '%admin%';

-- ============================================================================
-- PART 3: Create permission level constants view (optional)
-- ============================================================================

-- Create view for permission level reference
CREATE OR REPLACE VIEW permission_levels AS
SELECT 
    0 AS level, 'Super Admin' AS name, 'Full system access' AS description
UNION ALL SELECT 
    100, 'Admin', 'Manage users, policies, gates, servers'
UNION ALL SELECT 
    500, 'Operator', 'View-only access, manage active sessions'
UNION ALL SELECT 
    1000, 'User', 'No GUI access (SSH/RDP only)';

COMMENT ON VIEW permission_levels IS 
    'Reference view for permission level constants';

-- ============================================================================
-- VALIDATION
-- ============================================================================

-- Show gates with auto-grant configuration
-- SELECT name, auto_grant_enabled, auto_grant_duration_days, 
--        auto_grant_inactivity_timeout_minutes, auto_grant_port_forwarding
-- FROM gates;

-- Show users with permission levels
-- SELECT username, email, permission_level,
--        CASE 
--          WHEN permission_level = 0 THEN 'Super Admin'
--          WHEN permission_level <= 100 THEN 'Admin'
--          WHEN permission_level <= 500 THEN 'Operator'
--          ELSE 'User'
--        END AS role
-- FROM users
-- ORDER BY permission_level;

-- ============================================================================
-- ROLLBACK (if needed)
-- ============================================================================

-- To rollback this migration:
-- ALTER TABLE gates DROP COLUMN auto_grant_enabled;
-- ALTER TABLE gates DROP COLUMN auto_grant_duration_days;
-- ALTER TABLE gates DROP COLUMN auto_grant_inactivity_timeout_minutes;
-- ALTER TABLE gates DROP COLUMN auto_grant_port_forwarding;
-- ALTER TABLE users DROP COLUMN permission_level;
-- DROP VIEW IF EXISTS permission_levels;
