# Jump Host Project - Roadmap & TODO

## Project Vision

Stworzenie kompletnego SSH/RDP jump hosta z:
- Uwierzytelnianiem przez FreeIPA
- Czasowym przydzielaniem dostępów
- Mapowaniem użytkowników per source IP
- Nagrywaniem sesji
- Dynamicznym zarządzaniem pulą IP (10.0.160.128/25)

## Architecture Goal

```
Client 100.64.0.X
    ↓
    Connect to: 10.0.160.150:22 (SSH) or :3389 (RDP)
    ↓
Jump Host extracts:
    - Source IP: 100.64.0.X (identifies user)
    - Destination IP: 10.0.160.150 (identifies backend server)
    ↓
Access Control:
    - User from source IP has grant to backend?
    - Grant still valid (temporal)?
    ↓
Proxy forwards to backend:
    - SSH: 10.30.0.200:22
    - RDP: 10.30.0.140:3389
    ↓
Session recorded to disk
```

---

## Phase 1: Core Infrastructure ✓ COMPLETE

### Task 1: Environment Setup ✓
- [x] Debian 13 installation
- [x] Python 3.13 + virtualenv
- [x] PostgreSQL setup
- [x] Disk expansion (3GB → 35GB)

### Task 2: Database Schema ✓ + V2 UPGRADE ⭐
- [x] Users table with source_ip (V1)
- [x] Servers table (V1)
- [x] Access grants with temporal fields (V1 - legacy)
- [x] IP allocations table (V1)
- [x] Session recordings table (V1)
- [x] Audit logs table (V1)
- [x] SQLAlchemy ORM models (V1)
- [x] **NEW V2**: user_source_ips (multiple IPs per user)
- [x] **NEW V2**: server_groups (tags/groups)
- [x] **NEW V2**: server_group_members (N:M relationship)
- [x] **NEW V2**: access_policies (flexible granular control)
- [x] **NEW V2**: policy_ssh_logins (SSH login restrictions)
- [x] **NEW V2**: Alembic migration (8419b886bc6d)
- 📄 **Documentation**: `/opt/jumphost/FLEXIBLE_ACCESS_CONTROL_V2.md`

### Task 3: Access Control Engine ✓ + V2 UPGRADE ⭐
- [x] check_access() with source IP + username (V1 - legacy)
- [x] Temporal validation (start_time/end_time) (V1)
- [x] Backend server verification (V1)
- [x] Support for RDP (username=None, source IP only) (V1)
- [x] **NEW V2**: check_access_v2() with policy-based logic
- [x] **NEW V2**: Group-level, server-level, service-level scopes
- [x] **NEW V2**: Protocol filtering (ssh/rdp/all)
- [x] **NEW V2**: SSH login restrictions support
- [x] **NEW V2**: Multiple source IPs per user
- [x] **NEW V2**: Legacy fallback for backward compatibility
- 📂 **File**: `/opt/jumphost/src/core/access_control_v2.py`

### Task 4: IP Pool Manager ✓
- [x] Pool definition: 10.0.160.128/25
- [x] allocate_ip() function
- [x] release_ip() function
- [x] get_pool_status()
- [x] allocate_permanent_ip() for backend servers
- [ ] **TODO**: Integration with V2 policies (auto-allocate on grant)

---

## Phase 2: SSH Proxy ✓ COMPLETE + V2 PRODUCTION

### Status: 🟢 FULLY OPERATIONAL
- ✅ Listening on: `0.0.0.0:22`
- ✅ Access Control: AccessControlEngineV2
- ✅ Authentication: Transparent (agent forwarding + password fallback)
- ✅ Session Recording: `/var/log/jumphost/ssh/`
- ✅ Production Testing: 13/13 scenarios passed

### Key Implementation
**File**: `/opt/jumphost/src/proxy/ssh_proxy.py`

**Critical Fix**: SSH Login Forwarding
- Problem: Backend auth used database username (p.mojski) instead of client's SSH login (ideo)
- Solution: Store `ssh_login` in handler, use for backend authentication
- Code: `backend_transport.auth_password(server_handler.ssh_login, password)`

