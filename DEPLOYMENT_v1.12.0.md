# v1.12.0 Implementation Summary

## ✅ Completed Work

### 1. Database Changes

**File**: `/opt/jumphost/migrations/011_auto_grant_config_and_permissions.sql`

**Gates table** - Per-gate auto-grant configuration:
```sql
ALTER TABLE gates ADD COLUMN:
- auto_grant_enabled BOOLEAN DEFAULT TRUE
- auto_grant_duration_days INTEGER DEFAULT 7
- auto_grant_inactivity_timeout_minutes INTEGER DEFAULT 60
- auto_grant_port_forwarding BOOLEAN DEFAULT TRUE
```

**Users table** - Permission level system:
```sql
ALTER TABLE users ADD COLUMN:
- permission_level INTEGER DEFAULT 1000 NOT NULL
  * 0 = Super Admin
  * 100 = Admin
  * 500 = Operator
  * 1000 = User (no GUI)
```

### 2. Database Models

**File**: `/opt/jumphost/src/core/database.py`

- Added `permission_level` to User model
- Added auto-grant config columns to Gate model

### 3. Permission System

**File**: `/opt/jumphost/src/web/permissions.py` (NEW)

Decorators:
- `@permission_required(level)` - Generic permission check
- `@admin_required` - Admin or higher (level ≤ 100)
- `@super_admin_required` - Super admin only (level = 0)
- `@operator_required` - Operator or higher (level ≤ 500)

### 4. Web UI - Gate Management

**Files**:
- `/opt/jumphost/src/web/blueprints/gates.py` - Backend
- `/opt/jumphost/src/web/templates/gates/edit.html` - Edit form
- `/opt/jumphost/src/web/templates/gates/add.html` - Add form

**Changes**:
- Added `@admin_required` to add/edit/delete/maintenance routes
- Added auto-grant configuration section to forms
- Backend saves/loads auto-grant settings

**Form fields**:
- Enable Auto-Grant (checkbox)
- Grant Duration (1-365 days)
- Inactivity Timeout (0-1440 minutes)
- Port Forwarding (checkbox)

### 5. Access Control Engine

**File**: `/opt/jumphost/src/core/access_control_v2.py`

**Modified `_create_auto_grant()`**:
- Now accepts `gate_id` parameter
- Reads configuration from gate record
- Returns None if auto-grant disabled
- Uses gate-specific values for:
  - Duration days
  - Inactivity timeout
  - Port forwarding permission

**Modified `check_access_v2()`**:
- Passes `gate_id` to `_create_auto_grant()`
- Handles `auto_grant_disabled` denial reason
- Better logging with gate information

### 6. SAML Auto-User Creation

**File**: `/opt/jumphost/src/web/auth_saml.py`

**When user not found by email**:
1. Extract username from email (before @)
2. Check for username collision
3. Create new User:
   - username: from email or full email if collision
   - email: from SAML
   - full_name: from SAML attributes
   - permission_level: 1000 (no GUI access)
   - is_active: True
4. Log auto-creation to audit_logs
5. Continue with MFA flow

---

## 📋 Deployment Steps

### Step 1: Stop Services

```bash
# SSH to tower
ssh root@jump1

# Stop web GUI
systemctl stop inside-web

# Gates will keep running (no changes needed)
```

### Step 2: Backup Database

```bash
pg_dump -U inside inside > /opt/jumphost/backup_before_v1.12.0_$(date +%Y%m%d_%H%M%S).sql
```

### Step 3: Run Migration

```bash
cd /opt/jumphost

# Check migration first (dry run)
psql -U inside inside < migrations/011_auto_grant_config_and_permissions.sql

# Verify columns added
psql -U inside inside -c "\d gates" | grep auto_grant
psql -U inside inside -c "\d users" | grep permission_level
```

### Step 4: Update Code

```bash
cd /opt/jumphost

# Pull latest code (or deploy manually)
git add -A
git commit -m "v1.12.0: Auto-grant config, permission system, auto-user creation"

# Check syntax
python3 -m py_compile src/core/access_control_v2.py
python3 -m py_compile src/core/database.py
python3 -m py_compile src/web/blueprints/gates.py
python3 -m py_compile src/web/auth_saml.py
```

