# Jump Host - SSH/RDP Proxy with Access Control

## Project Overview

Self-made SSH/RDP jump host with temporal access control, source IP mapping, session recording, and IP pool management.

## Architecture (Current State)

```
┌─────────────────────────────────────────────────────────────────┐
│                         JUMP HOST                                │
│                      (10.0.160.5)                                │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  SSH Access (10.0.160.129:22)                            │   │
│  │                                                            │   │
│  │  SSH Proxy (Paramiko)                                     │   │
│  │  - Source IP: 100.64.0.20 → User: p.mojski               │   │
│  │  - Agent forwarding support (-A flag)                     │   │
│  │  - Session recording (JSON)                               │   │
│  │  - Backend: 10.0.160.4 (Linux SSH)                        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  RDP Access (10.0.160.129:3389)                           │   │
│  │                                                            │   │
│  │  RDP Guard Proxy (Python asyncio)                         │   │
│  │  - Source IP: 100.64.0.39 → User: p.mojski.win           │   │
│  │  - Access control + audit logging                         │   │
│  │  - Forwards to: PyRDP MITM (localhost:13389)             │   │
│  │                                                            │   │
│  │  PyRDP MITM (localhost:13389)                             │   │
│  │  - Full session recording (.pyrdp files)                  │   │
│  │  - Backend: 10.30.0.140 (Windows RDP)                     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Core Components                                          │   │
│  │                                                            │   │
│  │  • PostgreSQL Database                                    │   │
│  │    - users (username, source_ip, is_active)              │   │
│  │    - servers (name, ip_address, os_type)                 │   │
│  │    - access_grants (user_id, server_id, start/end time)  │   │
│  │    - ip_allocations (ip, server_id, allocated_at)        │   │
│  │    - session_recordings (user_id, server_id, file_path)  │   │
│  │    - audit_logs (action, source_ip, success, details)    │   │
│  │                                                            │   │
│  │  • Access Control Engine                                  │   │
│  │    - Source IP + temporal validation                      │   │
│  │    - Backend server verification                          │   │
│  │    - For SSH: checks username + source_ip                │   │
│  │    - For RDP: checks source_ip only (RDP auth later)     │   │
│  │                                                            │   │
│  │  • IP Pool Manager                                        │   │
│  │    - Pool: 10.0.160.128/25 (126 usable IPs)             │   │
│  │    - Dynamic allocation for backend servers               │   │
│  │    - Release on grant expiration                          │   │
│  │                                                            │   │
│  │  • CLI Management Tool (Typer + Rich)                    │   │
│  │    - add-user, add-server, grant-access                  │   │
│  │    - list-users, list-servers, list-grants               │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐      ┌──────────────┐     ┌──────────────┐
│   Client 1   │      │   Client 2   │     │   Client 3   │
│ 100.64.0.20  │      │ 100.64.0.39  │     │ 100.64.0.88  │
│              │      │              │     │              │
│ p.mojski     │      │p.mojski.win  │     │ (no grant)   │
│ SSH access   │      │ RDP access   │     │ DENIED       │
└──────────────┘      └──────────────┘     └──────────────┘
```

## Technology Stack

### System
- **OS**: Debian 13 (35GB disk, expanded from 3GB)
- **Python**: 3.13 with virtualenv at `/opt/jumphost/venv`
- **Database**: PostgreSQL with SQLAlchemy ORM

### SSH Proxy
- **Paramiko 4.0.0**: SSH server/client implementation
- **Features**:
  - SSH agent forwarding (AgentServerProxy)
  - PTY forwarding with term type/dimensions
  - Exec/subsystem support (SCP, SFTP)
  - Password + public key authentication
  - Session recording (JSON format)

### RDP Proxy
- **PyRDP MITM 2.1.0**: RDP man-in-the-middle with session recording
- **Twisted 25.5.0**: Async networking framework
- **Custom Guard Proxy**: Python asyncio TCP proxy with access control
- **Patch Applied**: RDPVersion._missing_() for new Windows RDP clients
  - File: `/opt/jumphost/venv/lib/python3.13/site-packages/pyrdp/enum/rdp.py`
  - Handles unknown RDP version numbers
  - Added RDP10_12 = 0x80011

## Access Control Logic

### SSH Access Control
1. Client connects with username + source IP
2. `AccessControlEngine.check_access(db, source_ip, username)`
3. Validates:
   - User exists and is active
   - Source IP matches user's registered source_ip
   - Active grant exists (start_time <= now <= end_time)
   - Target server is active
4. If OK: Connect to backend with agent forwarding
5. If DENIED: Close connection, log to audit_logs