**Authentication Flow**:
1. Client connects with pubkey → Accept
2. Check for agent forwarding (`agent_channel`)
3. If available → Use forwarded agent for backend auth
4. If not available → Show helpful error message
5. Client can retry with password: `ssh -o PubkeyAuthentication=no user@host`

**Backup**: `/opt/jumphost/src/proxy/ssh_proxy.py.working_backup_20260104_113741`

---

## Phase 3: RDP Proxy ✓ COMPLETE + V2 PRODUCTION

### Status: 🟢 FULLY OPERATIONAL
- ✅ Listening on: `0.0.0.0:3389`
- ✅ Access Control: AccessControlEngineV2
- ✅ Session Recording: `/var/log/jumphost/rdp_recordings/`
- ✅ Production Testing: Validated 100.64.0.39 → 10.0.160.130 → 10.30.0.140

### Key Implementation
**File**: `/opt/jumphost/venv/lib/python3.13/site-packages/pyrdp/core/mitm.py`

**Critical Fix**: Destination IP Extraction
- Problem: When listening on `0.0.0.0`, cannot determine which backend to route to in `buildProtocol()`
- Root Cause: `buildProtocol()` called before socket established, only has source IP/port
- Solution: Wrap `connectionMade()` to extract dest_ip from socket after connection:
  ```python
  sock = protocol.transport.socket
  dest_ip = sock.getsockname()[0]  # e.g., 10.0.160.130
  ```
- Then find backend: `find_backend_by_proxy_ip(db, dest_ip)` → `10.30.0.140`
- Update state: `mitm.state.effectiveTargetHost = backend_server.ip_address`
- PyRDP's `connectToServer()` uses `state.effectiveTargetHost` to connect to backend

**Why This Works**:
1. Client connects to 10.0.160.130:3389
2. `buildProtocol()` creates MITM, wraps `connectionMade()`
3. `connectionMade()` extracts 10.0.160.130 from socket
4. Looks up backend: 10.0.160.130 → 10.30.0.140 (from ip_allocations table)
5. Checks access: 100.64.0.39 + 10.0.160.130 + rdp → Policy #8
6. Sets `state.effectiveTargetHost = "10.30.0.140"`
7. Original `connectionMade()` triggers `connectToServer()` which connects to 10.30.0.140:3389

**Integration Points**:
- Import: `from core.access_control_v2 import AccessControlEngineV2`
- Database: `from core.database import SessionLocal, IPAllocation, AuditLog`
- Access Check: `check_access_v2(db, source_ip, dest_ip, 'rdp')`
- Backend Lookup: `find_backend_by_proxy_ip(db, dest_ip)`

### Task 5: CLI Management Tool ✓ + V2 CLI ⭐
- [x] Typer + Rich tables (V1)
- [x] add-user command (V1)
- [x] add-server command (V1)
- [x] grant-access command with --duration (V1 - legacy)
- [x] list-users, list-servers, list-grants (V1)
- [x] **NEW V2 CLI**: jumphost_cli_v2.py (11 commands)
  - add-user-ip, list-user-ips, remove-user-ip
  - create-group, list-groups, show-group
  - add-to-group, remove-from-group
  - grant-policy (with full flexibility)
  - list-policies, revoke-policy
- 📂 **File**: `/opt/jumphost/src/cli/jumphost_cli_v2.py`
- 🧪 **Test**: `/opt/jumphost/test_access_v2.py` (Mariusz/Jasiek scenario)

---

## Phase 2: SSH Proxy ✓ COMPLETE

### Task 6: SSH Proxy Implementation ✓
- [x] Paramiko SSH server
- [x] Password authentication
- [x] Public key authentication
- [x] SSH agent forwarding (AgentServerProxy)
- [x] PTY forwarding with term/dimensions
- [x] Exec support (SCP)
- [x] Subsystem support (SFTP)
- [x] Session recording (JSON format)
- [x] Access control integration
- [x] Audit logging

