# Auto-Registration Design for "Opening Inside to the World"

## IMPLEMENTATION STATUS

✅ **IMPLEMENTED** - auto_grant_create (v1.12.0)
- **Location**: `src/core/access_control_v2.py` - `_create_auto_grant()` method
- **Trigger**: When user connects to server with no matching policy (user or group)
- **Before creating**: Checks if revoked grant exists (expired AccessPolicy for user+server)
- **If revoked**: Returns PERMDEN, no auto-grant created
- **If not revoked**: Creates auto-grant with 7 days validity

**Auto-grant properties** (as implemented):
- **Validity**: 7 days from creation (strict, no auto-renewal)
- **Scope**: Server-level (`scope_type='server'`)
- **Permissions**: Full (port_forwarding_allowed=True)
- **SSH logins**: No restrictions (empty PolicySSHLogin = allow all)
- **Schedules**: No restrictions (use_schedules=False)
- **MFA**: Not required (mfa_required=False)
- **Inactivity timeout**: 60 minutes
- **Granted by**: 'AUTO-GRANT' (system marker)
- **Created by user_id**: NULL (system-created)

**Revoke mechanism** (as implemented):
- Admin revokes by setting `end_time` to past (existing behavior)
- Before auto-grant creation: Query for expired AccessPolicy (user_id + target_server_id + end_time < now)
- If found → Return denial_reason='access_revoked'
- Active sessions killed by existing heartbeat mechanism

**Flow**:
```
Gate → /api/v1/auth/check → check_access_v2() →
  1. Find user by source_ip
  2. Find server by destination_ip
  3. Check user policies → empty
  4. Check group policies → empty
  5. Query revoked grants (expired AccessPolicy for user+server)
     → If found: DENY (access_revoked)
     → If not found: CREATE auto-grant (7 days)
  6. Continue with normal flow (schedule check, SSH login check)
```

---

## Problem Statement

When opening Inside to external users, we need to handle three scenarios automatically:
1. **Unknown user** authenticates via SAML (email not in database)
2. **Unknown server** is accessed (destination IP not in database)
3. **Missing grant** between user and server

Currently all three result in rejection. We need auto-creation to avoid manual support overhead.

---

## Current Flow (Rejection)

```
User connects → MFA Challenge created
              → SAML auth returns email
              → Query User by email
              → NOT FOUND → 403 Error ❌
```

```
Known user connects to unknown IP
              → Check grant (check_grant function)
              → Query Server by IP
              → NOT FOUND → reject connection ❌
```

---

## Design #1: Full Auto-Registration (Permissive)

### auto_person_create (in auth_saml.py)

**When**: SAML auth returns email not in database  
**Action**:
```python
# Extract SAML attributes
saml_email = nameid.lower()
saml_name = attributes.get('name', [saml_email.split('@')[0]])[0]
saml_groups = attributes.get('groups', [])

# Create user record
new_user = User(
    username=saml_email,  # or extract from email: p.mojski@inside.com → p.mojski
    email=saml_email,
    full_name=saml_name,
    is_active=True,
    port_forwarding_allowed=False  # restrictive default
)
db.add(new_user)
db.flush()

# Add to default user group
default_group = db.query(UserGroup).filter(UserGroup.name == "Auto-Registered Users").first()
if default_group:
    member = UserGroupMember(user_id=new_user.id, user_group_id=default_group.id)
    db.add(member)

# Audit log
audit = AuditLog(
    user_id=new_user.id,
    action="auto_person_create",
    details=f"Auto-created from SAML: {saml_email}",
    source_ip=request.remote_addr
)
db.add(audit)
db.commit()

# TODO: Send alert to admins
```

**Requirements**:
- UserGroup "Auto-Registered Users" must exist
- Consider: Username collision (p.mojski already exists from different domain)
  - Solution: Use full email or add domain suffix

---

### auto_server_create (in grants.py or access_control.py)

**When**: User connects to unknown destination IP  
**Where**: In `check_grant()` before rejecting connection  
**Action**:

```python
# In check_grant() function
server = db.query(Server).filter(Server.destination_ip == dest_ip).first()
if not server:
    # AUTO-CREATE SERVER
    try:
        # Try reverse DNS
        import socket
        hostname = socket.gethostbyaddr(dest_ip)[0]
    except:
        hostname = f"auto-{dest_ip.replace('.', '-')}"
    
    new_server = Server(
        name=hostname,
        destination_ip=dest_ip,
        is_active=True,
        protocol='ssh',  # default, can upgrade to rdp later
        port=22  # assume SSH
    )
    db.add(new_server)
    db.flush()
    
    # Add to auto-registered servers group
    auto_group = db.query(ServerGroup).filter(ServerGroup.name == "Auto-Discovered").first()
    if auto_group:
        db.execute(server_group_members.insert().values(
            server_id=new_server.id,
            server_group_id=auto_group.id
        ))
    
    # Audit
    audit = AuditLog(
        user_id=user_id,
        action="auto_server_create",
        details=f"Auto-discovered: {dest_ip} → {hostname}",
        source_ip=source_ip
    )
    db.add(audit)
    db.commit()
    
    server = new_server  # Continue with grant check
```

