#!/bin/bash
# Cleanup script: Remove user p.mojski and all associated data
# WARNING: This irreversibly deletes ALL traces of the user!

set -e
set -u

PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGDATABASE="${PGDATABASE:-jumphost_db}"
PGUSER="${PGUSER:-postgres}"

USERNAME="p.mojski"

echo "=========================================="
echo "Inside User Cleanup Script"
echo "=========================================="
echo "Target user: ${USERNAME}"
echo "Database: ${PGDATABASE}@${PGHOST}:${PGPORT}"
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
USER_ID=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -t -A -c \
    "SELECT id FROM users WHERE username = '${USERNAME}';")

if [ -z "$USER_ID" ]; then
    echo "User '${USERNAME}' not found in database."
    exit 0
fi

echo "Found user ID: ${USER_ID}"
echo ""
echo "Starting cleanup (cascading deletes)..."

# Note: Many deletes will cascade automatically due to ON DELETE CASCADE
# But we'll be explicit for clarity and to show what's being deleted

# 1. MFA Challenges (CASCADE from users)
echo "1. Deleting MFA challenges..."
psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -c \
    "DELETE FROM mfa_challenges WHERE user_id = ${USER_ID};"

# 2. User Group Memberships (CASCADE from users)
echo "2. Deleting user group memberships..."
psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -c \
    "DELETE FROM user_group_members WHERE user_id = ${USER_ID};"

# 3. User Source IPs (CASCADE from users via relationship)
echo "3. Deleting user source IPs..."
psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -c \
    "DELETE FROM user_source_ips WHERE user_id = ${USER_ID};"

# 4. Maintenance Access (foreign key to users)
echo "4. Deleting maintenance access entries..."
psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -c \
    "DELETE FROM maintenance_access WHERE person_id = ${USER_ID};"

# 5. Sessions (might have active sessions)
echo "5. Deleting sessions..."
# First get session IDs for cleanup of related data
SESSION_IDS=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -t -A -c \
    "SELECT id FROM sessions WHERE person_id = ${USER_ID};" || echo "")

if [ -n "$SESSION_IDS" ]; then
    echo "   Found sessions: $(echo $SESSION_IDS | wc -w) records"
    # Session transfers will cascade (ON DELETE CASCADE)
    # Just delete sessions
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -c \
        "DELETE FROM sessions WHERE person_id = ${USER_ID};"
else
    echo "   No sessions found"
fi

# 6. Stays (person presence tracking)
echo "6. Deleting stays..."
psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -c \
    "DELETE FROM stays WHERE user_id = ${USER_ID};"

# 7. Access Policies (grants) where user is beneficiary
echo "7. Deleting access policies (where user is beneficiary)..."
POLICY_IDS=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -t -A -c \
    "SELECT id FROM access_policies WHERE user_id = ${USER_ID};" || echo "")

if [ -n "$POLICY_IDS" ]; then
    echo "   Found policies: $(echo $POLICY_IDS | wc -w) records"
    # Policy schedules and SSH logins will cascade
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -c \
        "DELETE FROM access_policies WHERE user_id = ${USER_ID};"
else
    echo "   No policies found"
fi

# 8. Policy Audit Logs (referencing this user as changed_by)
echo "8. Setting policy audit logs changed_by to NULL..."
psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -c \
    "UPDATE policy_audit_log SET changed_by_user_id = NULL WHERE changed_by_user_id = ${USER_ID};"

# 9. Access Policies created by this user (set created_by to NULL)
echo "9. Setting access policies created_by to NULL..."
psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -c \
    "UPDATE access_policies SET created_by_user_id = NULL WHERE created_by_user_id = ${USER_ID};"

# 10. Audit Logs - keep for compliance but could delete
echo "10. Keeping audit logs (compliance requirement)..."
# psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -c \
#     "DELETE FROM audit_logs WHERE user_id = ${USER_ID};"

# 11. Legacy access_grants table (if exists)
echo "11. Deleting legacy access grants (if table exists)..."
psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -c \
    "DELETE FROM access_grants WHERE user_id = ${USER_ID};" 2>/dev/null || true

# 12. Session recordings metadata
echo "12. Deleting session recordings metadata..."
psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -c \
    "DELETE FROM session_recordings WHERE user_id = ${USER_ID};" 2>/dev/null || true

# 13. Finally, delete the user record
echo "13. Deleting user record..."
psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -c \
    "DELETE FROM users WHERE id = ${USER_ID};"

echo ""
echo "=========================================="
echo "Cleanup completed successfully!"
echo "User '${USERNAME}' (ID: ${USER_ID}) has been removed."
echo "=========================================="