**Status**: 100% WORKING - Production ready!

**Current Config**:
- Listen: 10.0.160.129:22
- Backend: 10.0.160.4:22 (hardcoded)

---

## Phase 3: RDP Proxy ✓ COMPLETE

### Task 7: PyRDP MITM Setup ✓
- [x] Install pyrdp-mitm
- [x] Fix Python 3.13 compatibility (typing.BinaryIO)
- [x] Apply RDP version patch (RDPVersion._missing_)
- [x] Test with Windows RDP client
- [x] Session recording to .pyrdp files

### Task 8: RDP Guard Proxy ✓
- [x] Async TCP proxy (Python asyncio)
- [x] Source IP-based access control
- [x] Backend server verification
- [x] Audit logging (access granted/denied)
- [x] Access denial with message
- [x] Forward to PyRDP MITM on localhost:13389

**Status**: 100% WORKING - Production ready!

**Current Config**:
- Guard: 10.0.160.129:3389 → PyRDP: localhost:13389 → Backend: 10.30.0.140:3389

---

## Phase 4: Architecture Refactor ✓ COMPLETE

### Task 9: Dynamic IP Pool-Based Routing ✓ COMPLETE
**Priority**: CRITICAL

**Goal**: Każdy backend dostaje swój dedykowany IP z puli, proxy nasłuchuje na 0.0.0.0 i routuje na podstawie destination IP

**Completed Changes**:

#### A. SSH Proxy Changes ✓
1. **✓ Moved management SSH to port 2222**
   ```bash
   # /etc/ssh/sshd_config
   Port 2222
   ListenAddress 10.0.160.5
   # Restarted: systemctl restart sshd
   ```

2. **✓ SSH Proxy listens on 0.0.0.0:22**
   ```python
   # src/proxy/ssh_proxy.py - już było poprawnie zaimplementowane
   server = paramiko.Transport(('0.0.0.0', 22))
   ```

3. **✓ Destination IP extraction in SSH handler**
   ```python
   def check_auth_password(self, username, password):
       source_ip = self.transport.getpeername()[0]
       # Extract destination IP
       dest_ip = self.transport.getsockname()[0]
       
       # Lookup backend by dest_ip from ip_allocations table
       backend_lookup = self.access_control.find_backend_by_proxy_ip(db, dest_ip)
       backend_server = b ✓
1. **✓ Listens on 0.0.0.0:3389**
   ```python
   # src/proxy/rdp_guard.py - już było poprawnie zaimplementowane
   guard = RDPGuardProxy(
       listen_host='0.0.0.0',
       listen_port=3389,
       pyrdp_host='127.0.0.1',
       pyrdp_port=13389
   )
   ```

2. **✓ Destination IP extraction from socket**
   ```python
   async def handle_client(self, reader, writer):
       source_ip = writer.get_extra_info('peername')[0]
       # Extract destination IP
       sock = writer.get_extra_info('socket')
       dest_ip = sock.getsockname()[0]
       
       # Lookup backend by dest_ip from ip_allocations table
       backend_lookup = self.access_control.find_backend_by_proxy_ip(db, dest_ip)
       backend_server = backend_lookup['server']
       
       # Lookup backend by dest_ip
       backend_server = find_backend_by_proxy_ip(db, dest_ip)
   ```Schema Changes ✓
**✓ Zmieniono strategię**: Zamiast kolumny `proxy_ip` w `servers`, użyto istniejącej tabeli `ip_allocations` z:
- `server_id` - link do serwera
- `allocated_ip` - IP z puli przydzielony do serwera (UNIQUE)
- `user_id` - NULL dla permanent server allocations
- `source_ip` - NULL dla permanent server allocations  
- `expires_at` - NULL dla permanent allocations (nigdy nie wygasa)

**✓ Schema fixes**:
```sql
-- Usunięto NOT NULL constraints żeby umożliwić permanent allocations
ALTER TABLE ip_allocations ALTER COLUMN user_id DROP NOT NULL;
ALTER TABLE ip_allocations ALTER COLUMN source_ip DROP NOT NULL;
ALTER TABLE ip_allocations ALTER COLUMN expires_at DROP NOT NULL;
```

**✓ Workflow Implementation**:
1. **✓** Admin dodaje server: `add-server Test-SSH-Server 10.0.160.4 linux`
2. **✓** Admin przydziela IP z puli: `assign-proxy-ip 1 10.0.160.129`
3. **✓** System zapisujmplementation ✓
**✓ Implemented Functions**:
```python
# src/core/ip_pool.py
def allocate_permanent_ip(db, server_id, specific_ip=None):
    """Allocate permanent IP from pool for server (never expires)"""
    # Creates IPAllocation with user_id=NULL, expires_at=NULL
    # Allocates specific IP or next available from pool
    
