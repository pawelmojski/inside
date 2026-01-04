# Flexible Access Control System V2

**Status**: 🟢 PRODUCTION (Deployed January 4, 2026)

## Overview

New policy-based access control system providing maximum flexibility in permissions management. **Fully integrated** with SSH and RDP proxies.

## Key Features

✅ **Multiple Source IPs per User** - Users can connect from home, office, VPN, etc.
✅ **Server Groups (Tags)** - Organize servers into logical groups
✅ **N:M Relationships** - One server can belong to multiple groups
✅ **Granular Access Control** - Group-level, server-level, or service-level permissions
✅ **Protocol Filtering** - SSH, RDP, or both
✅ **SSH Login Restrictions** - Control which system accounts can be used
✅ **Temporal Access** - Time-limited permissions with TTL
✅ **Transparent Authentication** - SSH agent forwarding + password fallback
✅ **Production Tested** - 13/13 scenarios validated with real user

## Database Schema

### New Tables

1. **user_source_ips** - Multiple IPs per user
   - `id`, `user_id`, `source_ip`, `label`, `is_active`
   - Example: User "john" can have IPs: 192.168.1.100 (Home), 10.0.0.50 (Office)

2. **server_groups** - Logical groups/tags for servers
   - `id`, `name`, `description`
   - Example: "Production DB", "Dev Servers", "Windows Workstations"

3. **server_group_members** - N:M relationship (server ↔ groups)
   - `id`, `server_id`, `group_id`
   - Example: Server "prod-db-01" can be in both "Production DB" and "Critical Infrastructure"

4. **access_policies** - Main access control table
   - `id`, `user_id`, `source_ip_id` (NULL = all user IPs)
   - `scope_type`: 'group', 'server', 'service'
   - `target_group_id`, `target_server_id`
   - `protocol`: NULL (all), 'ssh', 'rdp'
   - `start_time`, `end_time`, `is_active`

5. **policy_ssh_logins** - SSH login restrictions
   - `id`, `policy_id`, `allowed_login`
   - Empty = all logins allowed

## Access Granularity Levels

### 1. Group-Level Access
Grant access to ALL servers in a group.
```bash
grant-policy john group "Production Servers" --duration-hours 8
# John gets SSH+RDP to all servers in group
```

### 2. Server-Level Access
Grant access to specific server, all protocols.
```bash
grant-policy mary server "bastion-host" --duration-hours 24
# Mary gets SSH+RDP to bastion-host only
```

### 3. Service-Level Access
Grant access to specific server + specific protocol.
```bash
grant-policy bob service "app-server-01" --protocol ssh --duration-hours 12
# Bob gets only SSH to app-server-01
```

## SSH Login Restrictions

Control which system accounts can be used:

```bash
# All logins allowed (no restrictions)
grant-policy alice server "web-01" --protocol ssh

# Only specific login
grant-policy bob server "db-01" --protocol ssh --ssh-logins postgres

# Multiple logins
grant-policy charlie server "app-01" --protocol ssh --ssh-logins deploy --ssh-logins monitoring --ssh-logins backup
```

## Technical Implementation Details

### RDP Proxy Integration

**Modified File**: `/opt/jumphost/venv/lib/python3.13/site-packages/pyrdp/core/mitm.py`

**Challenge**: When PyRDP MITM listens on `0.0.0.0`, it needs to determine which backend to route to based on which IP the client connected to (10.0.160.129 for SSH, 10.0.160.130 for RDP).

**Solution**: Extract destination IP from accepted socket in `connectionMade()` callback:

```python
# In buildProtocol(addr):
# 1. Create MITM instance
mitm = RDPMITM(mainlogger, crawlerLogger, self.config)
protocol = mitm.getProtocol()

# 2. Wrap connectionMade() to inject access control
original_connectionMade = protocol.connectionMade

def jumphost_connectionMade():
    # Extract destination IP from socket (AFTER connection established)
    sock = protocol.transport.socket
    dest_ip = sock.getsockname()[0]  # e.g., 10.0.160.130
    
    # Find backend from database
    backend_lookup = access_control.find_backend_by_proxy_ip(db, dest_ip)
    backend_server = backend_lookup['server']  # e.g., 10.30.0.140
    
    # Check access with V2 engine
    result = access_control.check_access_v2(db, source_ip, dest_ip, 'rdp')
    
    if result['has_access']:
        # Update MITM state BEFORE connectToServer() is called
        mitm.state.effectiveTargetHost = backend_server.ip_address
        mitm.state.effectiveTargetPort = 3389
        
        # Continue with original connectionMade (triggers backend connection)
        original_connectionMade()
    else:
        protocol.transport.loseConnection()

protocol.connectionMade = jumphost_connectionMade
```