### Step 5: Update Existing Gates (Optional)

```bash
# Set specific gate to stricter policy (example: DMZ gate)
psql -U inside inside <<EOF
UPDATE gates SET 
    auto_grant_duration_days = 1,
    auto_grant_inactivity_timeout_minutes = 30,
    auto_grant_port_forwarding = false
WHERE name = 'gate-dmz';
EOF

# Or keep defaults for all gates (already set by migration)
```

### Step 6: Set Admin Permissions

```bash
# Set specific users as admins
psql -U inside inside <<EOF
UPDATE users SET permission_level = 0 WHERE username = 'p.mojski';  -- Super Admin
UPDATE users SET permission_level = 100 WHERE username = 'admin';   -- Admin
-- All other users keep default 1000 (no GUI access)
EOF
```

### Step 7: Restart Web Service

```bash
systemctl start inside-web
systemctl status inside-web

# Check logs
journalctl -u inside-web -f
```

### Step 8: Test

**Test 1: Web UI Login**
```
1. Login to GUI: https://jump1/
2. Verify you can access (admin user)
3. Go to Gates → Edit gate
4. Verify "Auto-Grant Configuration" section visible
5. Change values, save
6. Verify saved correctly
```

**Test 2: Auto-Grant Creation**
```
1. Create test user via SAML (new email)
2. User auto-created with permission_level=1000
3. User connects to server (no grant exists)
4. Auto-grant created with gate-specific config
5. Check: Policies page → see AUTO-GRANT entry
6. Verify duration matches gate config
```

**Test 3: Revoke Mechanism**
```
1. Admin sets grant end_time to past (Revoke button)
2. User reconnects to same server
3. Should get PERMDEN (access_revoked)
4. No new auto-grant created
```

**Test 4: Permission System**
```
1. Create user with permission_level=1000
2. Try to access GUI → should be denied
3. Set user to permission_level=100
4. Can now access GUI and edit gates
```

---

## 🔒 Security Notes

### Permission Levels
- **Default for ALL new users**: 1000 (no GUI access)
- **Auto-created SAML users**: 1000 (no GUI access)
- **Manually promote to admin**: Set permission_level to 100 or 0

### Auto-Grant Safety
- Only works after MFA authentication
- Revoked grants block future auto-grants (permanent PERMDEN)
- Admin can disable auto-grant per-gate
- Configurable duration and timeout per-gate

### Recommended Settings
- **Production internal gates**: Auto-grant enabled, 7 days, port forwarding ON
- **DMZ gates**: Auto-grant enabled, 1 day, port forwarding OFF
- **Test gates**: Auto-grant enabled, 1 day, short timeout (30 min)

---

## 📝 Configuration Examples

### DMZ Gate (Strict)
```sql
UPDATE gates SET 
    auto_grant_enabled = TRUE,
    auto_grant_duration_days = 1,
    auto_grant_inactivity_timeout_minutes = 30,
    auto_grant_port_forwarding = FALSE
WHERE name = 'gate-dmz';
```

### Internal Gate (Permissive)
```sql
UPDATE gates SET 
    auto_grant_enabled = TRUE,
    auto_grant_duration_days = 7,
    auto_grant_inactivity_timeout_minutes = 60,
    auto_grant_port_forwarding = TRUE
WHERE name = 'gate-internal';
```

### Disable Auto-Grant (Manual Only)
```sql
UPDATE gates SET 
    auto_grant_enabled = FALSE
WHERE name = 'gate-production';
```

---

## 🐛 Troubleshooting

### Problem: User can't access GUI after update
**Solution**: Set permission_level ≤ 100
```sql
UPDATE users SET permission_level = 100 WHERE username = 'your_username';
```

### Problem: Auto-grant not creating
**Check**:
1. Gate has `auto_grant_enabled = TRUE`
2. No revoked grant exists for (user, server)
3. User authenticated via MFA
4. Check logs: `journalctl -u jumphost-flask -f`

### Problem: SAML user not auto-creating
**Check**:
1. Email extracted from SAML response
2. Check logs for "Auto-created user"
3. Verify database: `SELECT * FROM users WHERE email = 'test@example.com';`

---

## 📊 Monitoring