def release_ip(db, allocated_ip):
    """Release IP back to pool and remove from interface"""
    # Marks as released_at=now
    # Removes IP from network interface
```

**✓ CLI Commands Implemented**:
```bash
# Assign IP from pool to server
jumphost_cli.py assign-proxy-ip <server_id> [specific_ip]

# Remove IP allocation from server
jumphost_cli.py remove-proxy-ip <server_id>

# List all allocations (permanent and temporary)
jumphost_cli.py list-allocations
```

**✓ Testing Completed**:
1. **✓** Added 2 servers: Test-SSH-Server (ID:1), Windows-RDP-Server (ID:2)
2. **✓** Assigned IPs: 10.0.160.129→Server 1, 10.0.160.130→Server 2  
3. **✓** IPs configured on interface ens18
4. **✓** Created users: p.mojski, p.mojski.win
5. **✓** Created grants: p.mojski→SSH Server, p.mojski.win→RDP Server (480 min)
6. **✓** SSH Proxy running on 0.0.0.0:22, routing works
7. **✓** Verified session recording and audit logging
8. **⏳** RDP Guard needs to be started with PyRDP MITM backend
```

**Testing Plan**:
1. Add server, verify IP allocated and configured
2. Grant access to user
3. Connect from client to proxy_ip
4. Verify correct backend routing
5. Check session recording
6. Remove grant, verify IP still assigned
7. Remove server, verify IP released and removed from interface

---

## Phase 5: FreeIPA Integration ⏸️ NOT STARTED

### Task 10: FreeIPA Client Setup
- [ ] Install freeipa-client
- [ ] Join to FreeIPA domain
- [ ] Configure SSSD

### Task 11: FreeIPA User Sync
- [ ] Sync users from FreeIPA to local DB
- [ ] Map FreeIPA attributes to user table
- [ ] Periodic sync job (cron)

### Task 12: FreeIPA Authentication
- [ ] Replace password check with FreeIPA bind
- [ ] SSH key verification from FreeIPA
- [ ] Group-based access control

---

## Phase 6: Web Interface ⏸️ NOT STARTED

### Task 13: FastAPI Backend
- [ ] REST API endpoints
  - [ ] GET /users
  - [ ] POST /users
  - [ ] GET /servers
  - [ ] POST /servers
  - [ ] POST /grants
  - [ ] GET /grants
  - [ ] GET /audit-logs
  - [ ] GET /session-recordings

### Task 14: Web GUI
- [ ] Technology: React / Vue.js?
- [ ] User management page
- [ ] Server management page
- [ ] Grant management page (with temporal picker)
- [ ] Audit logs viewer
- [ ] Session recordings browser
- [ ] Real-time connection status

---

## Phase 7: Automation & Monitoring ⏸️ NOT STARTED

### Task 15: Grant Expiration Daemon
- [ ] Background service checking expired grants
- [ ] Auto-revoke access on expiration
- [ ] Notification to user before expiration
- [ ] Release unused proxy IPs

### Task 16: Systemd Services
- [ ] ssh_proxy.service
- [ ] rdp_guard.service
- [ ] rdp_wrapper.service
- [ ] grant_expiration.service

### Task 17: Monitoring & Alerting
- [ ] Prometheus metrics exporter
- [ ] Grafana dashboards
- [ ] Alert on access denials
- [ ] Alert on proxy failures
- [ ] Connection count metrics