**Key Points**:
1. `buildProtocol()` is called BEFORE socket is established - can't get dest_ip there
2. `connectionMade()` is called AFTER socket is established - can use `socket.getsockname()[0]`
3. Must set `state.effectiveTargetHost` BEFORE `connectToServer()` executes
4. PyRDP uses `state.effectiveTargetHost` in `connectToServer()` to route to backend

**Testing**: Successfully validated 100.64.0.39 → 10.0.160.130 → 10.30.0.140:3389

### SSH Proxy Integration

**Modified File**: `/opt/jumphost/src/proxy/ssh_proxy.py`

**Key Changes**:
1. **SSH Login Storage**: Store client's SSH login (e.g., "ideo") separately from database username (e.g., "p.mojski")
   ```python
   self.ssh_login = username  # Store in check_auth_password/check_auth_publickey
   ```

2. **Backend Authentication**: Use client's SSH login, not database username
   ```python
   backend_transport.auth_password(server_handler.ssh_login, password)  # NOT user.username
   ```

3. **Agent Forwarding**: Accept pubkey, check for agent, show helpful error if missing
   ```python
   if server_handler.client_key:
       if not server_handler.agent_channel:
           channel.send(b"ERROR: Public key authentication requires agent forwarding.\r\n")
           return
       # Use forwarded agent for backend
   ```

**Backup Created**: `/opt/jumphost/src/proxy/ssh_proxy.py.working_backup_20260104_113741`

## Real-World Example: p.mojski Production Setup

### Scenario
**User**: p.mojski (Paweł Mojski) with 3 devices, different access levels per device.

### User Setup
```bash
# Create user
add-user p.mojski --full-name "Paweł Mojski" --email p.mojski@ideosoftware.com

# Add 3 source IPs (different devices)
add-user-ip p.mojski 100.64.0.20 --label "Tailscale Linux"
add-user-ip p.mojski 10.30.14.3 --label "Biuro Linux"
add-user-ip p.mojski 100.64.0.39 --label "Tailscale Windows"
```

### Access Policies - Device-Specific Restrictions
```bash
# Policy 1: Tailscale Linux → SSH with specific logins
grant-policy p.mojski service Test-SSH-Server \
    --source-ip 100.64.0.20 \
    --protocol ssh \
    --ssh-logins p.mojski \
    --ssh-logins ideo \
    --duration-hours 720

# Policy 2: Biuro Linux → SSH with ALL logins (unrestricted)
grant-policy p.mojski service Test-SSH-Server \
    --source-ip 10.30.14.3 \
    --protocol ssh \
    --duration-hours 720

# Policy 3: Tailscale Windows → RDP only
grant-policy p.mojski service Windows-RDP-Server \
    --source-ip 100.64.0.39 \
    --protocol rdp \
    --duration-hours 720
```

### Results Matrix
| Device | Source IP | Protocol | Login | Target | Result |
|--------|-----------|----------|-------|--------|--------|
| Tailscale Linux | 100.64.0.20 | SSH | p.mojski | Test-SSH-Server | ✅ GRANTED |
| Tailscale Linux | 100.64.0.20 | SSH | ideo | Test-SSH-Server | ✅ GRANTED |
| Tailscale Linux | 100.64.0.20 | SSH | root | Test-SSH-Server | ❌ DENIED |
| Biuro Linux | 10.30.14.3 | SSH | p.mojski | Test-SSH-Server | ✅ GRANTED |
| Biuro Linux | 10.30.14.3 | SSH | root | Test-SSH-Server | ✅ GRANTED |
| Biuro Linux | 10.30.14.3 | SSH | admin | Test-SSH-Server | ✅ GRANTED |
| Tailscale Windows | 100.64.0.39 | RDP | - | Windows-RDP-Server | ✅ GRANTED |
| Tailscale Windows | 100.64.0.39 | SSH | any | Test-SSH-Server | ❌ DENIED |
| Tailscale Linux | 100.64.0.20 | RDP | - | Windows-RDP-Server | ❌ DENIED |