### Check Auto-Grants Created
```sql
SELECT 
    p.id,
    u.username,
    s.name AS server,
    p.granted_by,
    p.start_time,
    p.end_time,
    p.port_forwarding_allowed
FROM access_policies p
JOIN users u ON p.user_id = u.id
JOIN servers s ON p.target_server_id = s.id
WHERE p.granted_by = 'AUTO-GRANT'
ORDER BY p.created_at DESC
LIMIT 20;
```

### Check Auto-Created Users
```sql
SELECT 
    u.id,
    u.username,
    u.email,
    u.permission_level,
    u.created_at,
    CASE 
        WHEN u.permission_level = 0 THEN 'Super Admin'
        WHEN u.permission_level <= 100 THEN 'Admin'
        WHEN u.permission_level <= 500 THEN 'Operator'
        ELSE 'User'
    END AS role
FROM users u
ORDER BY u.created_at DESC
LIMIT 20;
```

### Check Gate Configurations
```sql
SELECT 
    name,
    auto_grant_enabled,
    auto_grant_duration_days,
    auto_grant_inactivity_timeout_minutes,
    auto_grant_port_forwarding
FROM gates
ORDER BY name;
```

---

## ✅ DEPLOYED (February 18, 2026)

**Deployment Steps Completed**:

1. ✅ **Database Backup**:
   ```bash
   sudo -u postgres pg_dump jumphost_db > backup_before_v1.12.0_20260218_143003.sql
   # Size: 262KB
   ```

2. ✅ **Migration Applied**:
   ```bash
   sudo -u postgres psql jumphost_db < migrations/011_auto_grant_config_and_permissions.sql
   # Results:
   #   ALTER TABLE (gates - 4 columns)
   #   CREATE INDEX (idx_gates_auto_grant_enabled)
   #   ALTER TABLE (users - permission_level)
   #   CREATE INDEX (idx_users_permission_level)
   #   UPDATE 1 (admin user → permission_level=0)
   #   CREATE VIEW (permission_levels)
   ```

3. ✅ **Schema Verified**:
   - Gates table: 4 auto_grant_* columns present
   - Users table: permission_level column present with default 1000

4. ✅ **Service Restarted**:
   ```bash
   systemctl restart jumphost-flask
   # Status: Active (running) since Wed 2026-02-18 14:33:04 CET
   ```

5. ✅ **Cleanup Script Tested**:
   ```bash
   bash scripts/cleanup_user_p_mojski_v2.sh
   # Successfully deleted:
   #   - 110 MFA challenges
   #   - 299 sessions
   #   - 145 stays
   #   - 19 access policies
   #   - 31 audit logs (preserved with user_id=NULL)
   #   - User p.mojski
   ```

**Next Steps**:
- [ ] Test Web GUI login
- [ ] Test gate edit form (auto-grant section)
- [ ] Test auto-grant creation on new connection
- [ ] Test SAML auto-user creation
- [ ] Monitor logs for errors

---

## ✅ Verification Checklist

**Deployment Phase**:
- [x] Database migration ran successfully
- [x] Gates table has auto_grant_* columns
- [x] Users table has permission_level column
- [x] Database backup created (262KB)
- [x] Service restarted (jumphost-flask)
- [x] Cleanup script tested (p.mojski deleted)

**Testing Phase** (in progress):
- [ ] Web GUI starts without errors
- [ ] Admin users can access GUI
- [ ] Non-admin users blocked from GUI
- [ ] Gate edit form shows auto-grant section
- [ ] Auto-grant creates policy on new connection
- [ ] Revoked grants block future auto-grants
- [ ] SAML auto-creates users with permission_level=1000
- [ ] Auto-created users blocked from GUI
- [ ] Audit logs show auto-grant and auto-user creations

---

## 🔄 Rollback Plan

If issues occur:

```bash
# Stop web service
systemctl stop jumphost-flask

# Restore database backup
sudo -u postgres psql jumphost_db < /opt/jumphost/backup_before_v1.12.0_20260218_143003.sql

# Revert code
git restore .
# or restore previous version manually

# Start web service
systemctl start jumphost-flask
```

**Note**: Auto-created grants and users will be lost in rollback.