### Task 18: Log Management
- [ ] Log rotation configuration
- [ ] Centralized logging (syslog/ELK?)
- [ ] Session recording cleanup policy

---

## Phase 8: Security Hardening ⏸️ NOT STARTED

### Task 19: Network Security
- [ ] Rate limiting (connection attempts per IP)
- [ ] DDoS protection
- [ ] Firewall rules (only allow from known networks)

### Task 20: Encryption
- [ ] TLS for RDP connections
- [ ] Encrypted session recordings
- [ ] Secure key storage

### Task 21: Audit & Compliance with dynamic routing
   - Agent forwarding ✓
   - Session recording ✓
   - Access control ✓
   - SCP/SFTP ✓
   - Listens on 0.0.0.0:22 ✓
   - Destination IP extraction ✓
   - Dynamic backend lookup via ip_allocations ✓
   - **Status**: Running in production

2. **RDP Proxy** - 100% functional in production (native PyRDP MITM modified)
   - **Modified PyRDP core**: /opt/jumphost/venv/lib/python3.13/site-packages/pyrdp/core/mitm.py
   - **Backup**: /opt/jumphost/venv/lib/python3.13/site-packages/pyrdp/core/mitm.py.backup
   - Access control based on source_ip only (simplified routing)
   - Uses deepcopy(config) for per-connection config isolation
   - Backend determined from user's grant in buildProtocol()
   - Session recording ✓
   - Listens on 0.0.0.0:3389 ✓
   - **Status**: Running in production (PID tracked in logs)
   - **Limitation**: If user has multiple grants, routes to first grant's server
   - **Future**: Add dest_ip verification by wrapping connectionMade() with state.effectiveTargetHost update

3. **Core Infrastructure**
   - Database schema ✓ (with permanent IP allocations)
   - Access control engine ✓ (with find_backend_by_proxy_ip)
   - IP pool manager ✓ (with allocate_permanent_ip)
   - CLI tool ✓ (assign-proxy-ip, remove-proxy-ip commands)

4. **Dynamic IP Pool System** ✓ COMPLETE
   - IP allocations table supports permanent server assignments ✓
   - allocate_permanent_ip() for server IPs ✓
   - CLI commands for IP management ✓
   - Network interface auto-configuration ✓
   - Backend lookup by destination IP ✓

### 🔄 In Progress
- None - all core systems operational!
   - Session recording ✓
   - Backend verification ✓

3. **Core Infrastructure**
   - Database schema ✓
   - Access control engine ✓
   - IP pool manag✓ DONE - Architecture refactor complete
   - ✓ Moved management SSH to port 2222
   - ✓ SSH proxy on 0.0.0.0:22 (already was)
   - ✓ RDP guard on 0.0.0.0:3389 (already was)
   - ✓ IP allocations via ip_allocations table (not proxy_ip column)
   - ✓ Destination IP lookup logic implemented (find_backend_by_proxy_ip)
   - ✓ SSH workflow tested end-to-end

2. **[HIGH]** ✓ DONE - RDP services started
   - ✓ Started rdp_guard.py on 0.0.0.0:3389
   - ✓ Started pyrdp-mitm on localhost:13389 → 10.30.0.140
   - TODO: Test RDP connection end-to-end
   - TODO: Configure PyRDP for Linux backend (10.0.160.4) if SSH proxy IP also needs RDP

3. **[MEDIUM]** Systemd service files for auto-start
   - jumphost-ssh.service
   - jumphost-rdp-guard.service  
   - jumphost-pyrdp-mitm.service
## Immediate Next Steps (Priority Order)

1. **[CRITICAL]** Refactor to 0.0.0.0 listening with destination IP extraction
   - Move management SSH to port 2222
   - Change SSH proxy to 0.0.0.0:22
   - Change RDP guard to 0.0.0.0:3389
   - ✓ SSH Proxy**: ~~Currently hardcodes backend to 10.0.160.4~~
   - ✓ FIXED: Uses destination IP via find_backend_by_proxy_ip()