## CLI Commands Reference

### User Source IPs
```bash
# Add source IP
add-user-ip USERNAME SOURCE_IP --label "Description"

# List user IPs
list-user-ips [USERNAME]

# Remove (deactivate) IP
remove-user-ip IP_ID
```

### Server Groups
```bash
# Create group
create-group "Group Name" --description "Description"

# List groups
list-groups

# Show group details
show-group "Group Name"

# Add server to group
add-to-group SERVER_NAME "Group Name"

# Remove from group
remove-from-group SERVER_NAME "Group Name"
```

### Access Policies
```bash
# Grant policy - full syntax
grant-policy USERNAME SCOPE TARGET \
    [--duration-hours HOURS] \
    [--protocol PROTOCOL] \
    [--source-ip SOURCE_IP] \
    [--ssh-logins LOGIN] \
    [--reason "Reason"]

# List policies
list-policies [USERNAME] [--active-only]

# Revoke policy
revoke-policy POLICY_ID
```

### Examples
```bash
# Full group access
grant-policy john group "Production Servers" --duration-hours 8

# Group SSH with specific login
grant-policy mary group "DB Servers" --protocol ssh --ssh-logins postgres --duration-hours 4

# Single server, multiple logins
grant-policy bob server "bastion" --protocol ssh --ssh-logins deploy --ssh-logins ops

# RDP to specific server
grant-policy alice service "win-app-01" --protocol rdp --duration-hours 24

# Restrict to specific source IP
grant-policy charlie server "prod-db" --source-ip 10.0.1.50 --protocol ssh
```

## Integration with Proxies

### SSH Proxy Integration
```python
from src.core.access_control_v2 import AccessControlEngineV2

engine = AccessControlEngineV2()

# Check access during SSH connection
result = engine.check_access_v2(
    db=db,
    source_ip=client_source_ip,
    dest_ip=proxy_destination_ip,    # From socket.getsockname()[0]
    protocol='ssh',
    ssh_login=requested_username
)

if result['has_access']:
    backend_server = result['server']
    # Route to backend_server.ip_address
```

### RDP Proxy Integration
```python
# Check access during RDP connection
result = engine.check_access_v2(
    db=db,
    source_ip=client_source_ip,
    dest_ip=proxy_destination_ip,
    protocol='rdp'
)

if result['has_access']:
    backend_server = result['server']
    # Route to backend_server.ip_address
```

## Migration from Old System

### Legacy Fallback
The old `access_grants` table remains functional. Use `check_access_legacy_fallback()` for backward compatibility.

### Migration Script
```python
from src.core.database import SessionLocal
from src.core.access_control_v2 import AccessControlEngineV2

db = SessionLocal()

# For each old grant:
# 1. Create user_source_ip if not exists
# 2. Create access_policy (scope='service', target_server_id, protocol)
# 3. Migrate SSH restrictions if any
```

## Security Considerations

1. **Source IP Validation**: Always validate source IP before accepting connections
2. **Time-based Access**: Policies automatically expire based on end_time
3. **Audit Logging**: Use `audit_access_attempt()` for all access checks
4. **Least Privilege**: Start with restrictive policies, expand as needed
5. **Regular Review**: Periodically review and revoke unused policies

## Performance Notes

- Indexed fields: `user_id`, `source_ip`, `target_server_id`, `target_group_id`, `is_active`, `start_time`, `end_time`
- Group membership lookup cached at application level (future optimization)
- Typical access check: 2-3 DB queries (user_ip → policies → server_group_members)

## Future Enhancements

- [ ] Policy templates for common access patterns
- [ ] Auto-renewal for permanent access
- [ ] Time-based restrictions (e.g., only business hours)
- [ ] Approval workflow for sensitive servers
- [ ] Policy inheritance (group policies override server policies)
- [ ] Rate limiting per policy
- [ ] Session count limits