### RDP Access Control (Two-Stage)
1. **Stage 1 - Guard Proxy** (`rdp_guard.py`):
   - Client connects from source IP
   - `AccessControlEngine.check_access(db, source_ip, username=None)`
   - Validates:
     - User found by source_ip
     - Active grant exists
     - Grant's server matches THIS proxy's target_server
   - If OK: Forward to PyRDP MITM on localhost:13389
   - If DENIED: Send "ACCESS DENIED" message, close, log to audit_logs

2. **Stage 2 - PyRDP MITM**:
   - Receives connection from guard proxy
   - Performs full RDP MITM
   - Records session to `.pyrdp` files
   - Connects to backend Windows server

## File Structure

```
/opt/jumphost/
├── venv/                           # Python virtual environment
├── src/
│   ├── core/
│   │   ├── database.py            # SQLAlchemy models
│   │   ├── access_control.py      # Access control engine
│   │   └── ip_pool.py             # IP pool manager
│   ├── proxy/
│   │   ├── ssh_proxy.py           # SSH proxy server (WORKING ✓)
│   │   ├── rdp_guard.py           # RDP guard proxy (WORKING ✓)
│   │   ├── rdp_wrapper.sh         # PyRDP MITM wrapper
│   │   └── rdp_proxy.py           # Old Python wrapper (deprecated)
│   └── cli/
│       └── jumphost_cli.py        # CLI management tool
├── certs/                         # SSL certificates for RDP
└── logs/

/var/log/jumphost/
├── ssh_proxy.log                  # SSH proxy logs
├── rdp_guard.log                  # RDP guard proxy logs
├── rdp_wrapper.log                # PyRDP backend logs
├── ssh_recordings/                # SSH session recordings (JSON)
│   └── ssh_session_*.json
└── rdp_recordings/                # RDP session recordings
    ├── replays/                   # .pyrdp replay files
    ├── files/                     # Transferred files
    └── certs/                     # Auto-generated certificates
```

## Database Schema

### users
- `id` (PK), `username`, `email`, `full_name`
- `source_ip` (VARCHAR 45) - Client source IP address
- `is_active`, `created_at`, `updated_at`

### servers
- `id` (PK), `name`, `ip_address`, `os_type`
- `description`, `is_active`, `created_at`, `updated_at`

### access_grants
- `id` (PK), `user_id` (FK), `server_id` (FK)
- `protocol` ('ssh' or 'rdp')
- `start_time`, `end_time` - Temporal access window
- `is_active`, `created_at`

### ip_allocations
- `id` (PK), `ip_address`, `server_id` (FK)
- `allocated_at`, `released_at`

### session_recordings
- `id` (PK), `user_id` (FK), `server_id` (FK)
- `protocol`, `file_path`, `duration`, `started_at`, `ended_at`

### audit_logs
- `id` (PK), `user_id` (FK nullable)
- `action` (e.g., 'ssh_access_granted', 'rdp_access_denied')
- `resource_type`, `resource_id`, `source_ip`
- `success` (Boolean), `details` (TEXT), `timestamp`

## Current Network Configuration

### Management
- Management SSH: `10.0.160.5:22` (OpenSSH sshd)

### Proxy Endpoints (Current - Same IP!)
- SSH Proxy: `10.0.160.129:22` → Backend: `10.0.160.4:22`
- RDP Guard: `10.0.160.129:3389` → PyRDP → Backend: `10.30.0.140:3389`
- PyRDP Backend: `localhost:13389` (internal)

### Backend Servers
- Linux SSH: `10.0.160.4:22`
- Windows RDP: `10.30.0.140:3389`

### Clients
- `100.64.0.20` - p.mojski (Linux, SSH grant to 10.0.160.4)
- `100.64.0.39` - p.mojski.win (Windows, RDP grant to 10.30.0.140)

### IP Pool (Not Yet Used)
- Range: `10.0.160.128/25` (10.0.160.129 - 10.0.160.254)
- Total: 126 usable IPs
- Reserved: 10.0.160.129 (currently used for both SSH and RDP - ISSUE!)

## CLI Usage Examples

```bash
# Add user with source IP
/opt/jumphost/venv/bin/python src/cli/jumphost_cli.py add-user p.mojski

# Add servers
/opt/jumphost/venv/bin/python src/cli/jumphost_cli.py add-server linux-ssh 10.0.160.4 linux
/opt/jumphost/venv/bin/python src/cli/jumphost_cli.py add-server win-rdp 10.30.0.140 windows

# Grant access for 2 hours
/opt/jumphost/venv/bin/python src/cli/jumphost_cli.py grant-access p.mojski 10.0.160.4 --duration 120

# List grants
/opt/jumphost/venv/bin/python src/cli/jumphost_cli.py list-grants
```

## Session Recording