**Requirements**:
- ServerGroup "Auto-Discovered" must exist
- Consider: IP might be invalid/unreachable
  - Solution: Mark as pending_verification, admin review required
- Consider: Security risk (any IP can be auto-added)
  - Solution: Limit to specific IP ranges (config.yaml)

---

### auto_grant_create (in grants.py)

**When**: User connects to server but no grant exists  
**Where**: In `check_grant()` after user and server both exist  
**Action**:

```python
# In check_grant() after ensuring user and server exist
grant = check_existing_grant(user_id, server_id)
if not grant:
    # Check if auto-grant is enabled globally
    if not config.get('auto_grant_enabled', False):
        return None  # Reject as before
    
    # Create temporary auto-grant
    auto_policy = AccessPolicy(
        user_id=user_id,
        server_id=server_id,
        created_by_user_id=None,  # System-created
        protocol='ssh',
        valid_from=datetime.utcnow(),
        valid_to=datetime.utcnow() + timedelta(hours=8),  # 8h default
        is_active=True,
        require_mfa=True,
        port_forwarding_allowed=False,
        clipboard_up=True,
        clipboard_down=True,
        file_transfer_up=True,
        file_transfer_down=True
    )
    db.add(auto_policy)
    
    # Add default SSH login (username from user.username)
    ssh_login = AccessPolicySSHLogin(
        policy_id=auto_policy.id,
        ssh_login=user.username.split('@')[0]  # p.mojski@inside.com → p.mojski
    )
    db.add(ssh_login)
    
    # Audit
    audit = AuditLog(
        user_id=user_id,
        action="auto_grant_create",
        details=f"Auto-grant: {user.username} → {server.name} (expires {auto_policy.valid_to})",
        source_ip=source_ip
    )
    db.add(audit)
    db.commit()
    
    return auto_policy
```

**Requirements**:
- Feature flag: `config['auto_grant_enabled']`
- Default expiry: 8 hours (configurable)
- Default SSH login: derived from user.username
- Consider: Grant might be too permissive
  - Solution: Minimal permissions by default, user can request elevation

---

## Design #2: Hybrid (Semi-Automatic)

### Option A: Auto-Create User, Manual Grant

- ✅ Auto-create user from SAML (low risk)
- ❌ No auto-server, no auto-grant
- User sees "No access to this server" → clicks "Request Access" → admin approves

**Pros**: More control, audit trail  
**Cons**: Still requires admin intervention (defeats purpose)

---

### Option B: Auto-Create via User Groups

- Create UserGroup "Auto-Access-Enabled" 
- Only users in this group get auto-grants
- Everyone else follows manual approval

**Pros**: Gradual rollout, per-user control  
**Cons**: Admins must manually add users to group (still overhead)

---

### Option C: Auto-Create with IP Whitelist

- Auto-grant only for connections to specific IP ranges
- E.g., `10.30.0.0/16` (internal network) → auto-grant
- External IPs → manual approval

**Pros**: Security boundary, safe for internal  
**Cons**: Requires defining trusted ranges

---

## Configuration Schema

Add to `config/settings.yaml`:

```yaml
auto_registration:
  enabled: true
  
  person:
    enabled: true
    default_user_group: "Auto-Registered Users"
    extract_username_from_email: true  # p.mojski@inside.com → p.mojski
    port_forwarding_allowed: false
    
  server:
    enabled: true
    default_server_group: "Auto-Discovered"
    allowed_ip_ranges:
      - "10.0.0.0/8"
      - "172.16.0.0/12"
    perform_reverse_dns: true
    default_protocol: "ssh"
    default_port: 22
    
  grant:
    enabled: true
    default_expiry_hours: 8
    require_mfa: true
    port_forwarding_allowed: false
    default_permissions:
      clipboard_up: true
      clipboard_down: true
      file_transfer_up: true
      file_transfer_down: true
      
  notifications:
    send_admin_alerts: true
    alert_emails:
      - "admin@inside.com"
```

---

## Database Changes Required

### 1. Create Default Groups

```sql
-- User group for auto-registered users
INSERT INTO user_groups (name, description, is_active)
VALUES ('Auto-Registered Users', 'Users created automatically via SAML', true);

-- Server group for auto-discovered servers
INSERT INTO server_groups (name, description)
VALUES ('Auto-Discovered', 'Servers discovered automatically from connection attempts');
```

### 2. Add Feature Flags Table (optional)

```sql
CREATE TABLE feature_flags (
    id SERIAL PRIMARY KEY,
    feature_name VARCHAR(255) UNIQUE NOT NULL,
    enabled BOOLEAN DEFAULT FALSE,
    config JSONB,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO feature_flags (feature_name, enabled, config)
VALUES (
    'auto_registration',
    true,
    '{"person": true, "server": true, "grant": true}'::jsonb
);
```

---

## Implementation Plan

### Phase 1: auto_person_create (Low Risk)
1. Modify `src/web/auth_saml.py` lines 194-207
2. Add User creation logic
3. Add audit logging
4. Test with new SAML user
5. Deploy with feature flag OFF
6. Enable for testing, monitor logs
7. Enable for production