## Files

- **Models**: `/opt/jumphost/src/core/database.py`
- **Access Control**: `/opt/jumphost/src/core/access_control_v2.py`
- **CLI**: `/opt/jumphost/src/cli/jumphost_cli_v2.py`
- **Migration**: `/opt/jumphost/alembic/versions/8419b886bc6d_*.py`
- **Tests**: 
  - `/opt/jumphost/test_access_v2.py` (Mariusz/Jasiek test scenario)
  - `/opt/jumphost/test_pmojski_policies.py` (Production p.mojski validation)

## Production Status 🚀

**Deployment Date**: January 4, 2026  
**Status**: 🟢 FULLY OPERATIONAL

### Integration Status

| Component | V2 Integration | Status |
|-----------|---------------|--------|
| SSH Proxy | ✅ AccessControlEngineV2 | 🟢 Production |
| RDP Proxy | ✅ AccessControlEngineV2 | 🟢 Production |
| CLI Tools | ✅ jumphost_cli_v2.py | 🟢 Ready |
| Database | ✅ Migration 8419b886bc6d | 🟢 Applied |
| Audit Logs | ✅ Integrated | 🟢 Active |

### Current Production Configuration

**User**: `p.mojski` (Paweł Mojski, p.mojski@ideosoftware.com)

**Source IPs**:
1. `100.64.0.20` - "Tailscale Linux" (vm-lin1)
2. `10.30.14.3` - "Biuro Linux"
3. `100.64.0.39` - "Tailscale Windows"

**Access Policies**:
| Policy ID | Source IP | Target | Protocol | SSH Logins | Notes |
|-----------|-----------|--------|----------|------------|-------|
| #6 | Tailscale Linux | Test-SSH-Server | SSH | p.mojski, ideo | Restricted logins |
| #7 | Biuro Linux | Test-SSH-Server | SSH | (all) | Office access |
| #8 | Tailscale Windows | Windows-RDP-Server | RDP | N/A | Remote desktop |

**Validated Scenarios** (13/13 ✅):
- ✅ SSH with agent forwarding (no password)
- ✅ SSH with password authentication
- ✅ SSH login validation (p.mojski, ideo allowed from Tailscale Linux)
- ✅ SSH all-logins access (from Biuro Linux)
- ✅ RDP access from Windows Tailscale
- ✅ Access denials for unauthorized combinations
- ✅ Correct backend routing via destination IP
- ✅ Proper SSH login forwarding (not database username)

**Files Modified**:
- `/opt/jumphost/src/proxy/ssh_proxy.py` - SSH proxy with V2
- `/opt/jumphost/src/proxy/ssh_proxy.py.working_backup_20260104_113741` - Backup
- `/opt/jumphost/venv/lib/python3.13/site-packages/pyrdp/core/mitm.py` - PyRDP with V2

### SSH Authentication Flow

**Scenario 1: SSH with Agent Forwarding (-A)**
```bash
ssh -A p.mojski@10.0.160.129
```
1. Client offers SSH key from agent
2. Jumphost accepts key (policy check passes)
3. Jumphost uses forwarded agent for backend auth
4. **Result**: Connected without password! ✅

**Scenario 2: SSH without Agent Forwarding**
```bash
ssh p.mojski@10.0.160.129
```
1. Client offers SSH key from agent
2. Jumphost accepts key (policy check passes)
3. No agent forwarding available
4. Shows helpful error message:
   ```
   ERROR: Public key authentication requires agent forwarding.
   Try: ssh -A p.mojski@10.0.160.129
   Or:  ssh -o PubkeyAuthentication=no p.mojski@10.0.160.129
   ```

**Scenario 3: SSH with Password**
```bash
ssh -o PubkeyAuthentication=no ideo@10.0.160.129
```
1. Client disabled pubkey auth
2. Jumphost prompts for password
3. Uses password for backend authentication
4. **Result**: Connected with password ✅
- ✅ Backend servers: Test-SSH-Server (10.0.160.4), Windows-RDP-Server (10.30.0.140)
- ✅ All tests passing: 13/13
- 🔧 Integration: SSH proxy ready, RDP proxy backend routing in testing