### SSH Sessions
- Format: JSON with timestamp and I/O events
- Location: `/var/log/jumphost/ssh_recordings/ssh_session_*.json`
- Content: PTY input/output, commands, timing

### RDP Sessions
- Format: PyRDP replay files (.pyrdp)
- Location: `/var/log/jumphost/rdp_recordings/replays/`
- Playback: `pyrdp-player replay_file.pyrdp`
- Features: Full video replay, file transfers, clipboard

## Tested & Working Features

### SSH Proxy ✓
- [x] Password authentication
- [x] Public key authentication
- [x] SSH agent forwarding (-A flag)
- [x] PTY forwarding (term type, dimensions)
- [x] Shell sessions
- [x] Exec requests (SCP)
- [x] Subsystem requests (SFTP)
- [x] Session recording (JSON)
- [x] Source IP-based access control
- [x] Temporal access validation

### RDP Proxy ✓
- [x] PyRDP MITM with session recording
- [x] Guard proxy with access control
- [x] Source IP-based access control
- [x] Backend server verification
- [x] Audit logging (access granted/denied)
- [x] Session recording (.pyrdp files)
- [x] RDP version compatibility patch (RDP10_12)
- [x] Access denial with message

## Known Issues & Limitations

### Architecture Issues
1. **CRITICAL**: SSH and RDP share same IP (10.0.160.129)
   - Clients can't determine which backend by destination IP
   - Breaks IP pool allocation logic
   - **Solution**: Move to 0.0.0.0 listen, extract destination IP

2. **IP Pool Not Used**: Dynamic allocation not yet implemented
   - Currently manual IP assignment
   - Need automated allocation on grant creation
   - Need automatic cleanup on grant expiration

3. **No FreeIPA Integration**: Using local database for users
   - Planned: Sync users from FreeIPA
   - Planned: FreeIPA authentication backend

### Minor Issues
1. Source IP must be manually set in database (CLI doesn't support it)
2. No web GUI for management
3. No monitoring/alerting
4. No systemd service files
5. SSH proxy runs on port 22, conflicts with management SSH

## Performance & Scaling

### Current Limits
- SSH: Paramiko handles ~100 concurrent connections
- RDP: PyRDP MITM tested with ~20 concurrent sessions
- Database: PostgreSQL, no tuning yet

### Future Optimizations
- Connection pooling for database
- Separate SSH proxy instances per backend
- Load balancing for multiple jump hosts

## Security Considerations

### Current
- Source IP validation
- Temporal access control (start/end time)
- Session recording for audit
- Backend server verification

### Missing (TODO)
- TLS for RDP connections
- SSH host key verification
- Rate limiting / DDoS protection
- Security hardening (SELinux, AppArmor)
- Log rotation
- Encrypted session recordings

## Maintenance

### Start Services
```bash
# SSH Proxy
cd /opt/jumphost && sudo /opt/jumphost/venv/bin/python src/proxy/ssh_proxy.py &

# RDP Backend (PyRDP MITM)
sudo /opt/jumphost/src/proxy/rdp_wrapper.sh &

# RDP Guard (Access Control)
cd /opt/jumphost && sudo /opt/jumphost/venv/bin/python src/proxy/rdp_guard.py &
```

### Stop Services
```bash
sudo pkill -f ssh_proxy
sudo pkill -f rdp_wrapper
sudo pkill -f rdp_guard
```

### View Logs
```bash
tail -f /var/log/jumphost/ssh_proxy.log
tail -f /var/log/jumphost/rdp_guard.log
tail -f /var/log/jumphost/rdp_wrapper.log
```

### Check Audit Logs
```bash
cd /opt/jumphost && /opt/jumphost/venv/bin/python -c "
from src.core.database import SessionLocal, AuditLog
db = SessionLocal()
logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(10).all()
for log in logs:
    print(f'{log.timestamp} - {log.action} - {log.source_ip} - {log.success} - {log.details}')
db.close()
"
```

## Testing Checklist

### SSH Proxy Tests
- [x] Connect with password
- [x] Connect with SSH key
- [x] Connect with agent forwarding (`ssh -A`)
- [x] Copy files with SCP
- [x] Transfer files with SFTP
- [x] Check session recording files
- [x] Test access denial (wrong source IP)
- [x] Test expired grant

### RDP Proxy Tests
- [x] Connect from allowed source IP
- [x] Test access denial (wrong source IP)
- [x] Test access denial (grant for different backend)
- [x] Check .pyrdp recording files
- [x] Replay session with pyrdp-player
- [x] Check audit logs in database

## Contributing

When modifying the codebase:
1. Test both SSH and RDP proxies
2. Verify audit logs are written correctly
3. Check session recordings are created
4. Update this documentation
5. Update ROADMAP.md with progress