### Phase 2: auto_server_create (Medium Risk)
1. Modify `src/core/access_control.py` check_grant()
2. Add Server creation logic
3. Add IP range validation
4. Add reverse DNS lookup
5. Test with unknown server
6. Deploy with feature flag OFF
7. Enable gradually per IP range

### Phase 3: auto_grant_create (High Risk)
1. Modify `src/core/access_control.py` check_grant()
2. Add AccessPolicy creation logic
3. Add expiry logic
4. Add SSH login derivation
5. Test end-to-end flow
6. Deploy with feature flag OFF
7. Enable for pilot users only
8. Monitor for abuse
9. Roll out gradually

---

## Security Considerations

### Risks

1. **Unauthorized Access**: Anyone with valid SAML can access any internal server
   - Mitigation: IP range limits, short expiry, audit alerts
   
2. **Resource Exhaustion**: Attacker creates thousands of user/server records
   - Mitigation: Rate limiting, CAPTCHA on SAML, monitoring
   
3. **Privilege Escalation**: Auto-grant might be too permissive
   - Mitigation: Minimal default permissions, require explicit elevation
   
4. **Data Exfiltration**: Port forwarding, clipboard, file transfer all enabled
   - Mitigation: Disable by default, require justification for elevation

### Mitigations

- **Audit Everything**: Log all auto-creations prominently
- **Alert Admins**: Email on every auto-creation (at least initially)
- **Short Expiry**: Auto-grants expire in 8 hours max
- **Review Dashboard**: Admin page showing all auto-created entities
- **Feature Flags**: Kill switch to disable instantly
- **Gradual Rollout**: Enable per user group first
- **IP Whitelisting**: Only allow trusted ranges initially

---

## Testing Strategy

### Test Cases

1. **New User, Known Server, Existing Grant Group**
   - User: new-user@inside.com (not in DB)
   - Server: 10.30.0.1 (exists)
   - Expected: User auto-created, grant exists via group policy → connect succeeds

2. **New User, Unknown Server**
   - User: new-user@inside.com
   - Server: 10.30.99.99 (not in DB)
   - Expected: User auto-created, Server auto-created, Grant auto-created → connect succeeds

3. **Known User, Unknown Server, No Auto-Grant**
   - User: existing@inside.com
   - Server: 10.30.99.88
   - Config: auto_grant_enabled = false
   - Expected: Server auto-created, no grant → connection rejected with "Request Access" button

4. **Blocked IP Range**
   - User: new-user@inside.com
   - Server: 8.8.8.8 (external, not whitelisted)
   - Expected: Connection rejected, server not auto-created

5. **Username Collision**
   - User: p.mojski@external.com (SAML)
   - Existing: p.mojski@inside.com (DB)
   - Expected: Create p.mojski@external.com (full email as username)

---

## Rollback Plan

If auto-registration causes issues:

1. **Immediate**: Set feature flags to `false` in config
2. **Clean Up**: Run cleanup script to remove auto-created entities
3. **Analyze**: Review audit logs to find root cause
4. **Fix**: Adjust logic or add more restrictions
5. **Re-enable**: Gradual rollout with tighter controls

---

## Questions for Discussion

1. **Default Grant Expiry**: 8 hours or longer? Renewable?
2. **SSH Login Auto-Detection**: Extract from email (p.mojski@... → p.mojski) or require user to specify?
3. **IP Whitelisting**: Which ranges are safe for auto-server-create?
4. **Admin Notifications**: Email on every auto-creation or daily digest?
5. **Cleanup Policy**: Auto-delete unused auto-created servers after 30 days?
6. **Port Forwarding**: Always disabled for auto-grants or allow for trusted users?
7. **RDP Support**: Auto-create RDP servers or SSH only initially?
8. **User Groups**: Should auto-registered users have limited permissions (e.g., no RDP)?

---

## Alternative: "Request Access" Workflow (No Auto-Grant)

Instead of auto_grant_create, implement fast-track approval:

1. User auto-created from SAML ✅
2. Server auto-created from connection attempt ✅
3. Grant NOT auto-created ❌
4. User sees: "Access denied. Request access to 10.30.0.5?"
5. User clicks → Creates AccessRequest record
6. Admin gets notification → Reviews → Approves in 1 click
7. Grant created → User notified → Can reconnect

**Pros**: More control, approval trail  
**Cons**: Still requires admin action (but faster than full manual flow)

Implement this as Phase 2b (after auto_person + auto_server, before auto_grant).

---

## Recommendation

**Start with**:
- ✅ auto_person_create (safe, just adds user record)
- ✅ auto_server_create (with IP whitelist for internal ranges)
- ⚠️ "Request Access" workflow (manual grant approval)
- ❌ auto_grant_create (too risky initially)

**After 2-4 weeks of monitoring**:
- ✅ Enable auto_grant_create for internal IP ranges only
- ✅ Add expiry/renewal logic
- ✅ Add usage analytics

**Long term**:
- ✅ Full auto for trusted domains/groups
- ✅ External users get manual approval
- ✅ Auto-cleanup of unused resources
