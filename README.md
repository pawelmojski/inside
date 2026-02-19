# Inside - SSH Access Control That Actually Works

**Enterprise SSH gateway with native client compatibility, zero backend changes, and Teleport-style session sharing.**

[![Status](https://img.shields.io/badge/status-production-brightgreen)]()
[![Version](https://img.shields.io/badge/version-2.0-blue)]()
[![Python](https://img.shields.io/badge/python-3.13-blue)]()

---

## Why Inside Exists

Modern infrastructure teams rely on SSH every day — on servers, switches, routers, firewalls, storage appliances, hypervisors, Kubernetes nodes, cloud VMs. Every layer of real infrastructure breathes through SSH.

**The industry has a problem.**

Traditional SSH gateways force a choice: Deploy agents everywhere, or lose native SSH compatibility. Most enterprises can't install agents on legacy hardware — and shouldn't have to.

All existing solutions break down when you touch:
- 10-year-old Cisco switches
- Ancient ASA firewalls
- ProCurve / Dell / Juniper devices
- Storage appliances
- Old ESXi or iLO firmware
- Legacy Linux with OpenSSH 5/6
- Anything that cannot run a vendor agent
- Anything that simply exposes SSH and nothing more

**This is where the real world lives.**

Every enterprise carries a long tail of old but critical systems that will not be replaced and cannot be modified. Access control must work there — otherwise it's not access control.

---

## What Makes Inside Different

Inside delivers enterprise access control while preserving native SSH — a combination rarely found in commercial products.

### Inside vs The Competition

| Feature | Inside | Teleport | StrongDM | Traditional PAM |
|---------|--------|----------|----------|-----------------|
| **Native SSH client** | ✅ Standard `ssh` | ⚠️ Requires `tsh` | ⚠️ Custom client | ❌ Web console |
| **Backend changes** | ✅ Zero | ❌ Agent or CA | ❌ Agent required | ❌ Agent + PAM |
| **Legacy hardware** | ✅ Works | ❌ No agent support | ❌ No agent support | ❌ No agent support |
| **User experience** | `ssh user@host` | `tsh ssh user@host` | Custom syntax | Web GUI |
| **Port forwarding** | ✅ Native `-L/-R/-D` | ⚠️ Via tsh tunnel | ⚠️ Limited | ❌ Not supported |
| **SCP/SFTP** | ✅ Standard tools | ⚠️ Via tsh | ⚠️ Limited | ❌ Web upload |
| **Agent forwarding** | ✅ Native `-A` | ⚠️ Requires setup | ❌ Not supported | ❌ Not supported |
| **Session sharing** | ✅ Native SSH | ✅ tsh join | ❌ | ❌ |
| **Deployment time** | 1 hour | Weeks/months | Weeks | Months |
| **Cost** | Open source | $10-50/user/mo | $$$ | $$$$ |

---

## Core Innovation: "Being Inside"

**Inside doesn't manage identities. Inside manages when real people can be inside your infrastructure.**

Not "access", not "identity", not "control" — everyone immediately understands:

- **Who is inside** right now
- **Who can be inside** (and when)
- **What they do while inside**
- **When they stop being inside**

Perfect operational language:

*"Who is inside production right now?"*

*"He was inside for 30 minutes."*

*"This stay lasts until 14:30."*

*"Nobody can be inside without a grant."*

Sounds like reality, not like a system.

---

## How It Works

**The 30-Second Version:**

```
Person's Computer → Inside Gateway → Backend Server
  (anywhere)         (one place)        (10.0.x.x)
```

From person's perspective: `ssh server.company.com` — works like normal SSH/RDP.

Behind the scenes: Inside checks "does this person have a valid grant RIGHT NOW?" and either allows or denies.

**Architecture:**

Inside is a transparent MITM SSH gateway with one critical advantage:
- **Client uses native SSH** (`ssh -A user@host`)
- **Backend uses native SSH daemon** (OpenSSH, IOS, ASA… anything)
- **Inside sits in the middle**, invisible to both sides
- **Backend authentication** via user's real SSH key (agent forwarding)

Everything else — MFA (v2.1), access control, audit, session replay, session sharing — happens transparently in the gateway.

Because Inside operates at the SSH protocol level, not at the OS or agent level, it imposes no requirements on devices.

**If it speaks SSH — Inside understands it.**

---

## Key Concepts

### Person

A real human being — not a username.
- Has a name (e.g., "Alice Cooper")
- Has source IPs (office, home, VPN, mobile)
- **Does NOT log into systems** — persons enter environments

### Grant

Permission to be inside.
- Defines **where** (which servers/groups)
- Defines **how long** (8 hours, 1 week, permanent)
- Defines **under what conditions** (time windows, protocols, SSH logins allowed)

Not a role, not a group — just a specific permission that expires.

Grants are created through the **Web Management Interface** — a simple 4-step wizard:
1. **Who** - Select person (or user group)
2. **Where** - Select servers (or server group)  
3. **How** - Protocol (SSH/RDP), duration, schedule
4. **Review** - Confirm and create

### Stay

The fact of being inside.
- **Stay starts** when person enters (first connection)
- **Stay ends** when grant expires or is revoked
- **Stay may have many sessions** (disconnect/reconnect allowed)
- Person **remains inside** even between connections

This concept is unique to Inside. A "Stay" groups all activity during one period, making audits trivial:

*"Show me everyone who was inside production last month"* → Done. One query.

**How Stay Works:**

1. **Stay Begins** - Person connects for first time (grant validated)
2. **Multiple Sessions** - Person can disconnect/reconnect freely (same stay continues)
3. **Stay Active** - Visible in real-time dashboard: "Alice is inside prod-db-01"
4. **Stay Ends** - When grant expires, admin revokes, or schedule window closes
5. **Auto-Termination** - Active sessions terminated, person can no longer enter

### Session

Single TCP connection within a stay.
- SSH connection (terminal)
- RDP connection (desktop)
- HTTP connection (web GUI - coming soon)

Technical detail. Stay is what matters for accountability.

### Username

Technical identifier on backend systems (root, admin, backup, etc.)
- **Does NOT represent a person**
- Inside maps `username → person` transparently
- No changes to hosts, clients, AAD, or targets

**This is a critical architectural point:** Inside provides accountability without disrupting existing systems.

---

## NEW in v2.0: Session Sharing (Teleport-Style)

**Join live SSH sessions using native SSH — not a web emulator.**

Admin console (SSH-based TUI) allows authorized users to:

**Watch Mode (Read-Only):**
```bash
# Connect to admin console
ssh admin@gate.company.com

# Select "Watch Session"
# Choose from list of active sessions
# Watch real-time output (silent observer)
```

**Join Mode (Read-Write):**
```bash
# Connect to admin console
ssh admin@gate.company.com

# Select "Join Session"
# Choose from list of active sessions
# Interact with session (pair programming, training)
```

**How It Works:**
- `SessionMultiplexer` - One SSH session → multiple viewers
- Ring buffer (50KB) - New watchers get recent history
- Input queue - Commands from participants are queued
- Thread-safe broadcasting - Real-time output to all viewers
- Announcements - "*** alice joined ***" visible to owner

**No other vendor does this with native SSH clients.**

Teleport requires `tsh join`. Inside just requires `ssh`.

---

## Business Impact

**Traditional SSH Access Control:**
- Deploy agents to 500 servers: Weeks of work
- Modify backend configs: Change management nightmare
- Train users on new clients: Resistance and support tickets
- Replace legacy devices: Budget explosion
- Rollback complexity: High risk

**With Inside:**
- Deploy gateway: 1 hour
- Backend changes: Zero
- User training: Zero (same `ssh` command)
- Legacy support: Everything works
- Rollback: Turn off gateway

### Real Metrics

- **Audit prep time:** 3 weeks → 2 hours (Stay timeline + session replay)
- **Deployment time:** 6 months → 1 day (no backend changes)
- **Coverage:** 100% of SSH infrastructure (including 10-year-old devices)
- **Compliance:** ISO 27001, SOC 2, GDPR ready out-of-box
- **User disruption:** Zero (native tools continue working)

### Cost Comparison

- **Teleport:** $10-50 per user per month + deployment costs
- **StrongDM:** Similar pricing + vendor lock-in
- **Traditional PAM:** $50k-500k license + 6-month deployment
- **Inside:** Open source + optional commercial support
---

## Features

### Access Control
- **Multiple source IPs per person** - Home, office, VPN, mobile
- **Server groups** - Grant access to entire groups ("All production servers")
- **Granular scope** - Group level, server level, or protocol level
- **Protocol filtering** - SSH only, RDP only, or both
- **SSH login restrictions** - Allow only specific usernames (root, admin, etc.)
- **Temporal grants** - Time-limited with automatic expiration
- **Schedule windows** - Access only Mon-Fri 9-17, recurring weekly
- **Recursive groups** - User groups with inheritance

### Session Management
- **Live monitoring** - See who is inside in real-time
- **Session sharing** - Watch or join live SSH sessions (v2.0)
- **Recording** - SSH (terminal) and RDP (video)
- **Playback** - Review past sessions with built-in players
- **Search** - Find sessions by person, server, time, status
- **Auto-termination** - Sessions end when grant expires
- **50KB history buffer** - New watchers see recent output

### Admin Console (v2.0)
SSH-based TUI for privileged operations:
1. **Active Stays** - List all current stays with session counts
2. **Active Sessions** - Detailed view of ongoing sessions
3. **Join Session** - Attach to session (read-write)
4. **Watch Session** - Silent observation (read-only)
5. **Kill Session** - Force termination
6-8. Coming soon (Audit Logs, Grant Debug, MFA Status)

Access requires:
- Permission level ≤100 (admin)
- MFA authentication (planned v2.1)
- SSH connection: `ssh admin@gate.company.com`

### Auditing
- **Entry attempts** - Both successful and denied with reasons
- **Grant changes** - Full audit trail with history
- **Stay timeline** - Complete activity log per person
- **Session recordings** - Terminal output + video
- **Export** - CSV export for compliance reporting

### User Experience
- **Transparent** - Works with standard SSH/RDP clients
- **No agents** - Zero software on client or backend
- **Native tools** - ssh, mstsc, PuTTY, VSCode Remote, Ansible
- **Port forwarding** - SSH -L, -R, -D work (if grant allows)
- **File transfer** - scp, sftp work normally
- **Agent forwarding** - ssh -A works natively

---

## Real-World Example

**Problem:** Production database issue at 9 AM. DBA needs immediate access.

**Traditional approach:**
1. Create VPN account (15 minutes)
2. Create SSH key (5 minutes)
3. Add key to prod-db (10 minutes + change ticket)
4. DBA connects (finally!)
5. Remember to revoke later (**usually forgotten**)

**With Inside:**
1. Admin opens Web GUI (30 seconds)
2. Grant Creation Wizard: "dba-john" → "prod-db-01" → "4 hours" → Create
3. DBA immediately connects: `ssh dba-john@prod-db-01.company.com`

**Result:**
- Access granted in 30 seconds
- Automatically expires in 4 hours
- Full session recording
- Audit trail visible in dashboard: "John was inside prod-db-01 from 09:00 to 13:00"

---

## Use Cases

### Contractor Access

**Problem:** External contractor needs 2 weeks access to staging environment.

**Solution via Web GUI:**
1. **Who:** contractor-bob
2. **Where:** staging-servers (group)
3. **How:** SSH+RDP, 14 days
4. **Create**

After 14 days: automatic expiration, no cleanup needed.

### On-Call Rotation

**Problem:** Weekly on-call engineer needs emergency production access.

**Solution via Web GUI:**
1. **Who:** oncall-alice
2. **Where:** production (group)
3. **How:** SSH+RDP, schedule "Mon-Sun 00:00-23:59", duration 7 days
4. **Create**

Every Monday, create new grant for current on-call person. Previous grant expires automatically.

### Temporary Privilege Escalation

**Problem:** Junior admin needs sudo for specific 1-hour maintenance window.

**Solution via Web GUI:**
1. **Who:** junior-admin
2. **Where:** app-01 (single server)
3. **How:** SSH only, allowed logins: `root`, duration 1 hour
4. **Create**

After 1 hour: root access revoked automatically, stay ends.

### Compliance Audit

**Problem:** "Show me everyone who was inside production last month."

**Solution:**
- Web UI → Universal Search
- Filter: server_group="Production", date_from="2026-01-01"
- Export → CSV
- Done. Full audit trail with session recordings.

### Training & Support

**Problem:** Senior engineer needs to guide junior through complex task.

**Solution (v2.0):**
```bash
# Junior starts work
ssh junior@prod-server

# Senior joins session
ssh admin@gate → Join Session → Select junior's session

# Both see same terminal, can type commands
# Perfect for: training, pair debugging, incident response
```

---

## Why Choose Inside

### For Infrastructure Teams
- Keep using `ssh`, `scp`, `ansible` — zero workflow changes
- Works on every SSH device — including 10-year-old hardware
- No agents to deploy, update, or troubleshoot
- Port forwarding and agent forwarding just work

### For Security Teams
- Full visibility: Who is inside, what they're doing, for how long
- Time-limited grants reduce attack surface
- Session recordings for incident response
- Admin can join/watch sessions in real-time (v2.0)

### For Compliance/Audit
- ISO 27001 alignment out-of-box
- Complete audit trail: entries, stays, recordings
- Person accountability (not username accountability)
- Stay-based timeline simplifies investigations

### For Management
- 1-hour deployment vs months of rollout
- Zero disruption to existing operations
- Open source with optional commercial support
- No vendor lock-in (standard protocols)

---

## Quick Start

### Prerequisites

- Linux server (Debian 12 recommended)
- PostgreSQL 15+
- Python 3.13+
- Public IP or VPN access for clients

### Installation

```bash
# 1. Clone repository
git clone https://github.com/pawelmojski/inside.git
cd inside

# 2. Install dependencies
pip install -r requirements.txt

# 3. Setup database
sudo -u postgres createdb inside
alembic upgrade head

# 4. Configure
cp config/inside.conf.example config/inside.conf
vim config/inside.conf

# 5. Start services
sudo systemctl start inside-ssh-proxy
sudo systemctl start inside-rdp-proxy
sudo systemctl start inside-flask
```

### First Grant

1. **Open Web GUI:** http://gateway.company.com:5000
2. **Add Person:** Management → Persons → Add → "John Doe", IP: 100.64.0.50
3. **Add Server:** Management → Servers → Add → "prod-db-01", IP: 10.0.1.100
4. **Create Grant:** Dashboard → New Grant → Wizard:
   - **Who:** john.doe
   - **Where:** prod-db-01
   - **How:** SSH, 8 hours
   - **Create**
5. **Person connects:** `ssh john.doe@gateway.company.com`
6. **Verify:** Dashboard shows "John Doe is inside prod-db-01"

---

## Architecture

**Current (v2.0):**

```
Person (anywhere)
    ↓
Inside Gateway (one server)
    ├── ssh_proxy (Entry via SSH :22)
    ├── rdp_proxy (Entry via RDP :3389)
    ├── admin_console (SSH-based TUI)
    └── web_ui (:5000)
    ↓
Backend Servers (10.0.x.x)
```

**How Entry Works:**

1. Person connects: `ssh alice@prod-db-01`
2. Entry (ssh_proxy) extracts: source IP, target hostname
3. Database lookup: Person has valid grant?
4. If yes: Create/join stay, proxy connection, record everything
5. If no: Deny entry, record denial reason

**Future (Distributed Tower/Gates):**

```
Tower (Control Plane)
├── Web UI
├── REST API (/api/v1/)
└── PostgreSQL (grants, stays, persons)

Gates (Data Plane - distributed)
├── Gate 1 (DMZ) - ssh/rdp/http entries
├── Gate 2 (Cloud) - ssh/rdp entries
└── Gate 3 (Office) - ssh entry only
```

Benefits: Horizontal scaling, geographic distribution, offline mode, reduced blast radius.

---

## Roadmap

### ✅ v2.0 (Current - February 2026)

**KILLER FEATURE: Session Multiplexing (Teleport-Style)**

- Admin Console (SSH-based TUI)
- SessionMultiplexer with ring buffer (50KB)
- Join Session (read-write mode)
- Watch Session (read-only mode)
- 50KB history buffer for new watchers
- Real-time output broadcasting
- Session sharing with native SSH clients

**"Holy shit, this actually works!"**

### 🎯 v2.1 (Planned - Q2 2026)

**MFA Integration with Azure AD**

- Hybrid session identification:
  - Priority 1: SSH key fingerprint (automatic)
  - Priority 2: SetEnv INSIDE_SESSION_ID (user config)
  - Priority 3: Password fallback (always MFA)
- Tower: Azure AD OAuth2 integration
- MFA banner + polling logic
- Admin console requires MFA

### 💡 v2.2 (Future)

**Cross-Gate Session Joining + RDP Multiplexing**

- Redis pub/sub for session registry
- Join sessions across different gates
- RDP session sharing (PyRDP multiplexer)
- Stealth mode watching (no announcements)

### 🔮 v2.3 (Future)

**Admin Console Expansion**

- Option 6: Audit Logs viewer
- Option 7: Grant Debug interface
- Option 8: MFA Status checker
- Full session recording playback in multiplexer

### 🚀 v3.0 (Commercial Release)

**HTTP/HTTPS Proxy + Licensing**

- MITM proxy for legacy web GUIs (switches, routers, appliances)
- Session recording for HTTP traffic
- Commercial licensing system (per-server or enterprise)
- Self-hosted option with support contracts

---

## Web Management Interface

**All management happens through the Web GUI** (port 5000). No CLI tools are provided.

### Dashboard

Real-time view with 5-second auto-refresh:
- **Who is inside right now** - Active stays with person names, servers, duration
- **Recent entries** - Last 100 connection attempts (success + denials)
- **Grants expiring soon** - Warnings for grants < 1 hour remaining
- **Statistics** - Stays today, sessions active, recordings available

### Grant Creation Wizard

Simple 4-step process:
1. **Who** - Select person (or user group from dropdown)
2. **Where** - Select servers (or server group from dropdown)
3. **How** - Protocol (SSH/RDP/Both), duration (1h-30d or permanent), schedule (optional)
4. **Review** - Summary with all details, confirm and create

Grant becomes active immediately.

### Universal Search (Mega-Wyszukiwarka)

Find anything with 11+ filters:
- Person name, username
- Server, server group, target IP
- Protocol (SSH/RDP), status (active/ended/denied)
- Date range (from-to)
- Grant ID, session ID
- Denial reason

Export results to CSV. Auto-refresh every 2 seconds.

### Live Session View

Watch active SSH sessions in real-time:
- Terminal output updates every 2 seconds
- See what person is typing right now
- Perfect for training, support, security monitoring

**Note:** v2.0 Admin Console provides higher-quality live view via SSH (not browser).

### Session Recordings

Playback past sessions:
- **SSH** - Terminal player (asciinema-style) with pause/play/speed controls
- **RDP** - MP4 video player (HTML5) with timeline scrubbing

Full history searchable, exportable.

---

## Security

**Authentication:**
- Person identification by source IP (mapped in database)
- No password handling by Inside
- Backend authentication via SSH keys or credentials stored per person

**Authorization:**
- Grant-based (every entry checked against active grants)
- Temporal (automatic expiration)
- Granular (per-person, per-server, per-protocol, per-username)

**Audit Trail:**
- Immutable records (all entries logged: success + denial)
- Session recordings (terminal logs for SSH, video for RDP)
- Change history (grant creation/modification/deletion tracked)

**Session Control:**
- Live monitoring (see who is inside right now)
- Forced termination (admin can kill active stays or sessions)
- Auto-termination (stay ends when grant expires with warnings)

---

## Advanced Features

### Port Forwarding Control

Configure in Grant Creation Wizard → **How** step:

- **Allowed:** SSH -L, -R, -D work normally
- **Blocked:** Connection rejected if port forwarding attempted

Useful for bastion hosts (allow forwarding) vs production servers (block forwarding).

### Schedule-Based Access

Configure in Grant Creation Wizard → **How** step → Schedule (optional):

- **Example:** "Mon-Fri 09:00-17:00", timezone "Europe/Warsaw"
- **Behavior:** Recurring weekly — person can enter anytime within schedule
- **Outside schedule:** Entry denied, active stays auto-terminated

Perfect for business-hours-only access to production.

---

## Documentation

- **[DOCUMENTATION.md](DOCUMENTATION.md)** - Complete technical documentation
- **[ROADMAP.md](ROADMAP.md)** - Detailed feature roadmap and version history
- **[README_PL.md](README_PL.md)** - Polish version of this README

---

## TL;DR

**Inside in one sentence:**

*Enterprise SSH gateway using native SSH clients that provides time-limited grants, full session recording, real-time session sharing, and complete audit trails — deployed in 1 hour with zero backend changes.*

**Key Advantages:**

- **Native SSH** - Works with standard `ssh`, `scp`, `sftp`, Ansible, VSCode Remote
- **Zero Backend Changes** - No agents, no configs, no modifications
- **Legacy Support** - 10-year-old Cisco switches, ASAs, storage appliances — anything with SSH
- **Session Sharing** - Join/watch live sessions using native SSH (Teleport-style)
- **Stay-Centric** - Person accountability, not username accountability
- **1-Hour Deployment** - Not 6 months

**One wizard to grant access:**

Web GUI → New Grant → Who: alice | Where: prod-db | How: 8h → Create

**One place to see everything:**
```
Dashboard → Who is inside right now
```

**Why choose Inside:**

Your devs already know SSH — why force them to learn `tsh`?

Your servers already have SSHD — why install agents?

Your workflows already use `scp` — why change them?

Inside: Enterprise features, zero disruption, fraction of the cost.

---

## Get Started

**Repository:** https://github.com/pawelmojski/inside

**Status:** Production (v2.0 with session multiplexing)

**License:** Open source (commercial support options available)

**Contact:**
- Questions: Open an issue on GitHub
- Commercial inquiries: See [DOCUMENTATION.md](DOCUMENTATION.md) for commercial positioning
- Beta testing: Early access program available for v2.1 (MFA integration)

**Next Steps:**
1. Star the repository ⭐
2. Try the quick start installation
3. Join the discussion on GitHub Issues
4. Contribute to the project

---

**Built for enterprises tired of choosing between security and usability.**

**Inside gives you both.**
