#!/bin/bash
# Cleanup script: Remove user p.mojski and all associated data
# Uses sudo -u postgres for peer authentication

set -e
set -u

USERNAME="p.mojski"

echo "=========================================="
echo "Inside User Cleanup Script v2"
echo "=========================================="
echo "Target user: ${USERNAME}"
echo "Database: jumphost_db"
echo ""
echo "WARNING: This will DELETE ALL data for user ${USERNAME}:"
echo "  - User record"
echo "  - Access policies (grants)"
echo "  - Stays (presence tracking)"
echo "  - Sessions (connection history)"
echo "  - MFA challenges"
echo "  - Source IPs"
echo "  - User group memberships"
echo "  - Audit logs"
echo "  - Maintenance access entries"
echo ""
read -p "Are you sure? Type 'YES' to confirm: " confirmation

if [ "$confirmation" != "YES" ]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "Looking up user ID..."

# Get user ID
USER_ID=$(sudo -u postgres psql jumphost_db -t -A -c \
    "SELECT id FROM users WHERE username = '${USERNAME}';")

if [ -z "$USER_ID" ]; then
    echo "User '${USERNAME}' not found in database."
    exit 0
fi

echo "Found user ID: ${USER_ID}"
echo ""
echo "Starting cleanup in transaction..."

# Single transaction for all deletes
sudo -u postgres psql jumphost_db <<EOF
BEGIN;

-- 1. MFA Challenges
DELETE FROM mfa_challenges WHERE user_id = ${USER_ID};

-- 2. User Group Memberships
DELETE FROM user_group_members WHERE user_id = ${USER_ID};

-- 3. User Source IPs
DELETE FROM user_source_ips WHERE user_id = ${USER_ID};

-- 4. Maintenance Access
DELETE FROM maintenance_access WHERE person_id = ${USER_ID};

-- 5. Sessions
DELETE FROM sessions WHERE user_id = ${USER_ID};

-- 6. Stays
DELETE FROM stays WHERE user_id = ${USER_ID};

-- 7. Access Policies (grants)
DELETE FROM access_policies WHERE user_id = ${USER_ID};

-- 8. Audit Logs - SET NULL to preserve history
UPDATE audit_logs SET user_id = NULL WHERE user_id = ${USER_ID};

-- 9. Finally, delete the user
DELETE FROM users WHERE id = ${USER_ID};

COMMIT;

-- Verify deletion
SELECT CASE 
    WHEN COUNT(*) = 0 THEN 'SUCCESS: User deleted'
    ELSE 'ERROR: User still exists'
END AS result
FROM users WHERE id = ${USER_ID};
EOF

echo ""
echo "=========================================="
echo "Cleanup complete!"
echo "=========================================="