2. **✓ RDP Guard**: ~~Currently hardcodes target_server to 10.30.0.140~~
   - ✓ FIXED: Uses destination IP via find_backend_by_proxy_ip()

3. **CLI**: No --source-ip option in add-user
   - TODO: Add optional --source-ip parameter

4. **✓ IP Pool**: ~~Not automatically used~~
   - ✓ FIXED: Manual assignment via assign-proxy-ip command
   - TODO: Consider auto-assignment on server creation

5. **Audit Logs**: user_id is nullable but should be set when known
   - TODO: Update audit logging to include user_id

6. **RDP Multi-Backend**: Simplified routing based on source_ip grant
   - ✓ Single PyRDP MITM instance handles all backends
   - ✓ No rdp_guard intermediate layer needed
   - ✓ Access control integrated directly in PyRDP factory
   - ⚠️ Limitation: Routes to first granted server if user has multiple grants
   - TODO: Implement full dest_ip verification in connectionMade() wrapper
   - TODO: Update state.effectiveTargetHost before server connection initiated stable)

---

## Technical Debt

1. **SSH Proxy**: Currently hardcodes backend to 10.0.160.4
   - Fix: Use destination IP to determine backend

2. **RDP Guard**: Currently hardcodes target_server to 10.30.0.140
   - Fix: Use destination IP to determine backend
 (Session 1 - Morning)
- ✅ SSH Proxy fully working with agent forwarding
- ✅ RDP Proxy fully working with PyRDP MITM
- ✅ RDP Guard proxy with access control
- ✅ Backend server verification in access control
- ✅ Audit logging for access granted/denied
- ⚠️ Identified architecture issue: shared IP for SSH/RDP
- 📝 Created documentation and roadmap

### 2026-01-02 (Session 2 - Afternoon) **MAJOR REFACTOR**
- ✅ Fixed database schema: user_id, source_ip, expires_at now nullable for permanent allocations
- ✅ Implemented allocate_permanent_ip() function for server IP assignments
- ✅ Fixed CLI assign-proxy-ip command (removed duplicate, uses allocate_permanent_ip)
- ✅ Fixed get_available_ips() to properly exclude permanent allocations
- ✅ Verified SSH proxy listens on 0.0.0.0:22 with destination IP extraction
- ✅ Verified RDP guard listens on 0.0.0.0:3389 with destination IP extraction
- ✅ Assigned proxy IPs: 10.0.160.129→Test-SSH-Server, 10.0.160.130→Windows-RDP-Server
- ✅ Configured IPs on network interface (ip addr add)
- ✅ Created users: p.mojski (Paweł Mojski), p.mojski.win (Paweł Mojski Windows)
- ✅ Created access grants: p.mojski→SSH (480 min), p.mojski.win→RDP (480 min)
- ✅ SSH proxy tested and working in production
- ✅ Started RDP Guard on 0.0.0.0:3389
- ✅ Started PyRDP MITM on localhost:13389 → Windows backend
- 🎯 **ARCHITECTURE REFACTOR COMPLETE** - Dynamic IP pool-based routing now operational
- 🚀 **SYSTEM FULLY OPERATIONAL** - Both SSH and RDP proxies running in production

**Current Production Status**:
- SSH Proxy: 0.0.0.0:22 (PID: 29078) → backends via IP pool routing (destination IP extraction) ✓
- RDP Proxy: 0.0.0.0:3389 (PID: ~34713) → backend via source_ip grant lookup (simplified) ✓
- Management SSH: 10.0.160.5:2222 ✓
- IP Allocations: 10.0.160.129→SSH Server, 10.0.160.130→RDP Server ✓
- **Active User**: p.mojski (Paweł Mojski) with 3 devices
  - Tailscale Linux (100.64.0.20): SSH as p.mojski/ideo
  - Biuro Linux (10.30.14.3): SSH as anyone
  - Tailscale Windows (100.64.0.39): RDP only
