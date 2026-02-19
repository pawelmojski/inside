#!/bin/bash
# Generic user cleanup script for Inside
# Usage: ./cleanup_user.sh <username>

set -e
set -u

if [ $# -ne 1 ]; then
    echo "Usage: $0 <username>"
    echo "Example: $0 p.mojski"
    exit 1
fi

USERNAME="$1"

PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGDATABASE="${PGDATABASE:-jumphost_db}"
PGUSER="${PGUSER:-postgres}"

echo "=========================================="
echo "Inside User Cleanup Script"
echo "=========================================="
echo "Target user: ${USERNAME}"
echo "Database: ${PGDATABASE}@${PGHOST}:${PGPORT}"
echo ""

# First verify user exists
USER_ID=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -t -A -c \
    "SELECT id FROM users WHERE username = '${USERNAME}';" 2>/dev/null || echo "")

if [ -z "$USER_ID" ]; then
    echo "❌ User '${USERNAME}' not found in database."
    exit 1
fi

echo "✓ Found user ID: ${USER_ID}"
echo ""

# Show what will be deleted
echo "Analyzing user data..."
echo ""

# Count records in each table
MFA_COUNT=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -t -A -c \
    "SELECT COUNT(*) FROM mfa_challenges WHERE user_id = ${USER_ID};" || echo "0")
    
UG_COUNT=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -t -A -c \
    "SELECT COUNT(*) FROM user_group_members WHERE user_id = ${USER_ID};" || echo "0")
    
IP_COUNT=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -t -A -c \
    "SELECT COUNT(*) FROM user_source_ips WHERE user_id = ${USER_ID};" || echo "0")
    
MAINT_COUNT=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -t -A -c \
    "SELECT COUNT(*) FROM maintenance_access WHERE person_id = ${USER_ID};" || echo "0")
    
SESSION_COUNT=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -t -A -c \
    "SELECT COUNT(*) FROM sessions WHERE person_id = ${USER_ID};" || echo "0")
    
STAY_COUNT=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -t -A -c \
    "SELECT COUNT(*) FROM stays WHERE user_id = ${USER_ID};" || echo "0")
    
POLICY_BENEF_COUNT=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -t -A -c \
    "SELECT COUNT(*) FROM access_policies WHERE user_id = ${USER_ID};" || echo "0")
    
POLICY_CREATED_COUNT=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -t -A -c \
    "SELECT COUNT(*) FROM access_policies WHERE created_by_user_id = ${USER_ID};" || echo "0")
    
AUDIT_COUNT=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -t -A -c \
    "SELECT COUNT(*) FROM audit_logs WHERE user_id = ${USER_ID};" || echo "0")

REC_COUNT=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -t -A -c \
    "SELECT COUNT(*) FROM session_recordings WHERE user_id = ${USER_ID};" 2>/dev/null || echo "0")

echo "Records to be affected:"
echo "  - MFA challenges:              ${MFA_COUNT}"
echo "  - User group memberships:      ${UG_COUNT}"
echo "  - Source IPs:                  ${IP_COUNT}"
echo "  - Maintenance access:          ${MAINT_COUNT}"
echo "  - Sessions:                    ${SESSION_COUNT}"
echo "  - Stays:                       ${STAY_COUNT}"
echo "  - Access policies (beneficiary): ${POLICY_BENEF_COUNT}"
echo "  - Access policies (created by): ${POLICY_CREATED_COUNT} (will set creator to NULL)"
echo "  - Session recordings:          ${REC_COUNT}"
echo "  - Audit logs:                  ${AUDIT_COUNT} (will be preserved)"
echo ""
echo "⚠️  WARNING: This will DELETE ALL data for user '${USERNAME}'"
echo "⚠️  This operation is IRREVERSIBLE!"
echo ""
read -p "Type 'DELETE ${USERNAME}' to confirm: " confirmation

if [ "$confirmation" != "DELETE ${USERNAME}" ]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "Starting cleanup in transaction..."
echo ""

# Use a transaction for safety
psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" <<EOF

BEGIN;

-- 1. MFA Challenges
DELETE FROM mfa_challenges WHERE user_id = ${USER_ID};

-- 2. User Group Memberships
DELETE FROM user_group_members WHERE user_id = ${USER_ID};

-- 3. User Source IPs
DELETE FROM user_source_ips WHERE user_id = ${USER_ID};

-- 4. Maintenance Access
DELETE FROM maintenance_access WHERE person_id = ${USER_ID};

-- 5. Sessions (and cascading session_transfers)
DELETE FROM sessions WHERE person_id = ${USER_ID};

-- 6. Stays
DELETE FROM stays WHERE user_id = ${USER_ID};

-- 7. Policy Audit Logs (set changed_by to NULL)
UPDATE policy_audit_log SET changed_by_user_id = NULL WHERE changed_by_user_id = ${USER_ID};

-- 8. Access Policies (set created_by to NULL for policies created by this user)
UPDATE access_policies SET created_by_user_id = NULL WHERE created_by_user_id = ${USER_ID};

-- 9. Access Policies where user is beneficiary (delete with cascades)
DELETE FROM access_policies WHERE user_id = ${USER_ID};

-- 10. Legacy access_grants (if exists)
DELETE FROM access_grants WHERE user_id = ${USER_ID};

-- 11. Session recordings metadata
DELETE FROM session_recordings WHERE user_id = ${USER_ID};

-- 12. Audit logs - PRESERVE for compliance (comment out to delete)
-- DELETE FROM audit_logs WHERE user_id = ${USER_ID};

-- 13. Finally delete the user record
DELETE FROM users WHERE id = ${USER_ID};

-- If we got here, commit
COMMIT;

-- Verify deletion
SELECT 'User deleted successfully. Remaining records:' AS status;
SELECT COUNT(*) AS remaining_users FROM users WHERE id = ${USER_ID};

EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✓ Cleanup completed successfully!"
    echo "✓ User '${USERNAME}' (ID: ${USER_ID}) removed."
    echo "=========================================="
else
    echo ""
    echo "=========================================="
    echo "❌ Cleanup failed! Transaction rolled back."
    echo "=========================================="
    exit 1
fi