- **Access Control V2**: 3 active policies, all tests passing (13/13) ✓
- **Architecture**: Native PyRDP modification (no wrappers) for maximum performance

**Known Limitations**:
- RDP: Currently routes based on source_ip grant only (dest_ip not used)
- RDP: Multi-server grants per user will route to first granted server
- Solution attempted: dest_ip extraction in connectionMade() with state.effectiveTargetHost
- Issue: deepcopy(config) needed, state update timing critical
- **Next**: Integrate AccessControlEngineV2 with SSH/RDP proxies
- 🎯 **ARCHITECTURE REFACTOR COMPLETE** - Dynamic IP pool-based routing now operational but should be set when known
   - Fix: Update audit logging to include user_id

---

## Questions for User

1. **IP Allocation**: Automatycznie przy dodaniu serwera czy na żądanie?
2. **FreeIPA**: Jaki jest hostname/domain FreeIPA?
3. **Web GUI**: Jakieś preferencje co do technologii (React/Vue/plain JS)?
4. **Monitoring**: Prometheus + Grafana OK?
5. **Session Recordings**: Jak długo trzymać? Auto-delete po X dniach?

---

## Changelog

### 2026-01-04 🎉 V2 PRODUCTION DEPLOYMENT
- ✅ **AccessControlEngineV2** fully deployed to production
- ✅ **Database migration** (8419b886bc6d) applied - 5 new V2 tables
- ✅ **SSH Proxy** integrated with V2 (check_access_v2 with protocol='ssh')
- ✅ **RDP Proxy** (PyRDP MITM) integrated with V2 (check_access_v2 with protocol='rdp')
- ✅ **CLI V2** implemented - 11 new management commands
- ✅ **Production user** p.mojski configured with 3 source IPs and 3 policies
- ✅ **Transparent auth** working: SSH agent forwarding + password fallback
- ✅ **All tests passed**: 13/13 production scenarios validated
- ✅ **Documentation**: FLEXIBLE_ACCESS_CONTROL_V2.md created
- 📦 **Backup**: ssh_proxy.py.working_backup_20260104_113741

### 2026-01-02
- ✅ SSH Proxy fully working with agent forwarding
- ✅ RDP Proxy fully working with PyRDP MITM
- ✅ RDP Guard proxy with access control
- ✅ Backend server verification in access control
- ✅ Audit logging for access granted/denied
- ⚠️ Identified architecture issue: shared IP for SSH/RDP
- 📝 Created documentation and roadmap

---

## Notes

### PyRDP Patch Location
- File: `/opt/jumphost/venv/lib/python3.13/site-packages/pyrdp/enum/rdp.py`
- Backup: `/opt/jumphost/venv/lib/python3.13/site-packages/pyrdp/enum/rdp.py.backup`
- Changes: Added `_missing_()` classmethod and `RDP10_12 = 0x80011`

### PyRDP MITM Modification
- File: `/opt/jumphost/venv/lib/python3.13/site-packages/pyrdp/core/mitm.py`
- Backup: `/opt/jumphost/venv/lib/python3.13/site-packages/pyrdp/core/mitm.py.backup`
- Changes: 
  - Added jumphost module imports (database, access_control)
  - Modified `MITMServerFactory.buildProtocol()` to check source_ip access
  - Uses `deepcopy(config)` for per-connection backend configuration
  - Sets `config.targetHost` from grant before creating RDPMITM
  - Integrated audit logging for RDP connections

### Database Manual Operations
```python
# Add user with source_ip
from src.core.database import SessionLocal, User
db = SessionLocal()
user = User(username='name', email='email@example.com', 
            full_name='Full Name', source_ip='100.64.0.X', is_active=True)
db.add(user)
db.commit()
db.close()
```

### Useful Commands
```bash
# Check active connections
ss -tnp | grep -E ':(22|3389)'

# View audit logs
psql -U jumphost -d jumphost -c "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 10;"

# Check allocated IPs
psql -U jumphost -d jumphost -c "SELECT * FROM ip_allocations WHERE released_at IS NULL;"
```
