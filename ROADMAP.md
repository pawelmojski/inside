# Inside - Roadmap & TODO

## ✅ v2.0 COMPLETED (February 19, 2026) 🚀🔥

### KILLER FEATURES:

**1. Admin Console with Session Multiplexing (Teleport-Style)**

**Holy shit, this actually works!** Native SSH session sharing built into the gate. No external tools required.

**2. MFA Integration with Azure AD**

**Full SAML authentication flow with per-stay MFA and per-grant enforcement.** First production-ready SSH gateway with native MFA via Azure AD.

#### What Was Delivered:

**1. Admin Console** (`src/proxy/admin_console_paramiko.py`)
- Interactive SSH menu for admins (permission level ≤100)
- MFA authentication required
- Direct SSH to gate → Admin console appears
- Clean text UI with proper CRLF line breaks
- 9 menu options (5 functional, 4 coming soon)

**2. Session Multiplexer** (`src/proxy/session_multiplexer.py`)
- One SSH session shared between multiple viewers
- **Ring buffer**: 50KB session history for new watchers
- **Input queue**: Commands from join-mode participants
- **Real-time broadcasting**: Live output to all watchers
- **Announcements**: "*** admin joined ***" notifications
- Thread-safe with RLock synchronization

**3. SessionMultiplexerRegistry (Singleton)**
- Global registry of all active multiplexed sessions
- Lives in gate process memory
- Tracks all joinable sessions
- Automatic cleanup on disconnect

**4. Join Session (Read-Write) - Option 3** 🔥
- Full interaction with live SSH sessions
- Type commands, see output in real-time
- Multiple admins can collaborate simultaneously
- Graceful disconnect (Ctrl+D/Ctrl+C)
- Use cases: Emergency troubleshooting, pair programming, training

**5. Watch Session (Read-Only) - Option 4** 🎯
- Silent observation mode
- See everything, type nothing
- Perfect for monitoring, auditing, training
- No impact on session owner
- Use cases: Junior admin monitoring, security audits

**6. Other Admin Console Functions:**
- **Active Stays** - List all active stays with session count
- **Active Sessions** - Detailed session list with duration
- **Kill Session** - Terminate any active session via API
- **Exit** - Return to shell

**7. Integration & Architecture:**
- Modified `ssh_proxy.py`:
  - Imports SessionMultiplexerRegistry
  - Registers each session on start
  - `forward_channel()` broadcasts output to watchers
  - Checks input_queue for participant commands
  - Unregisters session on disconnect
- Admin API endpoints (`/api/v1/admin/*`):
  - Fixed authentication: Flask-Login → gate bearer token
  - `/active-stays` - List stays
  - `/active-sessions` - List sessions
  - `/kill-session/<id>` - Terminate session
- Tower API integration:
  - Admin console fetches session list
  - Filters to sessions with multiplexers (v2.0+)
  - Cross-gate session tracking

**8. Database & Access Control:**
- Special server: "Gate Admin Console" (10.210.0.76, 10.30.0.76)
- Grant ID 55 (admin), 56 (p.mojski)
- Permission level ≤100 required
- MFA enforcement via existing flow

**9. Deployment:**
- Package: `inside-ssh-proxy-2.0-tproxy.tar.gz` (1.5MB)
- Deployed to both gates:
  - 10.30.0.76 (tailscale-ideo)
  - 10.210.0.76 (tailscale-ideo)
- Flask service restarted with admin API
- Zero downtime deployment

#### Technical Details:

**Files Created:**
- `src/proxy/session_multiplexer.py` (380 lines)
- `src/web/blueprints/admin_api.py` (135 lines)

**Files Modified:**
- `src/proxy/ssh_proxy.py`:
  - Added SessionMultiplexerRegistry import
  - Modified `forward_channel()` for broadcasting
  - Pass `owner_username` for multiplexer
  - Admin console integration
- `src/proxy/admin_console_paramiko.py` (577 lines):
  - Implemented join_session()
  - Implemented watch_session()
  - Added _attach_to_session() for multiplexer integration
  - Fixed CRLF line breaks (\r\n)
  - Removed ASCII art boxes (clean UI)
- `src/api/grants.py`:
  - Added `person_permission_level` to response
- `scripts/build_standalone_package.sh`:
  - Version: 1.11.2-tproxy → 2.0-tproxy

**Architecture:**
```
Backend Server
      ↕
forward_channel()
   (ssh_proxy.py)
      ↕
SessionMultiplexer
   ├─ output_buffer (50KB ring)
   ├─ input_queue (participant commands)
   └─ watchers: {id → channel, mode}
      ↕
┌─────────┬──────────┬──────────┐
│ Owner   │ Admin 1  │ Admin 2  │
│ (full)  │ (watch)  │ (join)   │
└─────────┴──────────┴──────────┘
```

#### Comparison with Commercial Solutions:

| Feature | Inside v2.0 | Teleport | PAM360 | AWS Bastion |
|---------|-------------|----------|---------|-------------|
| Session Join | ✅ FREE | ✅ Paid | ✅ Paid | ❌ No |
| Session Watch | ✅ FREE | ✅ Paid | ⚠️ Limited | ❌ No |
| History Buffer | ✅ 50KB | ✅ Full | ⚠️ Limited | N/A |
| Native SSH | ✅ Yes | ✅ Yes | ⚠️ Agent | ✅ Yes |
| **Cost** | **$0** | **$$$** | **$$$$** | **$0** |

**Inside v2.0 = Enterprise features at zero cost** 🎉

#### Known Limitations:
- SSH sessions only (RDP not yet supported)
- Same gate only (local multiplexer registry)
- v2.0+ sessions only (pre-v2.0 sessions not joinable)
- Owner always sees join/leave announcements (no stealth mode)
- 50KB history buffer (not full session recording)
- Input latency ~100ms in join mode (queue-based)

#### User Feedback:
> "JA PIERDOLE TO DZIAŁA. TO PO PROSTU ZAJEBIŚCIE DZIAŁA!!!"
> "kurwa, jaram się jak dziecko... To jest kill-feature. to jest coś czego chyba nie ma nikt w natywnym ssh!"
> — p.mojski, February 19, 2026

---

### MFA INTEGRATION WITH AZURE AD

#### What Was Delivered:

**1. Azure AD SAML Integration** (`config/saml_config.py`)
- Full SAML 2.0 configuration
- Azure AD tenant: `0d9653a4-4c3f-4752-9098-724fad471fa5`
- Azure AD app: `05275222-1909-4d40-a0d0-2c41df7b512a`
- SAML endpoints configured (login, logout, metadata)
- Certificate embedded (x509cert for signature validation)
- Attribute mappings: email, name, groups

**2. MFA API Endpoints** (`src/api/mfa.py`)
- `POST /api/v1/mfa/challenge` - Create MFA challenge for gate
- `GET /api/v1/mfa/status/<token>` - Poll MFA verification status
- Phase 1: Known user (user_id provided)
- Phase 2: Unknown user (identified via SAML after auth)
- Token-based challenge flow
- Configurable timeout (default 5 minutes)

**3. MFA Challenge Flow:**
```
1. User connects via SSH (unknown source IP or password auth)
2. Gate detects no active stay → requires MFA
3. Gate calls Tower: POST /api/v1/mfa/challenge
4. Tower creates MFAChallenge, returns:
   - mfa_token (secret)
   - mfa_url (https://inside.ideo.pl/auth/saml/login?token=...)
   - mfa_qr (ASCII art QR code for mobile)
   - timeout_minutes
5. Gate displays banner with URL + QR
6. User opens URL in browser → Azure AD SAML login
7. Tower validates SAML response → marks challenge as verified
8. Gate polls Tower: GET /api/v1/mfa/status/<token>
9. Challenge verified → Gate creates stay → connection proceeds
10. User disconnects/reconnects → same stay → MFA skipped
```

**4. MFA Per Stay (Persistent Authentication)**
- First session in stay requires MFA
- Subsequent sessions within same stay skip MFA
- Stay identified by:
  - SSH key fingerprint (automatic, preferred)
  - Source IP + username (fallback)
  - Password auth → always per-session MFA
- Stay expiration ends MFA session

**5. MFA Per Grant (Enforcement)**
- Database: `AccessPolicy.mfa_required` (Boolean, default False)
- Grant creator can enforce MFA for specific grants
- Use cases:
  - Production servers → MFA required
  - Staging/dev → MFA optional
  - Contractor access → MFA always
- Web GUI: Grant Creation Wizard → "Require MFA" checkbox

**6. Database Schema** (`src/core/database.py`)
- `MFAChallenge` table:
  - `token` (unique, urlsafe secret)
  - `gate_id` (which gate initiated)
  - `user_id` (NULL for unknown users)
  - `destination_ip` (target server)
  - `source_ip` (client IP)
  - `ssh_username` (backend username)
  - `verified` (Boolean, False until SAML success)
  - `verified_at` (timestamp of authentication)
  - `user_email` (extracted from SAML)
  - `user_name` (extracted from SAML)
  - `expires_at` (5 min timeout)
- `AccessPolicy.mfa_required` (Boolean)
- `Gate.mfa_enabled` (Boolean, per-gate control)

**7. SSH Proxy Integration** (`src/proxy/ssh_proxy.py`)
- Password authentication flow modified
- Checks for unknown source IP → triggers MFA
- Polling loop for MFA status (2s interval, 5min timeout)
- Banner display with URL and QR code
- Automatic stay creation after MFA success
- Connection proceeds transparently

**8. Web GUI Integration** (Grant Creation Wizard)
- Step 3 (How): "Require MFA" checkbox
- sets `AccessPolicy.mfa_required = True`
- Visible in grant details
- Editable after creation

**9. Configuration:**
- `config/saml_config.py`:
  - `AZURE_TENANT_ID` = "0d9653a4-4c3f-4752-9098-724fad471fa5"
  - `AZURE_APP_ID` = "05275222-1909-4d40-a0d0-2c41df7b512a"
  - `TOWER_BASE_URL` = "https://inside.ideo.pl"
  - `MFA_CHALLENGE_TIMEOUT_MINUTES` = 5
  - `MFA_TOKEN_LENGTH` = 32 bytes

**10. Security Features:**
- Token-based challenge (urlsafe, 32 bytes)
- Time-limited (5 minutes default)
- Source IP validation
- SAML signature verification via Azure AD certificate
- Automatic cleanup of expired challenges
- MFA session bound to stay (not user globally)

**Files Created:**
- `src/api/mfa.py` (226 lines)
- `src/api/mfa_pending.py` (helper functions)
- `config/saml_config.py` (80 lines)

**Files Modified:**
- `src/proxy/ssh_proxy.py`:
  - Added MFA challenge flow in password auth
  - MFA banner display
  - MFA status polling
  - Stay creation with MFA verification
- `src/core/database.py`:
  - Added `MFAChallenge` model
  - Added `AccessPolicy.mfa_required` column
  - Added `Gate.mfa_enabled` column
- Web GUI:
  - Grant wizard "Require MFA" checkbox
  - Grant details display MFA status

**Deployment:**
- Azure AD app configured (Paweł's Azure tenant)
- SAML endpoints tested
- MFA flow tested end-to-end
- Both gates support MFA (10.30.0.76, 10.210.0.76)
- Tower SAML metadata published

#### Use Cases:

**1. Production Access with MFA:**
```
Grant: production-servers
MFA Required: Yes
User connects → MFA challenge → Azure AD → Success → Stay created
User reconnects within 4h → No MFA (same stay)
```

**2. Contractor with Always-MFA:**
```
Grant: contractor-bob, staging-servers
MFA Required: Yes
Duration: 14 days
Every connection requires MFA (password auth, no SSH key)
```

**3. Internal Dev without MFA:**
```
Grant: dev-team, development-servers
MFA Required: No
SSH key authentication → Direct access
```

#### Known Limitations:
- SAML only (no OAuth2 yet)
- Azure AD only (no generic IdP support yet)
- ASCII QR code in banner (not clickable in all terminals)
- 5-minute timeout (not configurable per grant)
- MFA per stay, not per session (future enhancement)

#### Future Enhancements (v2.1+):
- Admin console option 8: MFA Status checker
- MFA dashboard in Web GUI
- Configurable timeout per grant
- MFA audit logs
- Generic SAML IdP support (Okta, Google, etc.)
- OAuth2 flow for modern apps

---

#### Future Enhancements (Session Multiplexing - v2.1+):
- RDP session sharing (via PyRDP multiplexer)
- Cross-gate session joining (via Redis/WebSocket)
- Stealth mode (silent watch without announcements)
- Full session recording playback in multiplexer
- Multiple simultaneous join-mode participants
- Session recording synchronized with multiplexer buffer
- Admin console options 6-8: Audit Logs, Grant Debug, MFA Status

---

## Next Planned: v2.1 (Admin Console Enhancements) 🎯 PLANNED

**Features:**

**1. Admin Console Options 6-8:**
- **Option 6: Audit Logs Viewer**
  - Search and filter audit logs via SSH console
  - Date range, user/person, action type filters
  - Export to CSV for compliance reports
  - Real-time tail mode (follow live events)

- **Option 7: Grant Debug Interface**
  - Troubleshoot access denials interactively
  - Input: person name/IP, target server, protocol
  - Output: Detailed decision tree (why denied)
  - Show active grants, missing permissions, schedule windows
  - Test grant creation with what-if scenarios

- **Option 8: MFA Status Checker**
  - View active MFA sessions (per stay)
  - Show MFA challenges in-flight (waiting for auth)
  - Revoke MFA session (force re-auth)
  - Display user's MFA history (last 30 days)

**2. Session Recording Playback in Admin Console:**
- Navigate to session via Admin Console
- Play SSH session recording in terminal (asciinema-style)
- Pause, resume, speed control (1x, 2x, 5x)
- Jump to timestamp
- Search output for keywords

**3. Cross-Gate Session Information:**
- When multi-gate deployed, show sessions from all gates
- Filter by gate: "Show only sessions on gate-dmz"
- Join/watch sessions on remote gates (via gate-to-gate protocol)
- Unified session registry (Redis pub/sub)

**4. Grant Management via Admin Console:**
- Create grant interactively (wizard-style prompts)
- Edit existing grant (duration, schedule, MFA requirement)
- Revoke grant immediately
- View grant history for person

**5. Stay Management:**
- View stay timeline (all sessions within stay)
- Terminate stay (kills all sessions)
- Extend stay duration (if grant allows)
- Force stay closure with grace period

**Implementation Priority:**
1. Options 6-8 (highest demand from ops teams)
2. Session playback (audit requirement)
3. Grant management (convenience)
4. Cross-gate info (when distributed architecture ready)
5. Stay management (advanced admin feature)

**Timeline:** Q2 2026 (estimated 4-6 weeks)

**Dependencies:**
- None - all features build on existing v2.0 foundation

---

## v2.2 PLANNED (Cross-Gate Architecture + RDP Multiplexing)
- ✅ Tower: Azure AD SAML integration with SSO login
- ✅ Tower: MFA challenge/verify endpoints (/api/v1/mfa/challenge, /api/v1/mfa/status)
- ✅ Tower: Auto-registry from Azure AD group membership
- ✅ Gate: MFA banner with SAML URL + QR code
- ✅ Gate: Polling logic for MFA status
- ✅ Database: `mfa_challenges` table with token, user_id, expiry
- ✅ User experience: Browser-based SAML authentication flow

**Phase 2 Implementation (January 28, 2026):**
- ✅ Database: Added `ssh_key_fingerprint` column to Stay model (VARCHAR 255, indexed)
- ✅ Gate: SSH key fingerprint extraction (SHA256 hash of public key bytes, base64 encoded)
- ✅ Gate: Fingerprint sent in check_grant API call for Stay matching
- ✅ Tower: Stay matching by fingerprint + gate_id + is_active
- ✅ Tower: If Stay found → user identified, skip MFA prompt
- ✅ User experience: First connection = MFA, subsequent connections = fingerprint match
- ✅ Critical fix: Moved check_grant from check_auth_none() to check_auth_publickey()
  - Ensures fingerprint is extracted BEFORE first check_grant call
  - Previous bug: fingerprint=None sent to Tower → always unknown source IP
- ✅ Banner enhancement: Denial messages sent via SSH userauth banner (MSG_USERAUTH_BANNER)
  - Allows personalized banners even when Stay exists but grant expired
  - User sees "Dear Paweł Mojski" instead of generic "Permission denied"

**Session Persistence Flow:**
1. First connection: User connects with SSH key → Gate extracts fingerprint → Tower: unknown IP → MFA challenge
2. User authenticates via SAML → Stay created with ssh_key_fingerprint
3. Second connection: Same SSH key → Gate sends fingerprint → Tower finds Stay → user identified → no MFA
4. Grant expires: Connection terminated with personalized banner
5. Reconnect attempt: Stay exists → user recognized → personalized "no access" message
6. Last session closes: Stay ends → next connection requires MFA again

**Benefits Achieved:**
- ✅ Zero configuration for SSH key users (95%+ of users)
- ✅ Automatic session persistence via SSH public key fingerprint
- ✅ No user action required beyond normal SSH connection
- ✅ Secure identification: Fingerprint + Tower verification
- ✅ Works across multiple terminal windows/tabs
- ✅ Personalized denial messages even when grant expires
- ✅ Clean audit trail: Stay.ssh_key_fingerprint stored in database

**Note:** Priority 2 (SetEnv INSIDE_SESSION_ID) and Priority 3 (password fallback) deferred - SSH key fingerprint covers majority use case.

---

## Next After MFA: Code Optimization & Refactoring 🎯 PLANNED

**Priority:** After MFA Phase 2 (session persistence) is complete and stable

**Problem:** `ssh_proxy.py` has grown to 3300+ lines - becoming unmaintainable "monolith"

### Modularization Plan

**Current structure:**
```
src/proxy/ssh_proxy.py  (3301 lines)
├── SSHProxyServer class (2800+ lines)
├── Helper functions
├── Monitor threads
├── Channel handling
├── Authentication
├── Recording
└── Session management
```

**Proposed structure:**
```
src/proxy/
├── ssh_proxy.py              (200-300 lines - main entry point)
├── server.py                 (SSHProxyServer skeleton - 300 lines)
├── auth/
│   ├── __init__.py
│   ├── authentication.py     (publickey, password, MFA flow)
│   ├── tower_client.py       (grant checks, stay management)
│   └── session_identifier.py (key FP, custom env, fallback)
├── channels/
│   ├── __init__.py
│   ├── session.py            (shell, exec channel handling)
│   ├── forwarding.py         (port forward, reverse forward, proxy intercept)
│   └── sftp.py               (SFTP channel handling)
├── monitoring/
│   ├── __init__.py
│   ├── grant_monitor.py      (grant expiry thread)
│   ├── inactivity_monitor.py (idle timeout thread)
│   └── terminal_title.py     (title updates, helpers)
├── recording/
│   ├── __init__.py
│   ├── recorder.py           (session recording, activity tracking)
│   └── output_filter.py      (command filtering, censoring)
└── utils/
    ├── __init__.py
    ├── terminal.py           (ANSI helpers, title updates)
    └── networking.py         (socket helpers, IP extraction)
```

### Refactoring Goals

1. **Separation of Concerns:**
   - Authentication logic separate from channel handling
   - Monitoring threads in dedicated modules
   - Recording abstracted from transport

2. **Testability:**
   - Each module independently testable
   - Mock-friendly interfaces
   - Unit tests for critical paths (auth, MFA, recording)

3. **Maintainability:**
   - Max 300 lines per file
   - Clear module responsibilities
   - Docstrings and type hints

4. **Performance:**
   - Profile hot paths (forward_channel, recorder)
   - Optimize buffer handling
   - Reduce memory footprint for long sessions

5. **Code Quality:**
   - Remove duplicated code (DRY violations)
   - Consistent error handling patterns
   - Logging standardization

### Migration Strategy

**Phase 1 - Extract helpers (low risk):**
- Move terminal title functions → `monitoring/terminal_title.py`
- Move ANSI helpers → `utils/terminal.py`
- Move IP/socket utils → `utils/networking.py`
- Test: No behavior change

**Phase 2 - Extract monitoring (medium risk):**
- Move grant monitor thread → `monitoring/grant_monitor.py`
- Move inactivity monitor thread → `monitoring/inactivity_monitor.py`
- Test: Timers still work, title updates OK

**Phase 3 - Extract authentication (medium risk):**
- Move Tower API calls → `auth/tower_client.py`
- Move key/password auth → `auth/authentication.py`
- Move session_identifier logic → `auth/session_identifier.py`
- Test: Auth flow unchanged, grants checked correctly

**Phase 4 - Extract channels (high risk):**
- Move port forwarding → `channels/forwarding.py`
- Move SFTP handling → `channels/sftp.py`
- Move session channel → `channels/session.py`
- Test: All channel types work, recording OK

**Phase 5 - Extract recording (high risk):**
- Move Recorder class → `recording/recorder.py`
- Move output filtering → `recording/output_filter.py`
- Test: Sessions recorded correctly, playback works

**Phase 6 - Final cleanup:**
- SSHProxyServer becomes thin orchestrator
- Main entry point cleaned up
- Dead code removal
- Documentation update

### Success Criteria

- ✅ No regression in functionality
- ✅ All existing tests pass
- ✅ Code coverage maintained or improved
- ✅ No file >300 lines (except tests)
- ✅ Import time unchanged or faster
- ✅ Memory usage similar or lower
- ✅ Performance benchmarks pass (connection time, throughput)

### Additional Optimizations

**Beyond modularization:**

1. **Connection pooling to Tower:**
   - Reuse HTTP connections for grant checks
   - Reduce latency on session open

2. **Async I/O for monitoring:**
   - Consider asyncio for monitor threads
   - Reduce thread overhead

3. **Buffer optimization:**
   - Profile `forward_channel` buffer sizes
   - Optimize for typical session patterns

4. **Logging performance:**
   - Lazy string formatting
   - Log level filtering

5. **Startup optimization:**
   - Lazy imports where possible
   - Reduce initial memory footprint

### Documentation Updates

- Architecture diagram showing new module structure
- Developer guide for adding features
- Testing guide for contributors
- Migration notes for deployments

**Status:** Planned after MFA complete. Estimated effort: 2-3 weeks for full refactor + testing.

---

## Architecture Challenges & Design Decisions 🤔 TO DISCUSS

**IMPORTANT:** These are unresolved architectural questions. Document here for future discussion when implementing MFA/session features.

### 1. MFA Enforcement Granularity

**Question:** When should MFA be required?

**Options:**
- **A) Per-Stay (default):** MFA once when Stay opens, all connections within Stay skip MFA
- **B) Per-Connection (high security):** MFA for EVERY connection, even within same Stay
- **C) Per-Target (hybrid):** MFA per-Stay for normal servers, per-Connection for critical servers

**Proposal (C - Hybrid):**
```python
# Grant model:
class Grant:
    mfa_policy = Enum('per-stay', 'per-connection')  # default: per-stay
    
# Example use cases:
- Normal servers (dev, test): mfa_policy = 'per-stay'
- Critical servers (prod DB, routers, switches): mfa_policy = 'per-connection'
```

**Consequences:**
- Per-connection = annoying but secure (for critical infra)
- Per-stay = usable but shared session risk
- Need UI in Tower to configure per-grant

---

### 2. Source IP Management Types

**Question:** How to handle different source IP scenarios?

**Current model:** Source IP = user identity (breaks on shared IPs)

**Types:**
- **User-Owned IP:** Desktop, laptop (static DHCP reservation) → one person always
- **Shared IP:** Windows jump host, VDI pool, NAT gateway → multiple persons
- **No Source IP Restriction:** User can connect from anywhere → MFA-only access

**Proposal:**
```python
# SourceIP model:
class SourceIP:
    address = VARCHAR(45)
    type = Enum('user-owned', 'shared', 'any')
    
# Logic:
if source_ip.type == 'user-owned':
    # Old behavior: source IP = person identity
    person = get_person_by_ip(source_ip)
    
elif source_ip.type == 'shared':
    # NEW: require session_identifier + MFA
    person = get_person_by_mfa(session_identifier)
    
elif source_ip.type == 'any':
    # No IP restriction, pure MFA
    person = get_person_by_mfa(session_identifier)
```

**Migration path:**
- Existing IPs → default to 'user-owned' (backward compatible)
- New shared jump hosts → mark as 'shared'
- Remote users → type 'any' + MFA required

**Edge case - Same person, different IPs:**
```
User at office (IP: 10.1.1.50) opens Stay
→ Goes home, connects via VPN (IP: 10.8.1.200)
→ Should match same Stay? OR new Stay?

Proposal: Match by session_identifier (SSH key FP or custom ID), NOT by source IP
→ Stay lookup: WHERE session_identifier = ? AND person_id = ?
```

---

### 3. Password-Only Target Servers (Switches, Routers)

**Current workaround:** User must NOT send SSH key (`.ssh/config` hack)

**Problem:** Forces user to manage config, error-prone

**Better architecture:**

**Option A - Accept key first (session matching), then ask password:**
```python
# Gate flow:
1. User connects with SSH key → authenticate via key ✅
2. Match to existing Stay (or MFA for new Stay)
3. Target server requires password-only → Gate accepts key but DOESN'T forward it
4. Gate does keyboard-interactive to backend with user's password
5. Stay remains open, session_identifier preserved

Benefits:
- User always sends key (zero config)
- Stay matching works
- Password collected via keyboard-interactive

Implementation:
- Gate: check if target.auth_method == 'password-only'
- If yes: accept user key, DON'T include in backend auth, trigger keyboard-interactive
```

**Option B - Dual authentication (key + password):**
```python
# User authenticates to Gate with key → session_identifier extracted
# Gate authenticates to backend with password (via keyboard-interactive)
# Two separate auth methods, no conflict

Flow:
User --[SSH key]--> Gate --[password]--> Backend
       (session ID)        (user input)
```

**Option C - Keep current hack (user disables key):**
```
ssh -o PubkeyAuthentication=no router.company.local
# Works but forces user config
```

**Recommendation:** Option A or B - preserve key-based session matching while supporting password backends

---

### 4. Stay Lifecycle with Session Identifiers

**Question:** How do Stays close when using session_identifier?

**Current model:**
```
Stay = (person, gate, source_ip)
→ Close when: last connection from that IP ends
```

**New model with session_identifier:**
```
Stay = (person, gate, session_identifier)
→ Close when: ???

Options:
A) Last connection with that session_identifier ends
B) Explicit timeout (e.g., 8 hours)
C) Hybrid: timeout OR last connection + grace period
```

**Proposal (C - Hybrid):**
```python
Stay closes when:
- All connections with session_identifier closed + 5 min grace period
  OR
- Stay age > 8 hours (configurable per-grant)
  OR
- User clicks "Close Stay" in Tower UI
  OR
- Grant expires

Grace period allows:
- Quick reconnects without MFA
- Network hiccups don't force re-auth
```

---

### 5. Multiple Sessions from Same User

**Scenario:** User opens SSH from laptop (session_id = key_fp_1), then opens another SSH from same laptop but different terminal/key

**Question:** One Stay or two Stays?

**Options:**
- **One Stay:** Group by person + gate only (ignore session_identifier for stay grouping)
- **Multiple Stays:** Each session_identifier = separate Stay

**Implications:**

**One Stay approach:**
```python
# Stay lookup:
stay = db.query(Stay).filter_by(
    person_id=person.id,
    gate_id=gate.id,
    is_active=True
).first()

# All connections from same person share Stay
# session_identifier only for MFA skip decision

if stay and stay.session_identifier == current_session_id:
    # Skip MFA (same session)
else:
    # Require MFA (different session, same Stay)
```

**Multiple Stays approach:**
```python
# Stay lookup:
stay = db.query(Stay).filter_by(
    person_id=person.id,
    gate_id=gate.id,
    session_identifier=current_session_id,
    is_active=True
).first()

# Each SSH key/custom ID = separate Stay
# More isolated but more MFA prompts
```

**Recommendation:** Start with Multiple Stays (simpler, more secure), evaluate user feedback

---

### 6. AAD Group Sync Strategy

**Question:** How to handle users removed from AAD "insideAccess" group?

**Options:**
- **A) Check at login only:** User removed from group → next login fails, existing sessions continue
- **B) Background sync:** Cron job fetches AAD group members, disables persons not in group
- **C) Hybrid:** Check at login + periodic sync (e.g., daily)

**Recommendation:** Start with A (simple), add B if needed

**Implementation A (login-time check):**
```python
# Every MFA callback:
if INSIDE_ACCESS_GROUP not in aad_claims['groups']:
    # Removed from group → deny access
    # Existing Stays continue (until they expire naturally)
    return "Access revoked", 403
```

**Implementation B (background sync):**
```python
# Cron job (daily):
aad_members = fetch_aad_group_members(INSIDE_ACCESS_GROUP)
db_persons = db.query(Person).filter_by(created_via='aad-auto-registry')

for person in db_persons:
    if person.email not in aad_members:
        # Mark as disabled
        person.disabled = True
        # Close all active Stays
        db.query(Stay).filter_by(person_id=person.id, is_active=True).update({'is_active': False})
```

**Tradeoff:** Immediate revocation (B) vs simpler implementation (A)

---

### 7. MFA Token Delivery Method

**Current plan:** Gate sends banner with clickable URL

**Alternative ideas:**

**A) Email/Slack notification:**
```python
# Send MFA link via email
send_email(
    to=person.email,
    subject="Inside MFA Required",
    body=f"Click to authenticate: {mfa_url}"
)
```

**B) QR code in terminal:**
```python
# Generate QR code, display in SSH session
import qrcode
qr = qrcode.make(mfa_url)
print_ascii_qr(qr)  # ASCII art QR code in terminal
```

**C) SMS (expensive, requires Twilio/etc.)**

**Recommendation:** Start with banner URL (simple), optionally add QR code for convenience

---

## Summary: What needs resolution before implementation

1. ✅ **MFA phasing:** Agreed - MFA first, session persistence later
2. ❓ **MFA granularity:** Per-stay vs per-connection policies (propose: per-grant config)
3. ❓ **Source IP types:** user-owned vs shared vs any (propose: add type field)
4. ❓ **Password-only targets:** Better than current .ssh/config hack? (propose: accept key, forward password)
5. ❓ **Stay lifecycle:** Timeout strategy with session_identifier (propose: hybrid timeout + grace period)
6. ❓ **Multiple sessions:** One Stay or separate? (propose: separate Stays initially)
7. ❓ **AAD sync:** Login-time vs background (propose: start login-time, add background if needed)
8. ❓ **MFA delivery:** Banner vs QR vs email (propose: banner + optional QR)

**Action:** Review and decide on each before starting Phase 1 implementation.

---

## Future Features - Wish List 💡

### Reverse Forwarding Policy Control (Corporate Proxy Intercept)

**Problem:** SSH reverse forwarding (`-R`) is dangerous - allows backend server to connect anywhere via user's network, bypassing corporate firewall policies.

**Legitimate Use Case:** Admins need to provide internet access to isolated servers via corporate proxy:
```bash
# Admin wants:
ssh -R 3128:proxy.company.com:3128 isolated-server

# Server can then:
export http_proxy=http://localhost:3128
apt update  # via corporate proxy ✅
```

**Security Risk:**
```bash
# Malicious/compromised server:
ssh -R 8080:evil-site.com:443 production-server

# Server bypasses firewall:
curl http://localhost:8080  # → evil-site.com ⚠️
```

**Solution: Three-Level Reverse Forwarding Policy**

**Policy 1 - Deny (Secure Default):**
- Block ALL reverse forwarding requests
- Use for production servers with no internet needs
- Error: `channel open failed: administratively prohibited`

**Policy 2 - Corporate Proxy Only (Smart Intercept):**
- Accept reverse forward request from user's SSH client
- **Intercept destination** - ignore user-requested target
- **Gate acts as proxy** - connects to corporate proxy, NOT to client
- Client never receives connection on reverse channel (complete isolation)
- Traffic flow: `Backend Server ↔ Gate ↔ Corporate Proxy` (client bypassed)
- User thinks they're forwarding to `jump:3128`, server actually gets `proxy.company.com:3128`
- Benefits:
  - ✅ Server gets internet via corporate proxy
  - ✅ Client network NOT exposed (zero inbound connections)
  - ✅ Cannot bypass to arbitrary destinations
  - ✅ Gate terminates both ends of connection
  - ✅ Audit log shows requested vs actual destination

**Policy 3 - Allow All (Backward Compatible):**
- Current behavior - forward to client's network
- Use only for trusted admin scenarios
- Full reverse forwarding capability

**Grant Model:**
```python
class Grant:
    reverse_forwarding_policy = Enum('deny', 'corporate-proxy', 'allow-all')
    corporate_proxy_host = VARCHAR(255)  # e.g., 'proxy.company.com'
    corporate_proxy_port = INT           # e.g., 3128
```

**Gate Implementation:**
```python
def check_global_request(self, kind, msg):
    # SSH -R request handler
    if kind != 'tcpip-forward':
        return False
    
    policy = self.current_grant.reverse_forwarding_policy
    
    if policy == 'deny':
        return False
    
    elif policy == 'corporate-proxy':
        # Accept request, store mapping for intercept
        bind_port = msg.get_int()
        self.reverse_forward_mappings[bind_port] = {
            'requested_host': msg.get_string(),
            'requested_port': msg.get_int(),
            'actual_host': self.current_grant.corporate_proxy_host,
            'actual_port': self.current_grant.corporate_proxy_port
        }
        return True  # Accept, but Gate will intercept connections
    
    elif policy == 'allow-all':
        return True  # Normal reverse forward to client

def handle_reverse_forward_connection(self, bind_port):
    # Backend opened connection to reverse-forwarded port
    if bind_port in self.reverse_forward_mappings:
        # Corporate proxy mode: Gate acts as proxy
        # Client SSH session is NEVER contacted
        mapping = self.reverse_forward_mappings[bind_port]
        
        # Gate connects directly to corporate proxy
        proxy_sock = socket.create_connection(
            (mapping['actual_host'], mapping['actual_port'])
        )
        
        # Bridge: backend ↔ Gate ↔ corporate proxy
        # Client is completely bypassed (no inbound connections)
        return proxy_sock
    else:
        # Normal mode: backend ↔ Gate ↔ client
        return self.transport.open_forwarded_tcpip_channel(...)
```

**User Experience:**
```bash
# Admin with "corporate-proxy" policy:
admin@laptop$ ssh -R 3128:anything:1234 server

# Inside server session:
admin@server$ export http_proxy=http://localhost:3128
admin@server$ curl google.com
# Works via proxy.company.com:3128 ✅

# Gate audit log:
# Reverse forward intercept: server:45678 → proxy.company.com:3128
# (user requested: anything:1234)
```

**Benefits:**
- ✅ Servers get internet access (via controlled proxy)
- ✅ No arbitrary network bypass
- ✅ Client network isolation maintained
- ✅ Audit trail of intercepts
- ✅ Granular per-grant control

**Status:** Wish list - implement after MFA Phase 1

---

## Current Status: v1.10.10 (Terminal Window Title Countdown) - January 2026 ✅ COMPLETE

**v1.10.10 Completions:**
- ✅ **Terminal Window Title Updates**: Non-intrusive real-time countdown in window title
  - ANSI OSC 2 escape sequence: `\033]2;TITLE\007` (xterm, PuTTY, Windows Terminal compatible)
  - Format: `Inside: server-name | Grant: Xm | Idle: Y/Zm`
  - Warning indicator: `[!]` suffix when <5 minutes remaining
  - Server name truncation: Max 20 chars (longer names: "very-long-serve...")
  - Update frequency: 60s normally, 10s when warning (<10min grant OR >50min idle)
  - Disconnect status: `Inside: server-name | disconnected` on session end
  - Helper functions: `update_terminal_title()`, `clear_terminal_title()`
  - Integration: Only inactivity monitor updates title (reads grant info from metadata dict)
  - Session metadata: `session_metadata` dict stores grant_end_time, timeout, server_name
  - Disconnect timing: Clear in `forward_channel()` finally block (before channel.close())
  - Benefits: Always-visible countdown, no terminal spam, PuTTY compatible (ASCII only)
  - Edge case tested: PuTTY keepalive does NOT reset idle timer ✅
  - Title examples:
    * Normal: `Inside: vm-lin1 | Grant: 2h15m | Idle: 12/60m`
    * Warning: `Inside: srv-db01 | Grant: 4m | Idle: 56/60m [!]`
    * Permanent: `Inside: backup-srv | Idle: 23/60m`
    * Disconnected: `Inside: rancher2 | disconnected`

## Previous Status: v1.10.9 (Session Inactivity Timeout) - January 2026 ✅ COMPLETE

**v1.10.9 Completions:**
- ✅ **Inactivity Timeout**: Automatic disconnect after period of no activity
  - Database: Added `access_policies.inactivity_timeout_minutes` (default 60, NULL/0 = disabled)
  - GUI: Field in grant creation/edit forms with validation
  - API: Returns `inactivity_timeout_minutes` in `/api/v1/grants/check` response
  - Tracking: `session_last_activity` dict updated on every data transmission
  - Activity detection: Keystrokes, output, SFTP transfers all reset timer
  - Monitor thread: Separate `monitor_inactivity_timeout()` per session
  - Warnings: 5 minutes and 1 minute before disconnect (shell only, not SFTP)
  - Welcome banner: "Inactivity timeout: X minutes"
  - Disconnect message: "Disconnected due to inactivity (X minutes idle)"
  - Termination reason: `inactivity_timeout` for proper session tracking
  - Benefits: Closes abandoned sessions, frees Stay resources, better security
  - Deployment: Tower (Flask) and Gate (tailscale-etop) both updated

## Previous Status: v1.10.8 (Real-Time Grant Time Management) - January 2026 ✅ COMPLETE

**v1.10.8 Completions:**
- ✅ **Grant Extension Detection**: Real-time monitoring of policy end_time changes
  - Heartbeat (30s) detects grant extensions via `/api/v1/grants/check` effective_end_time
  - `session_grant_endtimes` dict tracks current grant end_time per session
  - Monitor thread detects extensions and restarts countdown from new end_time
  - User notification: "GOOD NEWS: Your access grant has been extended!"
  - No more disconnects at original time after admin renews grant
- ✅ **Grant Shortening Detection**: Real-time monitoring of policy reductions
  - Heartbeat detects when grant end_time is reduced (shortened)
  - Monitor restarts countdown with proper 5min/1min warnings at new time
  - User notification: "NOTICE: Your access grant has been shortened!"
  - Immediate effect: ostrzeżenia pokazują się w odpowiednich momentach
- ✅ **Smart Warning Logic**: Prevents duplicate/confusing messages
  - Flag `grant_extended_during_warning` prevents warning after extension
  - When grant changes during warning period: restart countdown, skip stale warning
  - Clean user experience: only relevant messages shown
- ✅ **Heartbeat Change Detection**: Unified extension AND shortening
  - Changed: `if new_end_time > old_end_time` → `if new_end_time != old_end_time`
  - Both increases and decreases update `session_grant_endtimes` dict
  - Monitor receives notification regardless of direction of change
- ✅ **Grant UI Improvements** (v1.10.6):
  - Removed confusing policy popover
  - Renamed "Policy" → "GRANT" in session details
  - Added recipient info: "User: name" or "Group: name"
  - Added validity period: "Valid until: time CET" or "Permanent"
  - Unified revoke button (always calls `/policies/revoke/<policy_id>`)
  - Timezone display: Warsaw CET/CEST using `|localtime` filter
- ✅ **Grant Defaults** (v1.10.7):
  - Default grant duration: 1 hour (not permanent)
  - Duration field required with `value="1h"`
  - Backend validation: rejects empty duration_text
  - Permanent grants require explicit checkbox or "permanent" keyword
  - Renew button: +1 hour (was +30 days)
  - Permanent grant monitoring: always runs, detects revocation

## Previous Status: v1.10.2 (Maintenance + Port Forwarding) - January 2026 ✅ COMPLETE

**v1.10.2 Completions:**
- ✅ **Maintenance Mode Auto-Disconnect**: Heartbeat forces active sessions to disconnect
  - Fixed `check_and_terminate_sessions()` to work without database access
  - Changed `active_connections` from tuple to dict with full session metadata
  - Heartbeat checks each session via Tower API `/api/v1/auth/check`
  - Denied sessions get 5-second grace period via `session_forced_endtimes`
  - `monitor_grant_expiry` thread handles forced disconnects
  - User confirmed: maintenance mode now disconnects active sessions
- ✅ **Stay API Fixed**: Server model attribute correction
  - Fixed `Server.hostname` → `Server.name` in Stay creation endpoint
  - Fixed `start_stay()` return type: returns full dict instead of just stay_id
  - Stay creation working correctly in both TPROXY and NAT modes
- ✅ **Remote Port Forwarding (-R) Fixed**: Direct SSH channels for cascade
  - Simplified architecture: Backend SSH → Gate SSH → Client SSH (no intermediate listeners)
  - Works in both TPROXY and NAT modes using direct forwarded-tcpip channels
  - Removed complex pool IP listener logic - cleaner and more reliable
  - Tested: `ssh -R 2225:host:25` works correctly in TPROXY mode
- ✅ **Grant Check Optimization**: Reduced API calls from 4 to 1 per connection
  - Removed early grant check before authentication
  - Removed check_auth_none grant verification
  - Implemented grant result caching per connection
  - Grant checked only once during first auth method, cached for subsequent attempts
  - Heartbeat continues to check grants for active sessions every 30s

## Previous Status: v1.10 (TPROXY + Standalone) - January 2026 ✅

**v1.10 Completions:**
- ✅ **TPROXY Transparent Proxy**: Linux kernel TPROXY v4 for SSH traffic interception
  - Dual-mode operation: NAT (port 22) + TPROXY (port 8022)
  - Original destination extraction via `getsockname()` (SO_ORIGINAL_DST)
  - iptables mangle PREROUTING with TPROXY target
  - Routing table 100 with fwmark 1
  - No iptables REDIRECT required - true transparent proxy
- ✅ **Standalone Gate Package**: 73KB deployment package for remote gates
  - Build system: `scripts/build_standalone_package.sh`
  - Dynamic venv creation on target (no GLIBC conflicts)
  - Unified configuration: `/opt/inside-ssh-proxy/config/inside.conf`
  - Environment variables: INSIDE_SSH_PROXY_CONFIG, INSIDE_GATE_CONFIG
  - Systemd service: `inside-ssh-proxy.service`
  - Zero database dependencies in gate code
- ✅ **Pure API Architecture**: Gates use ONLY Tower API
  - Complete removal of database access from gate code
  - All operations via TowerClient: sessions, stays, recordings, cleanup
  - New endpoint: POST /api/v1/gates/cleanup (stale session cleanup)
  - Clean separation: Gate = SSH proxy + API client, Tower = API + database
  - Works for both standalone gates and all-in-one deployments
- ✅ **Live Recording View**: Real-time session monitoring with auto-refresh
  - Format detection: .rec files with text header + JSONL
  - Live parsing bypasses cache (file written in real-time)
  - Auto-reload page on session end to show complete recording
  - ANSI-to-HTML with terminal colors and escape sequences
  - Yellow highlight animation for new events
  - Client/Server filtering and search
- ✅ **Production Deployment**: Gate "tailscale-etop" (10.210.0.76)
  - Tailscale exit gateway with TPROXY interception
  - IP pool: 10.210.200.128/25
  - Token: aabbccddetop
  - Recording streaming to Tower API working
  - Stay creation and lifecycle management validated

## Previous Status: v1.9 (JSONL Streaming) - January 2026 ✅

**v1.9 Completions:**
- ✅ Tower REST API: 15 endpoints implemented and tested
- ✅ Recording API: start/chunk/finalize endpoints
- ✅ ssh_proxy refactored: All AccessControlV2 → TowerClient API calls
- ✅ Database schema: gates, stays, sessions.gate_id, sessions.stay_id, ip_allocations.gate_id
- ✅ Web UI: Gate/Stay columns in sessions list and detail
- ✅ Recording parser: Dual-format support (JSON legacy + JSONL streaming)
- ✅ ANSI-to-HTML conversion: Terminal colors in Web UI
- ✅ Format auto-detection: JSON vs JSONL vs raw binary
- ✅ SSHSessionRecorder: JSONL streaming with buffering (50 events / 3s flush)
- ✅ IP Pool per Gate: gate_id in ip_allocations, overlapping IPs between gates allowed
- ✅ IPPoolManager: Gate-aware IP allocation with unique constraint (ip, gate_id)
- ✅ AccessControlV2: Gate-specific IP resolution (find_backend_by_proxy_ip with gate_id)
- ✅ Web UI: Gates management CRUD with IP pool configuration
- ✅ Stay Logic: Person-centric tracking (first session opens Stay, last closes)
- ✅ Tower API: Automatic Stay management in /sessions/create and /sessions/<id> PATCH
- ✅ **Dashboard Live Timeline**: Unified daily visualization
  - Timeline from first stay today → now (no wasted space)
  - All Stays as horizontal rows with person badges
  - Sessions nested inside Stay rows (positioned on daily timeline)
  - Interactive popovers with rich metadata tables
  - Clickable links: Person → user detail, Server → server detail
  - "View Details" button → full session view
  - Auto-close previous popover when opening new one
  - Min-width 50px for sessions, max-width to prevent overflow
  - Green dot (●) indicator for active sessions
  - Auto-refresh every 5 seconds with smooth updates
  - People Inside counter tracking active stays

````

## Previous Status: v1.8 (Mega-Wyszukiwarka) - January 2026 ✅

**Operational Services:**
- ✅ SSH Proxy: `0.0.0.0:22` (systemd: jumphost-ssh-proxy.service)
- ✅ RDP Proxy: `0.0.0.0:3389` (systemd: jumphost-rdp-proxy.service)  
- ✅ Flask Web: `0.0.0.0:5000` (systemd: jumphost-flask.service)
- ✅ MP4 Workers: 2 instances (systemd: jumphost-mp4-converter@1/2.service)
- ✅ PostgreSQL: Access Control V2 with policy-based authorization
- ✅ Session Monitoring: Real-time tracking with live view (SSH + RDP MP4)
- ✅ Auto-Refresh Dashboard: 5-second updates via AJAX
- ✅ RDP MP4 Conversion: Background queue with progress tracking
- ✅ Recursive User Groups: Hierarchical permissions with inheritance 🎯
- ✅ Port Forwarding Control: Per-policy SSH forwarding permissions 🎯
- ✅ SSH Port Forwarding: -L (local), -R (remote), -D (SOCKS) 🎯
- ✅ Policy Management: Renew/Reactivate with group filtering 🎯
- ✅ Grant Expiry Auto-Disconnect: Warnings & auto-termination 🎯
- ✅ Schedule-Based Access Control: Recurring time windows with timezone support 🎯
- ✅ Policy Audit Trail: Full change history with JSONB snapshots 🎯
- ✅ Policy Editing: Edit schedules without revoke/recreate 🎯
- ✅ Schedule Display: Tooltips showing all time windows 🎯
- ✅ Connection Tracking: policy_id, denial_reason, protocol_version 🎯
- ✅ **Mega-Wyszukiwarka**: Universal search with 11+ filters, auto-refresh, CSV export 🎯 NEW v1.8

**Recent Milestones:**
- v1.8: Mega-Wyszukiwarka (January 2026) ✅ COMPLETED
- v1.7.5: Connection Attempts Logging (January 2026) ✅ COMPLETED
- v1.7: Policy Audit Trail & Edit System (January 2026) ✅ COMPLETED
- v1.6: Schedule-Based Access Control (January 2026) ✅ COMPLETED
- v1.5: Grant Expiry Auto-Disconnect with Warnings (January 2026) ✅ COMPLETED
- v1.4: SSH Port Forwarding & Policy Enhancements (January 2026) ✅ COMPLETED
- v1.3: RDP MP4 Conversion System (January 2026) ✅ COMPLETED
- v1.2-dev: RDP Session Viewer (January 2026) ✅ COMPLETED
- v1.1: Session History & Live View (January 2026) ✅ COMPLETED
- v1.0: Access Control V2 with Flexible Policies (December 2025)
- v0.9: Real-time Session Tracking with UTMP/WTMP (December 2025)

## 🚀 Planned Features

### v1.11 - Simplify Grant Expiry Logic 🎯 ✅ COMPLETED (January 28, 2026)

**Problem Identified**: Current implementation was overly complex AND BUGGY
- Multiple time tracking variables: `grant_end_time`, `session_grant_endtimes`, `session_forced_endtimes`, `effective_end_time`
- Complex state management: `grant_was_extended`, `grant_extended_during_warning` flags
- Convoluted logic: Detect extension vs shortening, restart countdown, skip warnings
- Hard to maintain and debug
- **CRITICAL BUG DISCOVERED (Jan 28, 2026 - MFA Phase 2):**
  - `check_grant` returns `effective_end_time` (schedule-aware, MFA-adjusted)
  - `sessions.py` returns `grant.end_time` from AccessPolicy table (base policy end, NOT effective)
  - Gate receives WRONG time from session creation response
  - Monitor starts with OLD time (before MFA), detects "extension" every iteration
  - Results in spam warnings and premature disconnects
  - **Root cause**: No single source of truth for grant expiry time

**Lessons from MFA Phase 2 Debugging:**
1. **Time synchronization is critical**: When MFA extends grant, all components must use NEW time immediately
2. **API response inconsistency**: check_grant vs sessions.py return different times for same grant
3. **Complex data flow**: grant_end_time passed as parameter → stored in dict → read in loop → compared → updated → sent to user
4. **Bug reproduction**: MFA auth → welcome shows "38 min" → warnings show "5 min" → disconnect after "extension" loop
5. **Fix attempts failed**: Tried updating session_grant_endtimes at various points, but monitor thread already started with wrong value

**Proposed Simplification**:
1. **Single source of truth**: API returns one `end_time` (no effective/forced/grant distinction)
   - **CRITICAL**: check_grant, sessions.py, heartbeat ALL return SAME effective_end_time
   - Gate never queries AccessPolicy.end_time directly (it's wrong for schedules/MFA)
2. **Periodic polling**: Monitor checks API every 10-30 seconds for current `end_time`
   - **New endpoint**: GET /api/v1/sessions/{session_id}/grant_status → returns current effective_end_time
   - Monitor polls this, NOT local dict variable
3. **State-based warnings**: 
   - Track which warnings were sent: `sent_5min_warning`, `sent_1min_warning`
   - Each iteration: `end_time = api.get_grant_status()` then calculate `remaining = end_time - now()`
   - If `remaining <= 5min` and not `sent_5min_warning` → send warning, set flag
   - If `remaining <= 1min` and not `sent_1min_warning` → send warning, set flag
   - If `remaining <= 0` → disconnect
4. **No restart logic**: Just check current state and react accordingly
5. **Automatic handling**: Works for extension, shortening, and revoke without special cases

**Benefits**:
- Much simpler code (~100 lines vs current ~400 lines)
- Easier to understand and maintain
- No complex state machines or countdown restarts
- Natural handling of all time change scenarios
- Less prone to edge case bugs
- **FIXES MFA GRANT TIME BUG**: No local cache, always fresh from API

**Implementation Notes**:
- Remove: `session_grant_endtimes` dict completely (source of truth is API)
- Remove: Extension/shortening detection logic (just react to current state)
- Remove: Countdown restart mechanism with while loops
- Remove: `grant_end_time` function parameter (monitor fetches from API)
- Keep: Basic warning flags per session
- Add: New API endpoint for grant status polling
- Simplify: Monitor thread to just periodic check + react pattern

**Migration Path (after MFA Phase 2 complete)**:
1. ✅ Add GET /api/v1/sessions/{session_id}/grant_status endpoint
2. ✅ Rewrite monitor_grant_expiry() to poll API instead of using parameter
3. ✅ Test: Extension, shortening, revoke, MFA time changes
4. ✅ Remove session_grant_endtimes dict and related code
5. ✅ Document new architecture

**Implementation Completed (January 28, 2026)**:

**1. New API Endpoint - Single Source of Truth**:
- Created `/api/v1/sessions/{session_id}/grant_status` (src/api/sessions_grant_status.py)
- Returns: `{'valid': bool, 'end_time': 'ISO+Z' or null, 'reason': str}`
- Queries AccessPolicy directly, no caching
- Always returns UTC time with 'Z' suffix

**2. Gate Polling Architecture**:
- Rewrote `monitor_grant_expiry_v11()` (src/proxy/ssh_proxy.py lines 2096-2250)
- Polls API every 10 seconds using TowerClient.get_session_grant_status()
- State-based warnings: `sent_5min_warning`, `sent_1min_warning` flags
- No restart logic - just check current state and react
- Simplified from ~400 lines to ~150 lines

**3. Code Cleanup**:
- Removed `session_grant_endtimes` dict tracking
- Removed `session_forced_endtimes` dict tracking
- Removed extension/shortening detection logic
- Removed `grant_was_extended`, `grant_extended_during_warning` flags
- Removed countdown restart loops
- Old monitor disabled, v1.11 monitor active

**4. Critical Timezone Fix**:
- Problem: Postgres interpreted naive datetime as CET (local time), not UTC
- SQLAlchemy wrote UTC but Postgres compared as CET → valid grants appeared expired
- Solution: `connect_args={'options': '-c timezone=utc'}` in SQLAlchemy engine (src/core/database.py)
- Database columns remain `timestamp without time zone` (naive datetime)
- All Postgres sessions now interpret naive as UTC (consistent with Python)
- API always returns `datetime.isoformat() + 'Z'` for naive UTC

**5. Datetime Parsing Robustness**:
- Gate handles both 'Z' suffix and +HH:MM timezone formats
- Converts to naive UTC using `astimezone(pytz.utc).replace(tzinfo=None)`
- Works regardless of database column type (naive or timestamptz)

**Benefits Achieved**:
- ✅ Much simpler code (~150 lines vs ~400 lines)
- ✅ Easier to understand and maintain
- ✅ No complex state machines or countdown restarts
- ✅ Natural handling of all time change scenarios (extension/shortening/revoke)
- ✅ FIXES MFA GRANT TIME BUG: Always fresh data from API, no stale cache
- ✅ No timezone comparison bugs: Consistent UTC handling throughout
- ✅ Less prone to edge case bugs

**Testing Results**:
- MFA authentication with grant → ✅ Correct time displayed
- Connection established → ✅ No premature disconnects
- Grant expiry warnings → ✅ Working correctly (5-minute, 1-minute warnings)
- Grant expiry disconnect → ✅ Clean disconnect with countdown message

### v1.11.1 - MFA Phase 2: Full Password Auth & Per-Server MFA 🎯 ✅ COMPLETED (January 28, 2026)

**Problems Solved**:
1. MFA Phase 1 required MFA for EVERY connection, even with same SSH key
2. Password authentication without SSH keys was not supported
3. Agent forwarding failures on backend required manual reconnection
4. Keyboard-interactive auth bypassed MFA flow
5. Network switches using keyboard-interactive couldn't connect
6. Per-server MFA enforcement not possible (Stay always bypassed MFA)

**Solution - Comprehensive SSH Authentication & MFA**:
- SSH key fingerprint persistence in Stay (automatic session tracking)
- Password authentication with full MFA support (no SSH keys required)
- Password fallback when backend rejects agent keys
- Keyboard-interactive → password auth fallback for MFA
- Per-server MFA enforcement via policy.mfa_required flag
- 3-tier user identification: fingerprint → known IP → MFA token

**Implementation (January 28, 2026)**:

**1. Database Schema**:
```sql
ALTER TABLE stays ADD COLUMN ssh_key_fingerprint VARCHAR(255);
CREATE INDEX idx_stays_fingerprint ON stays(ssh_key_fingerprint);
-- ONE Stay per user+gate: UNIQUE(user_id, gate_id, is_active=true)
```

**2. SSH Key Fingerprint Persistence** (src/proxy/ssh_proxy.py):
- Extract SHA256 fingerprint in `check_auth_publickey()` (line 514)
- Format: `base64.b64encode(hashlib.sha256(key.asbytes()).digest())`
- Example: `FrMnH/bvPbA5prMYh5QNbKs/Z4YLCXRrxY5uj1njtjA=`
- Stay matching: First connection with key → MFA → Stay created with fingerprint
- Subsequent connections: Same fingerprint → user identified → skip MFA (unless policy requires)

**3. Password Authentication with MFA** (src/proxy/ssh_proxy.py lines 456-620):
- `check_auth_password()`: Full MFA flow support
  - Check grant with fingerprint=None (unknown user)
  - If mfa_required → create challenge → send banner via MSG_USERAUTH_BANNER
  - Poll status every 2s (5min timeout)
  - After MFA verified → re-check grant with mfa_token
  - Store password for backend authentication
- Stay creation without fingerprint (password-only sessions)
- Fingerprint upgrade: Stay created via password → key arrives later → fingerprint added

**4. Password Fallback After Agent Key Rejection** (src/proxy/ssh_proxy.py lines 2825-2860):
- Problem: Laptop with agent forwarding, but keys not on backend
- Gate accepts key → backend rejects all agent keys → **NEW**: Gate prompts for password
- Flow: Send password prompt via channel → read user input → authenticate backend
- Critical for mixed environments (keys on gate, passwords on backends)

**5. Keyboard-Interactive MFA Handling** (src/proxy/ssh_proxy.py lines 823-860):
- Problem: OpenSSH client prefers keyboard-interactive over password auth
- Original behavior: keyboard-interactive had no MFA support → silent failure
- **NEW**: Detect mfa_required → reject keyboard-interactive with AUTH_FAILED
- Client fallback: OpenSSH falls back to password auth (which has MFA)
- Network switches: keyboard-interactive still works when MFA not required

**6. Per-Server MFA Enforcement** (src/api/grants.py lines 391-425):
```python
if gate.mfa_enabled and selected_policy and selected_policy.mfa_required:
    if has_fingerprint_stay:
        # Force MFA even with existing Stay
        pass  # Fall through to MFA required logic
    
    if not recent_verified_challenge:
        return jsonify({'allowed': False, 'mfa_required': True})
```
- Policy can enforce MFA for specific servers
- Overrides Stay-based fingerprint bypass
- Recent challenge window: 60 seconds
- Use case: Sensitive servers always require MFA

**7. 3-Tier User Identification** (src/api/grants.py lines 178-235):
```python
# Priority 1: Fingerprint match (if fingerprint provided)
stay_by_fingerprint = Stay.query.filter(
    ssh_key_fingerprint == fingerprint,
    gate_id == gate.id,
    is_active == True
).first()

# Priority 2: Known source IP
known_ip = UserSourceIP.query.filter(
    source_ip == source_ip,
    is_active == True
).first()

# Priority 3: MFA token (verified challenge)
challenge = MFAChallenge.query.filter(
    token == mfa_token,
    verified == True
).first()
```
- **CRITICAL**: SSH username (e.g., "p.mojski") NOT used for person identification
- Username only for backend login validation (policy.ssh_logins)
- Secure: Anyone can provide any username, identification via fingerprint/IP/MFA only

**8. Source IP Markers** (src/core/access_control_v2.py lines 240-290):
- `_stay_{stay_id}` - Active Stay marker (lookup user from Stay table)
- `_identified_user_{user_id}` - MFA/known IP identified user
- `_fingerprint_{user_id}` - Legacy marker (deprecated)
- **Bug fix**: Corrected marker parsing split indices
  - `_identified_user_6` → split('_')[3] = '6' ✓ (was [2] = 'user' ✗)
  - `_stay_134` → split('_')[2] = '134' ✓

**9. Banner Improvements**:
- ASCII-only banners (removed Unicode emoji that didn't render)
- MFA banner sent via MSG_USERAUTH_BANNER (works even on auth failure)
- Personalized denial messages: "Dear Paweł Mojski, you don't have access..."
- Better error messages: "Access denied after MFA: {reason}" (not "MFA timeout")

**Benefits Achieved**:
- ✅ SSH key users: Zero config, fingerprint persistence, single MFA per Stay
- ✅ Password users: Full MFA support, no SSH keys required
- ✅ Laptop users: Agent forwarding with password fallback when keys rejected
- ✅ Network switches: keyboard-interactive auth works (when MFA not required)
- ✅ Per-server MFA: Sensitive servers can enforce MFA even with active Stay
- ✅ Secure identification: fingerprint/IP/MFA only (never SSH username)
- ✅ Stay fingerprint upgrade: password → key arrives → fingerprint added
- ✅ Clean audit trail: ssh_key_fingerprint + identification_method in logs

**Testing Results** (January 28, 2026):
- ✅ Password-only auth (no SSH key) → MFA → connected
- ✅ SSH key + agent forwarding, backend rejects → password prompt → connected
- ✅ Network switch (keyboard-interactive) → connected (no MFA)
- ✅ First connection with key → MFA → Stay created with fingerprint
- ✅ Second connection (same key) → no MFA (fingerprint match)
- ✅ Password-only second session → MFA → joins existing Stay
- ✅ Server with policy.mfa_required=True → MFA enforced despite Stay
- ✅ Server with policy.mfa_required=False → fingerprint bypass works

**Production Deployment**:
- Tower (10.0.160.5): Flask restarted with marker parsing fix
- Gate tailscale-etop (10.210.0.76): v1.11.1-tproxy deployed
- Gate tailscale-ideo (10.30.0.76): v1.11.1-tproxy deployed (new gate)
- Database: New gate added, Stay #134 active (p.mojski, fingerprint-based)

**Code Locations**:
- Stay schema: src/core/database.py lines 481-520
- Fingerprint extraction: src/proxy/ssh_proxy.py line 514
- Password auth with MFA: src/proxy/ssh_proxy.py lines 456-620
- Keyboard-interactive handling: src/proxy/ssh_proxy.py lines 823-860
- Password fallback: src/proxy/ssh_proxy.py lines 2825-2860
- User identification: src/api/grants.py lines 178-235
- Per-server MFA: src/api/grants.py lines 391-425
- Marker parsing: src/core/access_control_v2.py lines 240-290
- Stay creation: src/api/stays.py lines 55-140

### v1.11.2 - Exec Commands Exit Status Fix 🎯 ✅ COMPLETED (February 18, 2026)

**Problem**: SSH exec commands (e.g., `ssh user@host w`) didn't return output to client
- Client received "Connection closed by remote host" without seeing command output
- Issue: Backend closed channel immediately after sending output (fast commands like `w`, `uptime`)
- By the time `forward_channel()` was called (~300 lines later), backend channel was already closed
- Exit status propagation failed because channel was closed before reading it

**Root Cause Analysis**:
```python
# OLD FLOW (BROKEN):
backend_channel.exec_command('w')
# ... 300 lines of code ...
# - Session creation API call (~50-200ms)
# - Recording setup
# - Monitoring threads
# Backend already closed by now!
forward_channel(client_channel, backend_channel)  # Too late!
```

**Solution**: Immediate output reading for exec commands
- Read backend output **immediately** after `exec_command()`
- Forward each chunk to client in real-time
- Capture exit status before channel closes
- Skip `forward_channel()` for exec commands (output already forwarded)

**Implementation** (February 18, 2026):

**1. Immediate Output Reading** (src/proxy/ssh_proxy.py lines 2989-3033):
```python
backend_channel.exec_command(cmd_str)

# Read output immediately before backend closes channel
exec_output = b''
backend_channel.settimeout(5.0)

while True:
    chunk = backend_channel.recv(4096)
    if len(chunk) == 0:
        break
    exec_output += chunk
    channel.send(chunk)  # Forward to client immediately

# Get exit status
time.sleep(0.05)
if backend_channel.exit_status_ready():
    exit_status = backend_channel.recv_exit_status()
    channel.send_exit_status(exit_status)

# Mark output as read - skip forward_channel
server_handler.exec_output_read = True
```

**2. Skip forward_channel for Exec** (src/proxy/ssh_proxy.py lines 3327-3333):
```python
if hasattr(server_handler, 'exec_output_read') and server_handler.exec_output_read:
    logger.info(f"Skipping forward_channel for exec command (output already read)")
else:
    self.forward_channel(channel, backend_channel, recorder, ...)
```

**Benefits Achieved**:
- ✅ Exec commands return output correctly: `ssh user@host w` shows who is logged in
- ✅ Exit status propagated properly (0 = success, non-zero = error)
- ✅ Works for all exec commands: `w`, `uptime`, `ps`, `ls`, etc.
- ✅ No timeout waiting for closed channel
- ✅ Client sees output instantly (real-time forwarding)

**Testing Results** (February 18, 2026):
```bash
root@vm-lin1:~# ssh -A 10.30.14.3 -lpmojski w
 13:47:00 up 94 days,  2:59,  2 users,  load average: 0,00, 0,02, 0,01
UŻYTK.  TTY      Z                ZAL.OD   BEZCZ. JCPU   PCPU CO
pmojski  pts/10   100.64.0.39      10:37   21:00   0.04s  0.04s -bash
pmojski  pts/1    10.30.0.76       13:46    7.00s  0.02s  0.02s -bash
Connection to 10.30.14.3 closed by remote host.
# ✅ Output visible!
```

**Production Deployment**:
- Gate tailscale-ideo (10.30.0.76): v1.11.2-tproxy deployed
- Gate tailscale-etop (10.210.0.76): v1.11.2-tproxy deployed
- Both gates tested and working correctly

**Code Locations**:
- Immediate exec output reading: src/proxy/ssh_proxy.py lines 2989-3033
- Skip forward_channel logic: src/proxy/ssh_proxy.py lines 3327-3333

### v1.12.0 - Auto-Grant & Permission System 🎯 ✅ COMPLETED (February 18, 2026)

**Problem**: Opening Inside to external users requires:
- Auto-grant creation to avoid admin support overhead for every new connection
- Per-gate configuration (different rules per gate/environment)
- Permission levels to control GUI access (prevent auto-created users from accessing admin panel)
- Auto-user creation from SAML (zero-touch onboarding)
- Revoke mechanism to permanently block specific users

**Goal**: 
1. Automatically create configurable grants when no matching policy exists
2. Per-gate auto-grant settings (enable/disable, duration, timeout, port forwarding)
3. Permission system for GUI access control
4. Auto-create users from SAML authentication with restricted permissions

**Requirements**:
- ✅ **Per-gate configuration**: Admin can customize auto-grant behavior per gate in Web UI
- ✅ Auto-grant defaults: 7 days duration, 60min timeout, port forwarding enabled
- ✅ SSH login: Empty (allow any SSH login, no restrictions)
- ✅ No IP whitelisting (if user reached jumphost, they're trusted)
- ✅ **Permission levels**: 0=SuperAdmin, 100=Admin, 500=Operator, 1000=User (no GUI)
- ✅ **Auto-user creation**: Extract username from SAML email, create with permission_level=1000
- ✅ **Revoke mechanism**: Check for expired grants before creating auto-grant
  - If expired grant exists for (user_id, server_id) → **PERMDEN** (no auto-grant)
  - Admin can revoke by setting end_time in past (existing mechanism)

**Solution**: Auto-grant creation in AccessControlEngineV2

**Implementation** (February 18, 2026):

**1. Database Migration 011** (migrations/011_auto_grant_config_and_permissions.sql):

**Gates table** - Per-gate auto-grant configuration:
```sql
ALTER TABLE gates ADD COLUMN auto_grant_enabled BOOLEAN DEFAULT TRUE NOT NULL;
ALTER TABLE gates ADD COLUMN auto_grant_duration_days INTEGER DEFAULT 7 NOT NULL;
ALTER TABLE gates ADD COLUMN auto_grant_inactivity_timeout_minutes INTEGER DEFAULT 60 NOT NULL;
ALTER TABLE gates ADD COLUMN auto_grant_port_forwarding BOOLEAN DEFAULT TRUE NOT NULL;
CREATE INDEX idx_gates_auto_grant_enabled ON gates(auto_grant_enabled);
```

**Users table** - Permission level system:
```sql
ALTER TABLE users ADD COLUMN permission_level INTEGER DEFAULT 1000 NOT NULL;
CREATE INDEX idx_users_permission_level ON users(permission_level);
-- Update existing admin user to super admin
UPDATE users SET permission_level = 0 WHERE username = 'admin' OR email LIKE '%admin%';
```

**Permission levels**:
- 0 = Super Admin (full access to all features)
- 100 = Admin (manage users, policies, gates)
- 500 = Operator (view-only, manage active sessions)
- 1000 = User (no GUI access, only proxy connections)

**Reference view**:
```sql
CREATE VIEW permission_levels AS
SELECT 0 AS level, 'Super Admin' AS name, 'Full system access' AS description
UNION ALL SELECT 100, 'Admin', 'Manage users and policies'
UNION ALL SELECT 500, 'Operator', 'View and manage sessions'
UNION ALL SELECT 1000, 'User', 'Proxy access only (no GUI)';
```

**2. Permission System** (src/web/permissions.py - NEW FILE):

```python
def check_permission(user, min_level=100):
    """Check if user has required permission level"""
    if not user or not user.is_active:
        return False
    return user.permission_level <= min_level

def permission_required(min_level=100):
    """Decorator: Require minimum permission level"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if not check_permission(current_user, min_level):
                abort(403)  # Forbidden
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Convenience decorators:
admin_required = permission_required(100)  # Admin or Super Admin
super_admin_required = permission_required(0)  # Super Admin only
operator_required = permission_required(500)  # Operator, Admin, or Super Admin
```

**Applied to routes**:
- Gates: add, edit, delete, maintenance → `@admin_required`
- Users: add, edit, delete → `@admin_required`
- Policies: add, edit, delete → `@admin_required`
- Dashboard: view → `@operator_required`

**3. Auto-grant creation with gate configuration** (src/core/access_control_v2.py):

```python
def _create_auto_grant(self, db, user, server, protocol, now, source_ip, gate_id):
    """Create automatic grant with gate-specific configuration"""
    
    # Load gate configuration
    gate = db.query(Gate).filter(Gate.id == gate_id).first()
    if not gate:
        logger.error(f"Gate {gate_id} not found, cannot create auto-grant")
        return None
    
    # Check if auto-grant disabled for this gate
    if not gate.auto_grant_enabled:
        logger.info(f"Auto-grant disabled for gate {gate.name}, denying access")
        return None
    
    # Use gate-specific configuration
    duration_days = gate.auto_grant_duration_days or 7
    timeout_minutes = gate.auto_grant_inactivity_timeout_minutes or 60
    port_forwarding = gate.auto_grant_port_forwarding if gate.auto_grant_port_forwarding is not None else True
    
    auto_grant = AccessPolicy(
        user_id=user.id,
        scope_type='server',
        target_server_id=server.id,
        protocol=protocol,
        port_forwarding_allowed=port_forwarding,
        inactivity_timeout_minutes=timeout_minutes,
        start_time=now,
        end_time=now + timedelta(days=duration_days),
        mfa_required=False,
        use_schedules=False,
        is_active=True,
        granted_by='AUTO-GRANT',
        reason=f'Auto-grant from gate {gate.name} ({duration_days}d validity)'
    )
    # No PolicySSHLogin records = allow all SSH logins
    db.add(auto_grant)
    db.commit()
    
    logger.info(f"AUTO-GRANT created for {user.username} → {server.name} "
                f"via gate {gate.name} (valid {duration_days} days)")
    return auto_grant
```

**4. Revoke check before auto-grant** (src/core/access_control_v2.py):

```python
# In check_access_v2(), when no matching policies found:

# Step 1: Check if access was REVOKED (expired grant exists)
revoked_grant = db.query(AccessPolicy).filter(
    AccessPolicy.user_id == user.id,
    AccessPolicy.target_server_id == server.id,
    AccessPolicy.end_time < now,  # Expired = revoked
    AccessPolicy.is_active == True,
    AccessPolicy.granted_by == 'AUTO-GRANT'  # Only check auto-grants
).first()

if revoked_grant:
    logger.warning(f"Access revoked for {user.username} → {server.name}")
    return {
        'has_access': False,
        'denial_reason': 'access_revoked',
        'reason': 'Access to server was revoked by administrator'
    }

# Step 2: No revoke - create auto-grant (with gate config)
auto_grant = self._create_auto_grant(db, user, server, protocol, now, source_ip, gate_id)

# Step 3: Handle auto-grant disabled
if auto_grant is None:
    logger.info(f"Auto-grant disabled or failed for {user.username} → {server.name}")
    return {
        'has_access': False,
        'denial_reason': 'auto_grant_disabled',
        'reason': 'No matching policy and auto-grant is disabled for this gate'
    }

# Continue with normal flow (schedule check, SSH login check)
matching_policies = [auto_grant]
```

**5. SAML Auto-User Creation** (src/web/auth_saml.py):

```python
# After SAML authentication, when user email not found:
user = db.query(User).filter(User.email == saml_email).first()

if not user:
    # AUTO-CREATE new user from SAML
    logger.info(f"Auto-creating user from SAML email: {saml_email}")
    
    # Extract username from email (before @)
    username = saml_email.split('@')[0]
    
    # Check for username collision
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        # Use full email as username if collision
        username = saml_email.replace('@', '_at_').replace('.', '_')
        logger.warning(f"Username collision, using: {username}")
    
    # Create user with restricted permissions
    user = User(
        username=username,
        email=saml_email,
        full_name=saml_attributes.get('displayName', username),
        permission_level=1000,  # No GUI access by default
        is_active=True,
        created_at=datetime.utcnow()
    )
    db.add(user)
    db.commit()
    
    # Log auto-creation to audit trail
    audit_log = AuditLog(
        user_id=user.id,
        action='auto_user_create',
        target_type='user',
        target_id=user.id,
        description=f'User auto-created from SAML: {saml_email}',
        source_ip=request.remote_addr,
        timestamp=datetime.utcnow()
    )
    db.add(audit_log)
    db.commit()
    
    logger.info(f"User {username} (ID {user.id}) auto-created, permission_level=1000")

# Continue with MFA flow...
```

**6. Web UI - Gate Configuration** (src/web/templates/gates/edit.html, add.html):

Added "Auto-Grant Configuration" section to gate forms:
- **Enable Auto-Grant** - Checkbox toggle (default: enabled)
- **Grant Duration** - Number input (1-365 days, default: 7)
- **Inactivity Timeout** - Number input (0-1440 minutes, default: 60)
  - 0 = No timeout (session never expires from inactivity)
  - 1-1440 = Timeout in minutes
- **Port Forwarding** - Checkbox (default: enabled)

Form includes help text:
- "Auto-grant creates access policies automatically when user connects without existing grant"
- "Useful for trusted environments where users need quick access"
- "Security: Only enable for gates where all authenticated users are trusted"

Badge "New in v1.12.0" highlights new feature

**7. Backend - Gate Management** (src/web/blueprints/gates.py):

Protected routes with permission decorators:
```python
from src.web.permissions import admin_required

@gates_bp.route('/add', methods=['GET', 'POST'])
@login_required
@admin_required  # Requires permission_level ≤ 100
def add_gate():
    # ... gate creation logic ...
    
@gates_bp.route('/<int:gate_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_gate(gate_id):
    if request.method == 'POST':
        # ... existing validation ...
        
        # Parse auto-grant configuration from form
        gate.auto_grant_enabled = 'auto_grant_enabled' in request.form
        
        duration_days = request.form.get('auto_grant_duration_days', '7')
        gate.auto_grant_duration_days = max(1, min(365, int(duration_days)))
        
        timeout_mins = request.form.get('auto_grant_inactivity_timeout_minutes', '60')
        gate.auto_grant_inactivity_timeout_minutes = max(0, min(1440, int(timeout_mins)))
        
        gate.auto_grant_port_forwarding = 'auto_grant_port_forwarding' in request.form
        
        db.commit()
        flash(f'Gate {gate.name} updated successfully', 'success')
        return redirect(url_for('gates.list_gates'))
```

**8. User Cleanup Script** (scripts/cleanup_user_p_mojski_v2.sh):

Created script for complete user deletion with transaction safety:
- Deletes MFA challenges, group memberships, source IPs
- Deletes maintenance access, sessions, stays, access policies
- Preserves audit logs (sets user_id=NULL for compliance)
- Uses PostgreSQL transaction (ROLLBACK on error)
- Peer authentication with `sudo -u postgres`

**Tested on production**: Successfully deleted p.mojski account:
- 110 MFA challenges deleted
- 299 sessions deleted
- 145 stays deleted
- 19 access policies deleted
- 31 audit logs preserved (user_id=NULL)
- User record deleted

---

**Auto-grant Properties** (per-gate configurable):
- **Validity**: 1-365 days (default: 7 days)
- **Inactivity timeout**: 0-1440 minutes (default: 60, 0=no timeout)
- **Port forwarding**: Enabled/disabled (default: enabled)
- **SSH logins**: No restrictions (empty PolicySSHLogin list = allow all)
- **Schedules**: No restrictions (use_schedules=False)
- **MFA**: Not required (user already authenticated)
- **Scope**: Server-level (specific user → specific server)
- **Granted by**: 'AUTO-GRANT' (system marker for auditing)

**Revoke Workflow**:
1. Admin opens user's grant in web UI
2. Clicks "Revoke" → Sets end_time to current time (makes grant expired)
3. Active sessions killed by heartbeat mechanism (existing)
4. User reconnects → Auto-grant logic checks for revoked grant
5. If found → PERMDEN, no new auto-grant created
6. User permanently blocked from that server until admin creates new grant

**Flow Diagram**:
```
User connects → Gate → /api/v1/auth/check → check_access_v2() →
  1. Find user by source_ip
  2. Find server by destination_ip
  3. Check user policies → empty
  4. Check group policies → empty
  5. Check revoked grants (expired ACCESS_POLICY for user+server+AUTO-GRANT)
     → If found: DENY (access_revoked)
     → If not found: Load gate configuration
  6. Create auto-grant with gate config (if auto_grant_enabled=true)
     → Duration: gate.auto_grant_duration_days
     → Timeout: gate.auto_grant_inactivity_timeout_minutes
     → Port forwarding: gate.auto_grant_port_forwarding
  7. Continue with schedule check, SSH login validation
  8. Return has_access=True with auto-grant as selected_policy
Gate ← YES/NO + policy_id + timeout
```

**Benefits**:
- ✅ Zero admin intervention for new connections
- ✅ Per-gate customization (dev gates: 1 day, prod gates: 30 days)
- ✅ Gradual rollout (disable for sensitive gates, enable for dev/test)
- ✅ Auto-user creation from SAML (zero-touch onboarding)
- ✅ Permission system prevents auto-users from accessing admin panel
- ✅ Admin can revoke specific users permanently (sets end_time to past)
- ✅ Revoke check prevents auto-grant after admin denial
- ✅ Audit trail (AUTO-GRANT marker, auto_user_create events)
- ✅ Works with existing MFA flow

**Testing Scenarios**:
```bash
# Scenario 1: New user connecting to known server (no grant, auto-grant enabled)
ssh user@10.30.14.5 -l test_user
# Expected: Auto-grant created with gate config, connection succeeds

# Scenario 2: Auto-grant disabled for gate
# Web UI: Gates → Edit gate → Uncheck "Enable Auto-Grant"
# User reconnects without grant:
ssh user@10.30.14.5 -l test_user
# Expected: PERMDEN (auto_grant_disabled), no grant created

# Scenario 3: Admin revokes user access
# Web UI: Policies → Find user's grant → Revoke (sets end_time = now)
# Active sessions killed by heartbeat
# User reconnects:
ssh user@10.30.14.5 -l test_user
# Expected: PERMDEN (access_revoked), no auto-grant created

# Scenario 4: Existing group policy
# User has group policy for server group
ssh user@10.30.14.5 -l test_user
# Expected: Uses existing group policy, no auto-grant created

# Scenario 5: Auto-user creation via SAML
# New email authenticates: john.doe@company.com
# Expected: 
#   - User created with username 'john_doe' (or 'john' if no collision)
#   - permission_level=1000 (no GUI access)
#   - Audit log entry: action='auto_user_create'
#   - MFA challenge shown
#   - After MFA: auto-grant created, connection succeeds

# Scenario 6: Permission system - auto-user tries GUI
# User created via SAML (permission_level=1000) tries to access Web UI
# Expected: Login succeeds but dashboard redirects to "Access Denied" (403)

# Scenario 7: Gate config customization
# Web UI: Gates → Edit gate
#   - Duration: 1 day (short-lived access for test gate)
#   - Timeout: 30 minutes (aggressive timeout for security)
#   - Port forwarding: Disabled (restrict tunneling)
# User connects:
# Expected: Auto-grant created with 1d validity, 30min timeout, no port forwarding
```

**Deployment** (February 18, 2026):

**1. Database Backup**:
```bash
sudo -u postgres pg_dump jumphost_db > backup_before_v1.12.0_$(date +%Y%m%d_%H%M%S).sql
# Created: backup_before_v1.12.0_20260218_143003.sql (262KB)
```

**2. Apply Migration**:
```bash
sudo -u postgres psql jumphost_db < migrations/011_auto_grant_config_and_permissions.sql
# Result:
#   ALTER TABLE (gates - 4 columns added)
#   CREATE INDEX (idx_gates_auto_grant_enabled)
#   ALTER TABLE (users - permission_level added)
#   CREATE INDEX (idx_users_permission_level)
#   UPDATE 1 (admin user → permission_level=0)
#   CREATE VIEW (permission_levels)
```

**3. Verify Schema**:
```bash
sudo -u postgres psql jumphost_db -c "\d gates" | grep auto_grant
# auto_grant_enabled | boolean | not null | true
# auto_grant_duration_days | integer | not null | 7
# auto_grant_inactivity_timeout_minutes | integer | not null | 60
# auto_grant_port_forwarding | boolean | not null | true

sudo -u postgres psql jumphost_db -c "\d users" | grep permission_level
# permission_level | integer | not null | 1000
```

**4. Restart Tower Service**:
```bash
systemctl restart jumphost-flask
systemctl status jumphost-flask
# Active: active (running) ✓
```

**5. Test Cleanup Script** (production test):
```bash
bash scripts/cleanup_user_p_mojski_v2.sh
# Result: SUCCESS
#   - 110 MFA challenges deleted
#   - 299 sessions deleted
#   - 145 stays deleted
#   - 19 access policies deleted
#   - 31 audit logs preserved (user_id=NULL)
#   - User p.mojski deleted
```

**Deployment Status**:
- ✅ Tower v1.12.0: DEPLOYED (jumphost-flask restarted)
- ✅ Gates: NO CHANGES (use existing API v1)
- ✅ Database: Migration 011 APPLIED
- ✅ Backup: Created (262KB)
- ✅ Cleanup script: TESTED and WORKING

**Code Locations**:
- Migration: `/opt/jumphost/migrations/011_auto_grant_config_and_permissions.sql`
- Permission system: `/opt/jumphost/src/web/permissions.py` (NEW)
- Auto-grant logic: `/opt/jumphost/src/core/access_control_v2.py` `_create_auto_grant()`, `check_access_v2()`
- SAML auto-user: `/opt/jumphost/src/web/auth_saml.py` (lines ~194-250)
- Gate backend: `/opt/jumphost/src/web/blueprints/gates.py` (with @admin_required)
- Gate forms: `/opt/jumphost/src/web/templates/gates/edit.html`, `add.html`
- Cleanup script: `/opt/jumphost/scripts/cleanup_user_p_mojski_v2.sh`
- Design docs: `/opt/jumphost/scripts/AUTO_REGISTRATION_DESIGN.md`, `DEPLOYMENT_v1.12.0.md`

---

### v1.12 - Auto-Registration & Auto-Grant Groups 🎯 FUTURE

**Concept**: Special user groups for automatic backend management

**Feature 1: Auto Register Backend Group**
- Users in "Auto Register Backend" group can automatically register new servers
- When user connects to unknown backend (IP/hostname):
  - System automatically creates Server entry in database
  - No manual admin intervention required
  - Server details extracted from connection (IP, protocol, port)
  - Optional: Prompt user for server name/description
- Use cases:
  - Dev environments with dynamic servers
  - Cloud environments with auto-scaling
  - Trusted power users who manage their own infrastructure

**Feature 2: Auto Grant Backend Group**
- Users in "Auto Grant Backend" group automatically receive grants to new backends
- When new Server is registered in system:
  - Automatically create AccessPolicy for users in this group
  - Grant with configurable defaults (duration, schedules, permissions)
  - Optional: Per-group grant templates (dev group → 8h grants, ops group → permanent)
- Use cases:
  - Ops team needs access to all infrastructure
  - Dev team needs access to all dev servers
  - Reduce admin workload for grant creation

**Implementation Notes**:
- Group model: Add `auto_register_backends` and `auto_grant_backends` boolean flags
- Registration hook: In `check_access()` before denial, check group membership
- Grant hook: In Server creation, query groups with auto_grant flag
- Audit: Log auto-registrations and auto-grants for security tracking
- Limits: Optional max backends per user, rate limiting
- UI: Checkboxes in group edit form for these special permissions

**Security Considerations**:
- Auto-registration could be abused (DOS with fake servers)
- Consider approval workflow or notification to admins
- Auto-grants should respect existing schedules and restrictions
- Audit trail essential for compliance

### v1.13 - Proactive Connection Validation (TCP Handshake Proxy) 🎯 ADVANCED

**Concept**: Intercept SYN packets and validate backend availability BEFORE completing client handshake

**Current Behavior**:
1. Client → SYN → Jumphost
2. Jumphost → SYN-ACK → Client (accepts connection immediately)
3. Jumphost → SYN → Backend
4. If backend down → client sees "connection refused" or timeout AFTER handshake

**Proposed Behavior**:
1. Client → SYN → Jumphost
2. Jumphost → SYN → Backend (test backend first, hold client SYN)
3. If Backend → SYN-ACK → Jumphost:
   - Jumphost → SYN-ACK → Client (complete handshake)
   - Connection established normally
4. If Backend → ICMP Unreachable:
   - Jumphost → ICMP Unreachable → Client (mimic backend response)
   - Client immediately knows port is closed
5. If Backend → Timeout:
   - Jumphost → RST or timeout → Client
   - Clean failure without hanging connection

**Benefits**:
- Monitoring tools get accurate port status without SSH authentication
- Clients see immediate failure instead of post-handshake errors
- Better user experience (no "connected but can't reach backend" confusion)
- Health checks work at TCP level (no application layer needed)

**Implementation Challenges**:
- **Kernel-level TCP stack intervention required**
- Cannot be done in pure Python (operates above TCP layer)
- Possible approaches:
  1. **netfilter/NFQUEUE** (C extension or nfqueue-bindings):
     - Intercept packets at PREROUTING
     - Hold SYN in userspace queue
     - Test backend connection
     - Inject SYN-ACK or ICMP based on result
  2. **Raw sockets + iptables** (complex):
     - Drop incoming SYN with iptables
     - Capture with raw socket
     - Manually craft and send response packets
  3. **eBPF/XDP** (modern, high-performance):
     - Kernel-level packet filtering
     - C programs loaded into kernel
     - Can modify/drop packets before TCP stack
  4. **Kernel module** (most control, most complex):
     - Custom netfilter hook
     - Full control over TCP handshake
     - Maintenance burden

**Feasibility**:
- ⚠️ **NOT feasible in pure Python** (requires kernel-level packet manipulation)
- Possible with C extension + Python bindings
- High complexity, requires deep TCP/IP and Linux networking knowledge
- Maintenance risk (kernel API changes, security issues)

**Recommendation**:
- Consider as long-term goal (v2.0+)
- Research eBPF/XDP as modern approach
- Prototype with nfqueue-bindings first
- May require dedicated networking engineer
- Alternative: Keep current behavior, improve error messages

**Related Issue - Backend Validation During Authentication**:
- ⚠️ **Current problem**: User authenticates with SSH key/password, jumphost accepts it, THEN tries to connect to backend
- If backend is down/unreachable → user sees "Authentication succeeded" but connection hangs/fails
- Bad UX: User authenticated but gets stuck at "Opening channel" or similar
- **Proposed solution** (easier than TCP proxy):
  1. Add backend connectivity check DURING authentication (between auth_publickey and channel_open)
  2. Quick TCP connect test to backend:port with short timeout (2-5 seconds)
  3. If backend unreachable → fail authentication with clear message: "Backend server unreachable"
  4. If backend responds → proceed with normal authentication flow
- **Benefits**:
  - User gets immediate feedback if backend is down
  - No "authenticated but hanging" state
  - Can be implemented in pure Python (SSH server auth hook)
  - Much simpler than TCP handshake proxy
- **Implementation**: 
  - Hook in `check_auth_publickey()` / `check_auth_password()` after policy check
  - Use `socket.connect_ex()` with timeout to backend IP:port
  - Return `paramiko.AUTH_FAILED` with custom banner if unreachable
- **Priority**: Medium (improves UX significantly with low complexity)

### v1.9 - Distributed Architecture & JSONL Streaming (Q1 2026) 🔄 IN PROGRESS

**Status**: 90% complete - JSONL recording format migration in progress

**GUI Improvements:**
- ✅ Gate/Stay columns added to sessions list
- ✅ Gate/Stay info in session detail view
- ✅ Recording viewer: Dual-format support (JSON + JSONL)
- ✅ **Maintenance Mode v2**: Complete redesign with grace periods and personnel access 🎯 NEW
  - Dedicated `in_maintenance` field (separate from `is_active`)
  - Absolute time scheduling with grace period (minutes before maintenance)
  - Grace period blocks new logins, scheduled time disconnects existing sessions
  - Personnel whitelist (explicit user IDs, no groups)
  - API endpoints: POST/DELETE for gates and backends (servers)
  - GUI modal: DateTime picker with "Now" button, grace slider (5-60 min), personnel multi-select
  - AJAX auto-refresh without closing modal
  - Display: Maintenance status badges, "Until" time, Exit Maintenance button
  - Backend: Session termination marking with `termination_reason='gate_maintenance'`
- ✅ **Timezone Consistency**: Europe/Warsaw throughout GUI 🎯 NEW
  - Template filters: `|localtime`, `|time_only`, `|time_short` for proper UTC→Warsaw conversion
  - JavaScript datetime-local inputs: Use local time (not UTC)
  - Dashboard: All session times in Warsaw timezone
  - Database: Stores UTC (naive datetime), converts on display
  - Filter handles naive UTC → Warsaw conversion with pytz
- ⏳ Dashboard tuning (better metrics, cleaner layout)
- ⏳ Refactor host/group/user pages (better UX, consistent navigation)

**Distributed Jumphost Service - Tower API:**
- ✅ REST API layer (15 endpoints)
- ✅ POST /api/v1/auth/check - AccessControlV2 authorization with gate_id
- ✅ POST /api/v1/sessions/create - Session tracking with gate_id + automatic Stay management
- ✅ PATCH /api/v1/sessions/<id> - Session updates + automatic Stay closure when last session ends
- ✅ POST /api/v1/stays/start - Person entry tracking (legacy, deprecated by automatic Stay in /sessions)
- ✅ POST /api/v1/gates/heartbeat - Gate alive monitoring
- ✅ Database schema: gates, stays tables with relationships
- ✅ IP Pool per Gate: gate_id in ip_allocations table
- ✅ Gate-specific IP resolution: AccessControlV2 with gate_id parameter
- ✅ Web UI: Gates CRUD with IP pool configuration (network CIDR, start IP, end IP)
- ✅ Stay Logic Implementation: Per-person tracking (not per-server, not per-policy)
- ✅ **Maintenance Mode v2**: POST/DELETE /api/v1/gates/<id>/maintenance and /backends/<id>/maintenance 🎯 NEW
- ✅ **Maintenance Access Control**: Grace period blocking in AccessControlV2.check_access_v2() 🎯 NEW
- ✅ **SSH Proxy Cleanup**: Closes stale sessions AND stays on startup (service_restart) 🎯 NEW
- ⏳ Gate registration & management UI improvements
- ⏳ Policy scoping (all gates vs specific gate)
- ⏳ Dashboard: Active Stays widget with real-time person presence

**Stay Logic - Person-Centric Tracking:**
- ✅ **Stay** = period when person is "inside" (has ≥1 active session)
- ✅ **First session** of person → creates Stay (started_at, is_active=True)
- ✅ **Additional sessions** → reuse existing Stay (stay_id shared across sessions)
- ✅ **Last session ends** → closes Stay (ended_at, duration_seconds, is_active=False)
- ✅ One person can have multiple sessions in one Stay (different servers, different SSH usernames)
- ✅ Stay spans across reconnects (disconnect/reconnect keeps same Stay if sessions overlap)
- ✅ Fully automatic - no changes needed in Gate/proxy code

**Stay Examples:**
```
Person: p.mojski
08:00 - Connects: root@server1 → Session #1, Stay #1 opened
09:30 - Connects: shared@server2 → Session #2, Stay #1 reused
10:00 - Disconnects from server1 → Session #1 ended, Stay #1 still active (Session #2 running)
14:14 - Disconnects from server2 → Session #2 ended, Stay #1 closed (last session)

Result: Stay #1 duration = 08:00-14:14 (6h 14min)
```

**IP Pool Architecture:**
- ✅ Each Gate has its own IP pool (10.0.160.128-255)
- ✅ IP pools CAN overlap between gates (same IP range allowed)
- ✅ IP unique only within one gate, not globally
- ✅ Database: `ip_allocations.gate_id` foreign key to gates
- ✅ Unique constraint: `(allocated_ip, gate_id)` not just `(allocated_ip)`
- ✅ IPPoolManager: Gate-aware allocation with `gate_id` parameter
- ✅ AccessControlV2: `find_backend_by_proxy_ip(dest_ip, gate_id)` 
- ✅ Tower API: Passes `gate.id` to access control checks

**Example Multi-Gate Scenario:**
```
Gate-1 (localhost):    10.0.160.129 → Server A (Test-SSH)
Gate-2 (cloud-dmz):    10.0.160.129 → Server X (Prod-DB)

# Same IP, different backends - resolution by gate_id
find_backend_by_proxy_ip(db, '10.0.160.129', gate_id=1) → Server A
find_backend_by_proxy_ip(db, '10.0.160.129', gate_id=2) → Server X
```

**Recording Streaming - JSONL Format:**
- ✅ Tower API: 3 recording endpoints (start/chunk/finalize)
- ✅ JSONL format specification (JSON Lines, one event per line)
- 🔄 SSHSessionRecorder: Converting to JSONL streaming
- 🔄 Web parser: Dual-format support (legacy JSON + new JSONL)
- ✅ Streaming architecture: 256KB buffer, 3s flush, <5s latency
- ✅ Offline mode: /tmp/ buffer + auto-upload when Tower returns
- ✅ Base64 chunked upload (binary-safe over JSON API)
- ⏳ End-to-end testing with real SSH connections

**JSONL Recording Format:**
```jsonl
{"type":"session_start","timestamp":"2026-01-07T12:00:00.000Z","username":"p.mojski","server":"10.0.160.4"}
{"type":"client","timestamp":"2026-01-07T12:00:01.123Z","data":"ls -la\n"}
{"type":"server","timestamp":"2026-01-07T12:00:01.245Z","data":"total 24\ndrwxr-xr-x..."}
{"type":"session_end","timestamp":"2026-01-07T12:05:30.456Z","duration":330}
```

**Event Types:**
- `session_start`: Session metadata (username, server, timestamp)
- `client`: Data from client → server (user input)
- `server`: Data from server → client (command output)
- `session_end`: Session completion (duration, timestamp)

**Benefits:**
- ✅ Append-only streaming (no JSON parsing overhead)
- ✅ Real-time upload during session (not after end)
- ✅ Streaming parser (no need to load full file)
- ✅ Event-level timestamps and direction tracking
- ✅ Industry standard format (Kafka, ELK compatible)

**Next Steps:**
- [ ] Complete SSHSessionRecorder JSONL migration
- [ ] Test Web UI with JSONL recordings
- [ ] Gate heartbeat daemon implementation
- [ ] Gate cache (SQLite) for offline mode
- [ ] Multi-gate deployment testing

**TPROXY Support:**
- ✅ Transparent proxy mode for Linux routers
- ✅ SO_ORIGINAL_DST extraction (preserve dst_ip:dst_port)
- ✅ Server lookup by IP (no hostname needed) - dual fallback in find_backend_by_proxy_ip
- ✅ Dual mode support (NAT + TPROXY simultaneously)
- ✅ Configuration file: /opt/jumphost/config/ssh_proxy.conf
- ✅ NAT listener: 0.0.0.0:22 (traditional jumphost)
- ✅ TPROXY listener: 0.0.0.0:8022 (transparent mode)
- ⏳ iptables TPROXY rules documentation
- ⏳ Testing with real TPROXY traffic
- Perfect for Tailscale exit nodes & VPN concentrators
- Zero-config for end users (ssh target-server just works)

### v2.0 - CLI & Management Tools (Q1 2026) 🎯

**curl-based CLI:**
- `jumphost grant create --user p.mojski --server prod-01 --duration 2h`
- `jumphost sessions list --active --protocol ssh`
- `jumphost policy list --expired`
- `jumphost server add --name srv-01 --ip 10.0.1.50`
- Token-based authentication
- JSON output support
- Bash completion
- Man pages

### v2.1 - HTTP/HTTPS Proxy (Future) 💡

**HTTP Proxy dla starych urządzeń sieciowych:**
- Mini Squid-like proxy dla GUI-only devices (old switches, routers, appliances)
- HTTP/HTTPS proxy z policy-based access control
- HTTPS MITM (SSL intercept) dla pełnej kontroli dostępu
- Per-user/per-device access policies
- Session recording (HTTP request/response logs)
- Use case: Stare switche/routery bez CLI, tylko web GUI
- Perfect for: Legacy network infrastructure management

## Project Vision

**Inside: Control who can be inside your infrastructure, when, and for how long.**

Core principles:
- ✅ **Person ≠ username** - Identity is a person, not a system account (DONE)
- ✅ **Grant-based access** - Time-limited permissions, not permanent roles (DONE)
- ✅ **Stay-centric** - Track who is inside, not just connections (DONE)
- ✅ **Entry points** - Multiple ways to get inside: SSH, RDP, HTTP (SSH/RDP DONE)
- ✅ **Full audit** - Every entry, every stay, every session recorded (DONE)
- ⏳ **Distributed** - Tower (control) + Gates (data planes) (v1.9 - IN PROGRESS)
- ✅ **TPROXY** - Transparent proxy mode (v1.9 - IMPLEMENTED) 🎯 NEW
  - Dual-mode support: NAT (port 22) + TPROXY (port 8022)
  - SO_ORIGINAL_DST extraction from socket
  - find_backend_by_proxy_ip(): Automatic fallback NAT pool → real IP
  - IP_TRANSPARENT socket option enabled
  - Configuration: /opt/jumphost/config/ssh_proxy.conf
  - Ready for iptables TPROXY rules and Tailscale integration
- ⏳ **CLI tools** - curl-based management (v2.0 - PLANNED)
- ⏳ **HTTP/HTTPS proxy** - Legacy devices web GUIs (v2.1 - PLANNED)

## Architecture Goal

```
Person (100.64.0.X)
    ↓
    Entry: ssh target-server (SSH :22) or mstsc target-server (RDP :3389)
    ↓
Inside Gateway extracts:
    - Source IP: 100.64.0.X (identifies person)
    - Target: target-server (identifies backend server)
    ↓
Grant Check:
    - Person has valid grant to target?
    - Grant allows protocol (ssh/rdp)?
    - Grant allows this server?
    - Grant allows this SSH username?
    - Grant time window active?
    ↓
If approved:
    - Create or join stay (person is now inside)
    - Create session within stay (TCP connection)
    - Proxy to backend server
    - Record everything (terminal log / RDP video)
    ↓
Backend Server:
    - SSH: 10.30.0.200:22
    - RDP: 10.30.0.140:3389
    ↓
Stay tracked in database:
    - Person: "Paweł Mojski"
    - Grant: #123 (prod-db, 8h)
    - Sessions: [session-001, session-002]
    - Recordings: [term-001.log, rdp-001.mp4]
    - Record: Immutable audit entry
```

---

## ✅ COMPLETED: v1.1 - Session Monitoring & Live View (January 2026)

### 🎯 Major Features Delivered

#### 1. Session History & Live View System
- **Session List**: `/sessions/` with filtering by protocol, status, user, server
- **Session Detail**: Full metadata display with 14 fields
- **Live SSH Viewer**: Real-time log streaming with 2-second polling
- **Terminal UI**: Dark theme with color-coded events, search, client/server filters
- **Recording Format**: JSONL (JSON Lines) for streaming writes
- **Performance**: LRU cache (maxsize=100) for session parser optimization
- **Download**: Support for SSH .log and RDP .pyrdp files

#### 2. Dashboard Auto-Refresh
- **Active Sessions Table**: Auto-updates every 5 seconds via AJAX
- **Statistics Cards**: Today's connections, denied, success rate
- **API Endpoints**: `/api/stats`, `/api/active-sessions`
- **Recent Sessions Widget**: Shows last 10 closed sessions with Started/Duration/Ended
- **Tooltips**: European date format (dd-mm-yyyy hh:mm:ss) on all "ago" timestamps

#### 3. Systemd Service Integration
- **jumphost-flask.service**: Flask web app (port 5000, user: p.mojski)
- **jumphost-ssh-proxy.service**: SSH proxy (port 22, user: root)
- **jumphost-rdp-proxy.service**: PyRDP MITM direct (port 3389, user: root)
- **Centralized Logs**: `/var/log/jumphost/{flask,ssh_proxy,rdp_mitm}.log`
- **Logrotate**: Daily rotation, 14-30 days retention
- **Auto-Restart**: All services configured with `Restart=always`

#### 4. Architecture Simplification
- **RDP**: Direct PyRDP MITM on 0.0.0.0:3389 (systemd service: rdp-proxy)
- **Logs**: Unified structure in /var/log/jumphost/
- **Service Management**: Full systemd integration with enable/disable/restart

#### 5. Live Recording System
- **SSH**: JSONL format - writes each event immediately to disk
- **Performance**: File opened in append mode, flushed after each write
- **Compatibility**: Parser handles both JSONL (streaming) and old JSON format
- **Live View**: Browser polls `/sessions/<id>/live?after=<timestamp>` every 2s
- **Cache Invalidation**: LRU cache uses (file_path, mtime) as key

### 📁 New Files Created
- `/opt/jumphost/src/web/blueprints/sessions.py` - Session history & live view blueprint
- `/opt/jumphost/src/web/templates/sessions/index.html` - Session list with filters
- `/opt/jumphost/src/web/templates/sessions/view.html` - Session detail + live viewer
- `/etc/systemd/system/jumphost-flask.service` - Flask systemd service
- `/etc/systemd/system/jumphost-ssh-proxy.service` - SSH proxy systemd service
- `/etc/systemd/system/jumphost-rdp-proxy.service` - RDP proxy systemd service
- `/etc/logrotate.d/jumphost` - Log rotation configuration

### 🗑️ Deprecated/Removed
- `src/proxy/rdp_guard.py` - **REMOVED** (direct PyRDP MITM via systemd)
- `src/proxy/rdp_proxy.py` - **REMOVED** (direct PyRDP MITM via systemd)
- `src/proxy/rdp_wrapper.sh` - Still used for systemd startup

### 📊 Testing Results
- **Dashboard Refresh**: ✅ 5-second auto-update working
- **Live SSH View**: ✅ 2-second polling with new events
- **Session History**: ✅ Filtering by protocol/status/user/server
- **Recording Download**: ✅ SSH .log and RDP .pyrdp files
- **Systemd Services**: ✅ All 3 services running with auto-restart
- **Performance**: ✅ LRU cache eliminates repeated parsing

### 🐛 Issues Fixed
- Fixed API endpoint returning dict instead of Session objects
- Fixed dashboard auto-refresh selector (added #activeSessionsBody ID)
- Fixed Recent Sessions missing "Started" column
- Added tooltips with dd-mm-yyyy format to all timestamps
- Fixed JSONL recording to write immediately (not at session end)
- Fixed Flask becoming slow (added caching)

---

## ✅ COMPLETED: v1.8 - Mega-Wyszukiwarka (January 2026)

### 🎯 Goals Delivered

#### 1. Universal Search System 🎯
**Problem**: Brak centralnego miejsca do wyszukiwania sesji/polityk/użytkowników/serwerów.
**Solution**: Mega-wyszukiwarka z 11+ filtrami dynamicznymi i smart search detection.

**Features**:
- **Smart Search**: Auto-detektuje IP (`10.0.1.5`), policy ID (`#42`, `policy:42`), protokół (`ssh`, `rdp`), username
- **Filtry**: user_id, user_group_id, server_id, server_group_id, protocol, policy_id, connection_status, denial_reason, source_ip, has_port_forwarding, is_active, time_from/to, min/max_duration, scope_type, forwarding_type
- **Zakładki**: Sesje, Polityki (Port Forwards usunięty - pokazywany jako atrybut sesji)
- **Quick Filters**: Active/Closed, Denied/Granted, With/Without Port Forwarding
- **Advanced Filters**: 12 dropdowns + time/duration inputs (collapsible)
- **Auto-Refresh**: Co 2 sekundy z wizualnym wskaźnikiem (spinning icon)
- **Pagination**: 50 wyników/strona z manual query string building
- **CSV Export**: Dla sesji i polityk z property headers (max 10K wierszy)
- **Klikalne wiersze**: Cała sesja to link do session details
- **Port Forwarding Column**: Ikona `<i class="fas fa-exchange-alt"></i>` + licznik w tabeli sesji

**Routes**:
- `GET /search/` - Main search page with dynamic filters
- `GET /search/export` - CSV export for active tab

**Smart Search Examples**:
```
10.0.1.5          → Szuka w source_ip, Server.ip_address
#42               → Policy ID 42
policy:15         → Policy ID 15
ssh               → Protocol filter
rdp               → Protocol filter
username          → Szuka w User.username, Server.name
las.init1.pl      → Generic text search (wszystkie pola)
```

#### 2. Denied Sessions Logging 🎯
**Problem**: Sesje denied (brak polityki, out of window) nie były logowane do bazy.
**Solution**: SSH proxy loguje denied sessions w `check_auth_none()` i `check_auth_password()`.

**DBSession Fields**:
- `connection_status='denied'`
- `denial_reason` - machine codes: `outside_schedule`, `no_matching_policy`, `policy_expired`, `wrong_source_ip`, etc.
- `denial_details` - human-readable explanation
- `policy_id` - tracks which policy denied/granted access
- `started_at=ended_at` - immediate denial
- `is_active=False`

**Example Denied Session**:
```python
denied_session = DBSession(
    session_id=str(uuid.uuid4()),
    user_id=user.id if user else None,
    server_id=server.id if server else None,
    connection_status='denied',
    denial_reason='outside_schedule',
    denial_details='Access denied: Current time not in schedule',
    policy_id=policy.id if policy else None,
    started_at=datetime.utcnow(),
    ended_at=datetime.utcnow(),
    is_active=False
)
```

#### 3. Enhanced Session Details 🎯
**Problem**: Session view nie pokazywał dlaczego sesja była denied.
**Solution**: Dodano denial_reason, denial_details, connection_status badges.

**Status Badges**:
- `denied` → `<span class="badge bg-danger"><i class="bi bi-x-circle"></i> Connection Denied</span>`
- `active` → `<span class="badge bg-success"><i class="fas fa-circle"></i> Aktywna</span>`
- `closed` → `<span class="badge bg-secondary"><i class="far fa-circle"></i> Zamknięta</span>`

**Denial Info**:
- Reason: `<span class="badge bg-warning text-dark">{{ denial_reason }}</span>`
- Details: `<small class="text-muted">{{ denial_details }}</small>`
- Protocol Version: `<code>SSH-2.0-OpenSSH_9.2p1</code>`

#### 4. Database Schema Enhancements 🎯
**New Relationship**:
```python
# Session model
transfers = relationship("SessionTransfer", back_populates="session")

# SessionTransfer model
session = relationship("Session", back_populates="transfers")
```

**Benefits**:
- Eager loading: `query.options(joinedload(DBSession.transfers))`
- Template access: `{% set pf_count = session.transfers|selectattr('transfer_type', 'in', ['port_forward_local', ...])|list|length %}`
- Eliminuje subqueries w każdym wierszu tabeli

#### 5. UI/UX Improvements 🎯
- **Usunięto zbędne kolumny**: ID, Akcje (niepotrzebne, tylko szum)
- **Klikalne wiersze**: `<tr onclick="window.location.href='...'">` - cała sesja to link
- **Port Forwarding jako atrybut**: Kolumna w tabeli sesji zamiast osobnej zakładki (logiczne)
- **Auto-refresh indicator**: `<i class="fas fa-sync-alt fa-spin"> Auto-refresh aktywny (co 2s)`
- **outerjoin**: Obsługa denied sessions bez pełnych danych user/server

### 📁 New Files Created
- `/opt/jumphost/src/web/search.py` (605 lines) - Search blueprint z query builderami
- `/opt/jumphost/src/web/templates/search/index.html` (637 lines) - Search UI z JavaScript

### 🗑️ Removed
- Port Forwards tab - usunięty (port forwarding pokazywany jako kolumna w Sesjach)

### 📊 Testing Results
- ✅ Smart search detection dla IP/policy_id/protocol/username/text
- ✅ Wszystkie 11+ filtrów działają poprawnie
- ✅ Auto-refresh co 2s z fetch() API
- ✅ CSV export dla sesji i polityk (max 10K rows)
- ✅ Denied sessions logowane poprawnie (check_auth_none + check_auth_password)
- ✅ Port forwarding count wyświetla się jako ikona + licznik
- ✅ Klikalne wiersze sesji (onclick navigation)
- ✅ outerjoin dla User/Server (obsługa denied sessions)

### 🐛 Issues Fixed
- **Import errors**: PortForwarding → SessionTransfer, user_group_membership → UserGroupMember, get_session → SessionLocal
- **Schema mismatches**: Server.hostname → Server.name, Server.address → Server.ip_address, AccessPolicy.target_server_group → AccessPolicy.target_group, AccessPolicy.description → AccessPolicy.reason
- **Endpoint names**: sessions.session_detail → sessions.view, policies.view_policy → policies.edit
- **URL parameter duplication**: `url_for('search.search', tab=tab, **request.args)` → manual query string building
- **Policy status check**: `policy.end_time > request.args.get('_now', '2026-01-06')|datetime` → simplified datetime comparison
- **Missing relationship**: Session.transfers <-> SessionTransfer.session (back_populates added)

### 🎨 Code Quality
- **Query builders**: 3 separate functions (sessions, policies, port_forwards) - clean separation
- **Smart detection**: `smart_detect_search_term()` - auto-detects search type
- **Recursive groups**: `get_users_in_group()`, `get_servers_in_group()` - BFS traversal
- **Manual pagination**: Query string building bez parameter duplication
- **Auto-refresh**: JavaScript fetch() z error handling i visual indicator

---

## ✅ COMPLETED: v1.5 - UX Improvements & Access Control (January 2026)

### 🎯 Goals Delivered

#### 1. Immediate Rejection for No Grant 🎯
**Problem**: Users without grants were prompted for password 3 times before disconnection.
**Solution**: 
- Pre-auth grant checking in `check_auth_none()` (called before password prompt)
- Early access check in `SSHProxyHandler.__init__()` for banner preparation
- Friendly ASCII banner displayed immediately:
  ```
  +====================================================================+
  |                          ACCESS DENIED                             |
  +====================================================================+
  
    Dear user,
  
    There is no active access grant for your IP address:
      100.64.0.20
  
    Reason: No matching access policy
  
    Please contact your administrator to request access.
  
    Have a nice day!
  ```
- Returns only "publickey" auth method (no password prompt)
- User sees banner and immediate "Permission denied (publickey)" - no password attempts

**Technical Details**:
- `get_banner()` returns tuple `(message, "en-US")` per paramiko ServerInterface
- `check_auth_none()` checks access via `check_access_v2()` before auth negotiation
- `get_allowed_auths()` returns `"publickey"` only when no grant (prevents password prompt)
- Banner sent during SSH protocol negotiation (before authentication)

**Files Changed**:
- `src/proxy/ssh_proxy.py`: Added `check_auth_none()`, modified `get_banner()`, `get_allowed_auths()`

#### 2. Flexible Duration Parser 🎯
**Problem**: Grant duration limited to max 59 minutes, required separate hours/minutes fields.
**Solution**: Human-readable duration parser with single text field

**Supported Formats**:
- **Simple**: `30m`, `2h`, `5d`, `1w`, `1M`, `1y`
- **Decimal**: `1.5h` (90 min), `2.5d` (60 hours)
- **Combined**: `1h30m`, `2d12h`, `1w3d`, `1y6M`
- **Readable**: `30min`, `2hours`, `5days`
- **Special**: `0`, `permanent`

**Examples**:
```
30m       → 30 minutes
2h        → 120 minutes (2 hours)
1.5h      → 90 minutes
1d        → 1440 minutes (24 hours)
1w        → 10080 minutes (7 days)
1M        → 43200 minutes (30 days)
1h30m     → 90 minutes
2d12h30m  → 3630 minutes (2 days 12 hours 30 min)
1y6M      → 784800 minutes (1.5 years)
permanent → 0 (no expiry)
```

**Technical Details**:
- Parser: `src/core/duration_parser.py`
- Functions: `parse_duration(str) → int`, `format_duration(int) → str`
- Regex pattern: `(\d+(?:\.\d+)?)\s*([a-zA-Z]+)`
- Special handling for 'M' (month) vs 'm' (minute): converts `1M` → `1mo` before lowercasing
- Unit conversions: y=525600, M=43200, w=10080, d=1440, h=60, m=1

**Files Changed**:
- `src/core/duration_parser.py`: New module
- `src/web/blueprints/policies.py`: Import parser, use `parse_duration()`
- `src/web/templates/policies/add.html`: Single text field instead of two number inputs

#### 3. Scheduled Grants (Future Start Time) 🎯
**Problem**: Grants could only start immediately or at specific end time.
**Solution**: Absolute time mode with both start_time and end_time

**Features**:
- **Duration Mode**: Relative time (e.g., `2h`, `1d`) - starts now
- **Absolute Mode**: Specific start AND end dates/times
- **Scheduled Badge**: Future grants shown with blue "Scheduled" badge in policy list
- **Active Grants Filter**: Changed to show non-expired grants (not just currently active)
  - Old: `start_time <= now AND end_time > now`
  - New: `end_time > now OR end_time IS NULL`
  - Result: Scheduled grants visible in Active Grants list

**UI Improvements**:
- Dropdown selector (Duration/Absolute) instead of 3 radio buttons
- Removed "Permanent" button - use `0` or `permanent` in Duration field
- Absolute mode shows two datetime-local fields:
  - Start Date/Time (optional - defaults to now)
  - End Date/Time (required)

**Technical Details**:
- `absolute_start_time` form field for scheduled grants
- Backend parses `absolute_start_time` if provided, otherwise uses `utcnow()`
- Policy query filter updated to include future grants
- Template already had "Scheduled" badge logic: `policy.start_time > now`

**Files Changed**:
- `src/web/blueprints/policies.py`: Parse `absolute_start_time`, update query filter
- `src/web/templates/policies/add.html`: Dropdown selector, dual datetime fields for absolute mode

#### 4. SCP/SFTP Transfer Logging 🎯
**Problem**: SCP/SFTP sessions recorded binary data to transcripts.
**Solution**: 
- Disable session recording for SCP/SFTP (no binary data in transcripts)
- Track transfers in `session_transfers` table with byte counts
- Modern `scp` uses SFTP subsystem - detected and logged as `sftp_session`

**Technical Details**:
- Detection: Check `subsystem == 'sftp'` or `exec_command` contains `scp`
- Transfer logging: `log_sftp_transfer()` creates record, `update_transfer_stats()` adds byte counts
- Database constraint: Added `'sftp_session'` to `check_transfer_type_valid`
- No recorder for file transfers: `recorder = None` when `should_record = False`

**Files Changed**:
- `src/proxy/ssh_proxy.py`: Moved recorder creation after channel type detection, added SFTP logging
- `src/core/database.py`: Added `sftp_session` to CHECK constraint

### 📊 Summary Statistics

**Features Delivered**: 4 major improvements
**Lines Changed**: ~300 lines across 5 files
**New Modules**: 1 (`duration_parser.py`)
**User Experience**: Dramatically improved (no password prompts, flexible durations, scheduled grants)
**Code Quality**: Cleaner, more maintainable (single duration field, early rejection pattern)

---

## ✅ COMPLETED: v1.7 - Policy Audit Trail & Edit System (January 2026)

### 🎯 Goal: Comprehensive Policy Change Tracking & Easy Schedule Editing

**Challenge Solved**: Policies with 50+ schedules required full revoke/recreate to add one window. No audit trail of who changed what. Dashboard showed confusing "Recent Activity" (audit logs). Schedule tooltips missing.

### ✅ Delivered Features

#### 1. Database Schema - policy_audit_log Table
- **Table**: `policy_audit_log` with CASCADE delete on parent policy
- **Columns**:
  - `policy_id` (INTEGER FK) - Which policy was changed
  - `changed_by_user_id` (INTEGER FK) - Who made the change (admin user ID)
  - `change_type` (VARCHAR 50) - 'policy_updated', 'created', 'revoked', 'renewed'
  - `field_name` (TEXT) - Specific field changed (NULL for full updates)
  - `old_value`, `new_value` (TEXT) - Field-level changes
  - `full_old_state` (JSONB) - Complete policy snapshot before
  - `full_new_state` (JSONB) - Complete policy snapshot after
  - `changed_at` (TIMESTAMP, default NOW())
- **Indexes**: policy_id, changed_at, change_type for fast queries
- **Migration**: Manual SQL execution after granting permissions to jumphost_user
- **JSONB Snapshots**: Stores complete policy state including schedules, SSH logins, times

#### 2. Policy Creator Tracking - created_by_user_id
- **Column**: `access_policies.created_by_user_id` (INTEGER FK to users.id)
- **Purpose**: Track who created each policy (different from user_id = beneficiary)
- **Nullable**: Allows NULL for system-created policies
- **Relationships**: 
  - User.policies_created - policies this admin created
  - User.access_policies - policies granted TO this user
- **SQLAlchemy Fix**: Added explicit foreign_keys to resolve ambiguity:
  ```python
  User.access_policies = relationship(..., foreign_keys="[AccessPolicy.user_id]")
  User.policies_created = relationship(..., foreign_keys="[AccessPolicy.created_by_user_id]")
  AccessPolicy.user = relationship(..., foreign_keys=[user_id])
  AccessPolicy.created_by = relationship(..., foreign_keys=[created_by_user_id])
  ```
- **Existing Data**: Set to admin user (ID=7) for all existing policies

#### 3. Security Hardening - DELETE Endpoints Removed
- **Policies**: DELETE endpoint removed from `/policies/` blueprint
  - Old: DELETE button → immediate policy deletion
  - New: Only Revoke (set end_time=NOW) or Renew (extend end_time)
  - Comment: "policies cannot be deleted, only revoked"
- **Sessions**: Session records preserved (MP4 cache deletion still allowed)
- **Audit Trail**: Immutable history in policy_audit_log (CASCADE delete only when admin removes policy)
- **UI Changes**: Delete button removed from policies/index.html

#### 4. Dashboard Cleanup - Recent Activity Removed
- **Removed**: "Recent Activity" widget showing audit_logs
- **Reason**: Confusing for users, not relevant for daily operations
- **Kept**: "Recent Sessions" widget (last 10 closed sessions with duration)
- **Files Modified**:
  - `templates/dashboard/index.html` - lines 303-345 removed
  - `blueprints/dashboard.py` - recent_logs query removed

#### 5. Schedule Display in Policy List
- **Helper Function**: `format_policy_schedules_summary(policy)` returns (summary, tooltip)
- **Display Logic**:
  - 1 schedule: Full description ("Mon-Fri 08:00-16:00")
  - Multiple: First + count ("Mon-Fri 8-16 (+2 more)")
  - Disabled: "Schedule disabled" badge
  - No rules: "No rules defined"
- **Tooltip**: Bootstrap tooltip with HTML rendering showing all schedules line-by-line
- **UI Components**:
  - Badge with calendar icon in policy list table
  - data-bs-toggle="tooltip" with formatted HTML
  - JavaScript initialization on page load
- **Files Modified**:
  - `blueprints/policies.py` - lines 13-74 (helper function)
  - `templates/policies/index.html` - lines 133-143 (badge), 199-207 (JS)

#### 6. Policy Edit Endpoint - Full Schedule Management
- **Endpoint**: GET `/policies/<id>/edit`
  - Loads policy with all relationships (schedules, ssh_logins, groups)
  - Converts schedules to JSON for JavaScript
  - Pre-populates form with current values
  - Read-only fields: user/group, server/group (cannot change target)
- **Endpoint**: POST `/policies/<id>/edit`
  - Captures old_state as JSONB snapshot (all fields + schedules)
  - Updates editable fields: SSH logins, port_forwarding, start/end time
  - Schedule management:
    - Keeps existing schedule IDs for updates
    - Adds new schedules (no ID = insert)
    - Deletes removed schedules (not in updated list)
  - Captures new_state as JSONB snapshot after changes
  - Creates PolicyAuditLog entry with change_type='policy_updated'
  - Logs changed_by_user_id (current Flask user)
- **Template**: `templates/policies/edit.html`
  - Based on add.html structure
  - Pre-filled form fields
  - Schedule list with Edit/Delete buttons per schedule
  - JavaScript: editSchedule(index) - load schedule into form
  - JavaScript: saveSchedule() - add or update (keeps ID)
  - JavaScript: removeSchedule(index) - delete from array
  - Cancel Edit button to reset form
  - Status badge (Active/Inactive) per schedule

#### 7. Edit Button in Policy List
- **Location**: `templates/policies/index.html` actions column
- **Button**: Primary styled "Edit" button before Renew
- **Icon**: bi-pencil (Bootstrap Icons)
- **Link**: `/policies/<id>/edit`

### 📊 Use Cases Supported

**Edit Schedule Without Revoke**:
```
Before: Policy with 50 schedules → Need to add 1 window
Old way: Revoke entire policy → Create new → Re-enter all 50 schedules
New way: Edit → Add 1 schedule → Save (50 existing kept, 1 new added)

Benefit: Save 10+ minutes of re-entry work
```

**Audit Trail for Compliance**:
```
Scenario: Policy changed from 30 days to 60 days
Question: Who extended access and when?

Query policy_audit_log:
- changed_by_user_id: 7 (admin@example.com)
- changed_at: 2026-01-06 17:30:00
- full_old_state: {"end_time": "2026-02-05T23:59:00"}
- full_new_state: {"end_time": "2026-03-07T23:59:00"}
```

**Schedule Modification History**:
```
Policy #42 schedule changes:
1. Created with Mon-Fri 8-16 (by admin, 2026-01-01)
2. Added Sat 2-6 (+1 schedule, by admin, 2026-01-05)
3. Changed Mon-Fri to 9-17 (edited schedule ID=100, by admin, 2026-01-06)

All changes logged with JSONB snapshots in policy_audit_log
```

**Schedule Visibility in List**:
```
Policy list shows:
- Policy #42: [📅 Mon-Fri 08:00-16:00 (+2 more)]
- Hover tooltip shows:
  Business Hours: Mon-Fri 08:00-16:00
  Weekend Maintenance: Sat-Sun 02:00-06:00
  Monthly Backup: First day of month 04:00-08:00
```

### 📁 Files Modified/Created

**Database**:
- Manual SQL: ALTER TABLE access_policies ADD created_by_user_id
- Manual SQL: CREATE TABLE policy_audit_log with JSONB columns
- Manual SQL: Indexes on policy_id, changed_at, change_type
- Manual SQL: UPDATE existing policies SET created_by_user_id = 7 (admin)
- Manual SQL: GRANT ALL on policy_audit_log to jumphost_user

**Backend Models**:
- `src/core/database.py`:
  - Line 273: AccessPolicy.created_by_user_id column
  - Lines 275-283: Both relationships with explicit foreign_keys
  - Lines 32-38: User relationships (access_policies + policies_created)
  - Lines 351-372: PolicyAuditLog model (JSONB fields)

**Backend Blueprint**:
- `src/web/blueprints/policies.py`:
  - Lines 13-74: format_policy_schedules_summary() helper
  - Line 107: Pass format_schedules to template
  - Lines 76-260: edit() endpoint (GET + POST with audit logging)
  - Lines 255-257: DELETE endpoint removed (replaced with comment)

**Frontend Templates**:
- `src/web/templates/policies/edit.html` (NEW, 489 lines):
  - Pre-populated form with read-only grant details
  - Schedule list with Edit/Delete buttons
  - JavaScript for schedule management (add/edit/remove)
  - Bootstrap tooltips for schedule display
- `src/web/templates/policies/index.html`:
  - Line 77: Schedule column in table header
  - Lines 133-143: Schedule badge with tooltip
  - Lines 166-168: Edit button before Renew
  - Lines 175: DELETE button removed (comment)
  - Lines 199-207: JavaScript for tooltip initialization
- `src/web/templates/dashboard/index.html`:
  - Lines 303-345: Recent Activity section removed

**Migration Files**:
- `alembic/versions/9a1b2c3d4e5f_add_policy_audit_trail.py` (NEW):
  - Migration file structure (not executed via alembic)
  - Manual SQL used instead for faster deployment

### 🧪 Testing Results

**Policy Edit**:
- ✅ Load existing policy with 3 schedules → Form pre-populated
- ✅ Edit schedule #1 (Mon-Fri 8-16 → 9-17) → ID preserved
- ✅ Add new schedule (Sat 2-6) → New record created
- ✅ Delete schedule #3 → Removed from database
- ✅ Audit log created with full JSONB snapshots (before/after)

**SQLAlchemy Relationships**:
- ✅ User.access_policies (5 policies) → Works
- ✅ User.policies_created (0 policies) → Works
- ✅ No foreign key ambiguity errors
- ✅ Both relationships query correctly

**Schedule Display**:
- ✅ Single schedule: "Mon-Fri 08:00-16:00"
- ✅ Multiple schedules: "Mon-Fri 8-16 (+2 more)"
- ✅ Tooltip shows all schedules line-by-line
- ✅ Bootstrap tooltips initialize on page load
- ✅ HTML rendering in tooltips works (<br> tags)

**Security**:
- ✅ DELETE button removed from UI
- ✅ DELETE endpoint returns 404
- ✅ Only Revoke (end_time=NOW) and Renew (extend end_time) available
- ✅ Audit trail preserved (immutable history)

**Dashboard**:
- ✅ Recent Activity widget removed
- ✅ Recent Sessions widget still present
- ✅ No errors in Flask logs
- ✅ Auto-refresh still works (5s interval)

### 🐛 Issues Fixed

1. **SQLAlchemy Foreign Key Ambiguity**
   - Error: "Could not determine join condition between parent/child tables"
   - Root cause: AccessPolicy has 2 FKs to User (user_id, created_by_user_id)
   - Fix: Explicit foreign_keys in all 4 relationships (User + AccessPolicy)
   - Test: Both relationships work independently

2. **Policy Deletion Security**
   - Issue: Policies could be permanently deleted, losing audit trail
   - Fix: Remove DELETE endpoint, only allow Revoke (soft delete via end_time)
   - Result: Full history preserved in policy_audit_log

3. **Schedule Visibility**
   - Issue: Policy list showed only "(3 rules)" without descriptions
   - Fix: format_policy_schedules_summary() with tooltip
   - Result: Users see schedule windows at a glance

### 📈 Impact

**Time Savings**:
- Editing 1 schedule in 50-rule policy: ~10 minutes saved (no revoke/recreate)
- Audit trail queries: Instant compliance reports (JSONB queries)

**Data Integrity**:
- All policy changes logged with full state snapshots
- Immutable audit trail (CASCADE delete only)
- created_by_user_id tracks policy ownership

**User Experience**:
- Edit button in policy list (easier discovery)
- Schedule tooltips in list view (no need to open policy)
- No DELETE confusion (only Revoke/Renew)
- Cleaner dashboard (Recent Sessions only)

---

## ✅ COMPLETED: v1.6 - Schedule-Based Access Control (January 2026)

### 🎯 Goal: Recurring Time-Based Access Control

**Challenge Solved**: Policies could only have absolute start/end times. Needed support for recurring patterns like "business hours Mon-Fri 8-16" or "first Monday of month 04:00-08:00".

### ✅ Delivered Features

#### 1. Database Schema - policy_schedules Table
- **Table**: `policy_schedules` with CASCADE delete on parent policy
- **Columns**:
  - `weekdays` (INTEGER[]) - 0=Monday, 6=Sunday, NULL=all days
  - `time_start`, `time_end` (TIME) - Daily time window, NULL=00:00/23:59
  - `months` (INTEGER[]) - 1-12, NULL=all months
  - `days_of_month` (INTEGER[]) - 1-31, NULL=all days
  - `timezone` (VARCHAR 50) - pytz timezone string (default 'Europe/Warsaw')
  - `is_active` (BOOLEAN) - Enable/disable rule
- **Relationship**: `access_policies.use_schedules` (BOOLEAN) flag enables feature
- **Migration**: Manual SQL execution after killing 4 blocking sessions

#### 2. Schedule Checker Module (src/core/schedule_checker.py)
- **matches_schedule(schedule_rule, check_time)** → bool
  - Converts UTC to policy timezone using pytz
  - Checks weekday (0-6), time range, month (1-12), day of month (1-31)
  - Supports midnight-crossing ranges (e.g., 22:00-02:00 overnight shifts)
  - Returns True if all conditions match
- **check_policy_schedules(schedules, check_time)** → (bool, str)
  - OR logic: If ANY schedule matches, return (True, schedule_name)
  - No schedules: (True, None) - disabled
  - None match: (False, None)
- **format_schedule_description(schedule)** → str
  - Human-readable: "Mon-Fri 08:00-16:00", "Weekends only", "First day of month"
- **get_schedule_window_end(schedule_rule, check_time)** → datetime
  - Returns when current window closes (e.g., today at 16:00 UTC)
  - Returns None if not in valid window
- **get_earliest_schedule_end(schedules, check_time)** → datetime
  - Returns earliest end among all active schedules
  - Used for effective_end_time calculation

#### 3. Access Control Integration (Step 3.5)
- **Location**: `src/core/access_control_v2.py` in `check_access_v2()`
- **Step 3.5**: Schedule filtering after basic policy matching
  - For each matching policy: `check_schedule_access(db, policy, check_time)`
  - Queries PolicySchedule table, converts to dict format
  - Calls `check_policy_schedules()` from schedule_checker module
  - Filters out policies where schedule doesn't match
  - Returns "Outside allowed time windows" if all filtered out
- **Timing**: Executes AFTER basic policy matching, BEFORE SSH login check
- **Testing Parameter**: Added `check_time` parameter to check_access_v2() for unit testing

#### 4. Smart Effective End Time Calculation
- **Problem**: User has policy valid until Jan 31, schedule ends at 16:00 today
- **Old Behavior**: Warning "access expires in 25 days" (misleading)
- **New Behavior**: Warning "access expires in 5 minutes" (schedule closing)
- **Implementation**:
  ```python
  effective_end_time = min(policy.end_time, schedule_window_end)
  ```
- **Integration**: 
  - SSH proxy stores `access_result` in server_handler
  - Uses `effective_end_time` for grant expiry monitoring
  - Fallback to `policy.end_time` if no schedule
- **Result Dict**: `check_access_v2()` returns `effective_end_time` field

#### 5. Web GUI - Schedule Builder
- **Location**: `src/web/templates/policies/add.html` Section 6
- **Components**:
  - Checkbox to enable `use_schedules`
  - Weekday checkboxes (Mon-Sun)
  - Time range pickers (HH:MM 24h format)
  - Month checkboxes (Jan-Dec)
  - Days of month input (comma-separated: "1,15" or ranges: "1-7")
  - Timezone selector (Europe/Warsaw, UTC, US/Eastern, etc.)
  - "Add Schedule" button (multiple schedules per policy)
- **JavaScript Functions**:
  - `addSchedule()` - Collects form data, pushes to array
  - `removeSchedule(index)` - Deletes schedule from array
  - `formatScheduleDescription()` - "Mon-Fri 08:00-16:00" format
  - `parseCommaSeparatedInts()` - Handles "1,15" or "1-7" ranges
  - Form submit: Adds `schedules_json` hidden field

#### 6. Backend Policy Creation
- **Location**: `src/web/blueprints/policies.py`
- **Logic** (lines 152-188):
  ```python
  use_schedules = request.form.get('use_schedules') == 'on'
  if use_schedules:
      policy.use_schedules = True
      schedules_json = request.form.get('schedules_json')
      schedules = json.loads(schedules_json)
      for schedule_data in schedules:
          schedule = PolicySchedule(
              policy_id=policy.id,
              weekdays=schedule_data.get('weekdays'),
              time_start=datetime.strptime(schedule_data['time_start'], '%H:%M').time(),
              time_end=datetime.strptime(schedule_data['time_end'], '%H:%M').time(),
              # ... months, days_of_month, timezone
          )
          db.add(schedule)
  ```

### 📊 Use Cases Supported

**Business Hours**:
```
Policy: start=Jan 1, end=Jan 31, use_schedules=True
Schedule: Mon-Fri 08:00-16:00 Europe/Warsaw

Result: Access granted only during work hours on weekdays
Warning: "Access expires in 5 minutes" at 15:55 (schedule closing)
Tomorrow: Can reconnect at 08:00 (new window opens)
```

**Weekend Maintenance**:
```
Schedule: Sat-Sun 00:00-23:59
Result: Access only on weekends, denied Mon-Fri
```

**Monthly Backups**:
```
Schedule: days_of_month=[1], time=04:00-08:00
Result: Access only on first day of month, 4-8 AM
```

**Seasonal Access**:
```
Schedule: months=[5,6,7,8], weekdays=[0,1,2,3,4]
Result: Access May-August, only on weekdays
```

**Overnight Shifts**:
```
Schedule: time_start=22:00, time_end=02:00
Result: 22:00-02:00 window (crosses midnight correctly)
```

### 📁 Files Modified

**Backend**:
- `src/core/schedule_checker.py` (265 lines, NEW)
- `src/core/access_control_v2.py` - Added Step 3.5, effective_end_time calculation
- `src/core/database.py` - PolicySchedule model, cascade delete fix
- `src/proxy/ssh_proxy.py` - Store access_result, use effective_end_time

**Frontend**:
- `src/web/templates/policies/add.html` - Section 6: Schedule builder UI
- `src/web/blueprints/policies.py` - Parse schedules_json, create PolicySchedule records

**Database**:
- `alembic/versions/8f3c9a2e1d5b_add_policy_schedules.py` - Migration (executed via SQL)
- Manual SQL: CREATE TABLE, indexes, permissions, ALTER TABLE

**Integration**:
- RDP proxy: Uses check_access_v2() via modified PyRDP MITM
- SSH proxy: Uses check_access_v2() with ssh_login parameter
- Both proxies: Schedule-aware access control operational

### 🧪 Testing Results

**Test Scenario**: Mon-Fri 8-16 business hours
- ✅ Monday 10:00: ALLOWED (in window)
- ✅ Monday 18:00: DENIED (outside 8-16)
- ✅ Saturday 10:00: DENIED (weekend)
- ✅ Effective end time: Returns 16:00 today, not policy end (Jan 31)

**Test Scenario**: Policy ends before schedule
- ✅ Policy ends at 14:00, schedule at 16:00
- ✅ Effective end time: 14:00 (policy ends first)
- ✅ Warning: "Access expires in 4 hours" (policy), not "6 hours" (schedule)

**Backward Compatibility**:
- ✅ Policies with `use_schedules=False`: Work unchanged
- ✅ Existing policies: No schedules = disabled, normal behavior
- ✅ Legacy access control: Unaffected by schedule system

**Policy Priority**:
- ✅ OR logic: If ANY policy allows access, it's granted
- ✅ Multiple schedules: If ANY schedule matches, policy active
- ✅ Schedule disabled: Policy operates with start_time/end_time only

### 🐛 Issues Fixed

1. **Database Migration Blocked**: 4 active sessions killed via `pg_terminate_backend()`
2. **Cascade Delete Error**: Fixed relationship from `backref` to `back_populates` with `cascade="all, delete-orphan"`
3. **Timezone Complexity**: Implemented pytz conversion in matches_schedule()
4. **Midnight Crossing**: Overnight ranges like 22:00-02:00 work correctly
5. **Misleading Warnings**: Smart effective_end_time calculation provides accurate expiry time

### 📝 Technical Notes

**Architecture Decisions**:
- **Recurring Rules**: Cron-like but more flexible (month/day combinations)
- **OR Logic**: Multiple schedules with ANY matching = allow
- **Timezone Storage**: Per-schedule timezone string, pytz for conversion
- **Lazy Evaluation**: use_schedules flag enables/disables feature per policy
- **Hierarchical Time**: start_time/end_time = outer envelope, schedules = inner windows
- **Smart Expiry**: min(policy end, schedule end) for accurate warnings

**Performance Considerations**:
- Query optimization: PolicySchedule filtered by policy_id and is_active
- Timezone conversion: Cached pytz timezone objects
- Schedule evaluation: Early return on first match (OR logic)
- No caching: Real-time evaluation ensures accuracy

**Policy Hierarchy Clarification**:
```
policy.start_time ─────────────────────────────────────────────────── policy.end_time
                    ▲                                   ▲
                    │                                   │
                schedule window 1: Mon-Fri 8-16        │
                    │                                   │
                schedule window 2: Sat 10-12           │
                                                        │
                                             effective_end_time
```

### 🎯 Success Criteria - ALL MET ✅

- ✅ Support recurring time patterns (weekdays, hours, months, days)
- ✅ Multiple schedules per policy with OR logic
- ✅ Timezone-aware scheduling with pytz
- ✅ Midnight-crossing time ranges (overnight shifts)
- ✅ Web GUI for schedule creation
- ✅ Integration with SSH and RDP proxies
- ✅ Smart effective_end_time for accurate warnings
- ✅ Backward compatibility (use_schedules flag)
- ✅ Cascade delete when policy removed
- ✅ Testing validation (all scenarios passed)

---

## ✅ COMPLETED: v1.4 - SSH Port Forwarding & Policy Enhancements (January 2026)

### 🎯 Goal: Complete SSH Port Forwarding Support (-L, -R, -D)

**Challenge Solved**: SSH port forwarding through proxy requires special handling because:
1. **-L (Local forward)**: Standard `direct-tcpip` channels work naturally
2. **-R (Remote forward)**: Protocol limitation - destination not sent in tcpip-forward, requires cascaded architecture
3. **-D (SOCKS)**: Client handles SOCKS parsing, sends `direct-tcpip` for each connection

### ✅ Delivered Features

#### 1. SSH Local Forward (-L) Support
- **Usage**: `ssh -A -L 2222:backend:22 user@jump`
- **Mechanism**: Client opens `direct-tcpip` channels through jump to backend
- **Implementation**: 
  - `check_channel_direct_tcpip_request()` validates and stores destination
  - `handle_port_forwarding()` accepts channels and opens backend connections
  - `forward_port_channel()` bidirectional data relay with select()
- **Permission**: Per-policy `port_forwarding_allowed` flag
- **Status**: ✅ Working - tested with SSH and HTTP forwarding

#### 2. SSH Remote Forward (-R) Support - Cascaded Architecture
- **Usage**: `ssh -A -R 9090:localhost:8080 user@jump`
- **Challenge**: SSH protocol doesn't send destination in tcpip-forward request
- **Architecture**: 
  ```
  Client -R 9090:localhost:8080 → Jump pool IP:9090 → Backend localhost:9090 → Jump → Client
  ```
- **Implementation**:
  - Jump opens listener on pool IP (e.g. 10.0.160.129:9090)
  - Backend requests `-R 9090:localhost:9090` to jump
  - Pool IP listener forwards to client via `forwarded-tcpip` channels
  - `handle_cascaded_reverse_forward()` accepts backend channels
- **Permission**: Per-policy `port_forwarding_allowed` flag
- **Status**: ✅ Working - tested with HTTP server and external SMTP
- **Limitation**: Assumes same port for bind and destination (SSH protocol)

#### 3. SSH Dynamic Forward (-D) SOCKS Support
- **Usage**: `ssh -A -D 8123 user@jump`
- **Mechanism**: 
  - Client has built-in SOCKS server on localhost:8123
  - Client parses SOCKS requests and opens `direct-tcpip` channels
  - Jump forwards each connection to backend via existing -L mechanism
- **Channel Type**: `dynamic-tcpip` (added to `check_channel_request()`)
- **Implementation**: Reuses existing `direct-tcpip` infrastructure
- **Permission**: Per-policy `port_forwarding_allowed` flag
- **Status**: ✅ Working - tested with curl --socks5

#### 4. Policy Management Enhancements
- **Renew Endpoint**: `POST /policies/renew/<id>` extends policy by N days (default 30)
- **Reactivate**: Inactive policies can be renewed (sets `is_active=True`)
- **Group Filtering**: Added user group filter in policy list view
- **UI Changes**:
  - Green "Renew" button for active policies
  - Blue "Reactivate" button for inactive policies
  - User Group dropdown filter alongside User filter
- **Status**: ✅ Working - tested with policy renewal and group filtering

#### 5. Stale Session Cleanup
- **Function**: `cleanup_stale_sessions()` runs on SSH proxy startup
- **Action**: Sets `is_active=False`, `ended_at=now`, `termination_reason='service_restart'`
- **Purpose**: Clean database state after service crashes/restarts
- **Status**: ✅ Working

### 📁 Modified Files
- `src/proxy/ssh_proxy.py`:
  - Added `check_channel_direct_tcpip_request()` for -L validation
  - Added `check_port_forward_request()` for -R handling
  - Added `handle_pool_ip_to_localhost_forward()` for pool IP listener
  - Added `handle_cascaded_reverse_forward()` for backend channel relay
  - Added `cleanup_stale_sessions()` for startup cleanup
  - Modified `check_channel_request()` to accept `dynamic-tcpip`
- `src/web/blueprints/policies.py`:
  - Added `renew()` endpoint for policy extension
  - Modified `index()` to support group filtering
- `src/web/templates/policies/index.html`:
  - Added User Group filter dropdown
  - Added Renew/Reactivate buttons
  - Fixed filter parameter names

### 📊 Testing Results
- **SSH -L**: ✅ Local forward working (tested: -L 2222:backend:22)
- **SSH -R**: ✅ Remote forward working (tested: -R 9090:localhost:8080, -R 9093:las.init1.pl:25)
- **SSH -D**: ✅ SOCKS proxy working (tested: curl --socks5 localhost:8123 http://example.com)
- **Policy Renew**: ✅ Extends end_time by 30 days
- **Policy Reactivate**: ✅ Sets is_active=True and extends
- **Group Filter**: ✅ Shows policies for selected user group
- **Stale Cleanup**: ✅ Cleans sessions on restart

### 🐛 Issues Fixed
- Fixed port forwarding permission check (requires `port_forwarding_allowed=True`)
- Fixed variable name error (`client_transport` vs `transport` scope)
- Fixed -R destination assumption (uses same port due to SSH protocol limitation)
- Fixed cascade forward to connect to pool IP instead of localhost
- Fixed double listener on localhost (removed unnecessary listener)

### 📝 Technical Notes
- **-R Limitation**: SSH protocol doesn't send destination in tcpip-forward message, only bind address/port. Jump assumes client used same port for both (e.g. `-R 9090:localhost:9090`). This works because client stores the actual mapping internally and ignores the destination we send in `forwarded-tcpip` channel.
- **Pool IP Binding**: Each session gets unique pool IP, allowing multiple backends to use same port numbers without conflicts.
- **Cascaded Architecture**: Backend doesn't know about client - it only sees jump. Jump handles the relay transparently.

---

## ✅ COMPLETED: v1.3 - RDP MP4 Conversion System (January 2026)

### 🎯 Goal: Web-based RDP Session Video Playback

**Challenge Solved**: RDP recordings (.pyrdp files) required desktop Qt player. Implemented web-based MP4 conversion with background workers.

### ✅ Delivered Features

#### 1. Background Worker Queue System
- **Workers**: 2 systemd services (`jumphost-mp4-converter@1.service`, `@2.service`)
- **Queue**: SQLite `mp4_conversion_queue` table with status tracking
- **Concurrency**: Maximum 2 simultaneous conversions, 10 pending jobs
- **Polling**: Workers check database every 5 seconds
- **Priority**: "Rush" button to move jobs to front of queue
- **Resource Limits**: 150% CPU, 2GB RAM per worker
- **Logs**: `/var/log/jumphost/mp4-converter-worker{1,2}.log`
- **Auto-restart**: Systemd restarts on failure

#### 2. PyRDP MP4 Conversion
- **Environment**: Separate venv at `/opt/jumphost/venv-pyrdp-converter/`
- **Dependencies**: PySide6 + av + pyrdp-mitm
- **FPS**: 10 frames per second (quality/speed balance)
- **Storage**: `/var/log/jumphost/rdp_recordings/mp4_cache/`
- **Format**: H.264 MP4 with audio support
- **Performance**: ~15s for 1.8MB file, ~40s for 3.5MB file
- **Patches Applied**:
  - RDP version enum: Added `RDP10_12 = 0x80011` support
  - Python 3.13 fix: `BinaryIO` import in FileMapping.py
  - FPS override: Modified `convert/utils.py` to pass fps=10

#### 3. Progress Tracking & ETA
- **Real-time Updates**: Parses pyrdp-convert output via regex
- **Progress Bar**: Shows X of Y frames with percentage
- **ETA Calculation**: Based on elapsed time and frames processed
- **Queue Position**: Shows position for pending jobs
- **Status Badge**: Updates color (secondary/warning/primary/success/danger)
- **Polling Interval**: Frontend checks every 2 seconds

#### 4. Web UI Components
- **Convert Button**: Queues new conversion job (max 10 pending)
- **Progress Display**: Live progress bar with ETA countdown
- **Video Player**: HTML5 `<video>` with controls
- **Download Button**: Direct MP4 download link
- **Delete Button**: Remove MP4 from cache (known permission issue)
- **Priority Button**: Move job to front of queue
- **Retry Button**: Requeue failed conversions
- **4 Status Sections**: not-converted, converting, failed, completed

#### 5. API Endpoints
- `POST /sessions/<id>/convert` - Queue conversion (returns position)
- `GET /sessions/<id>/convert-status` - Get status/progress/eta
- `POST /sessions/<id>/convert/priority` - Move to front of queue
- `GET /sessions/<id>/mp4/stream` - Stream MP4 with range support
- `DELETE /sessions/<id>/mp4` - Delete MP4 cache file

#### 6. Database Schema
```sql
CREATE TABLE mp4_conversion_queue (
    id INTEGER PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',  -- pending/converting/completed/failed
    progress INTEGER DEFAULT 0,
    total INTEGER DEFAULT 0,
    eta_seconds INTEGER,
    priority INTEGER DEFAULT 0,
    mp4_path TEXT,
    error_msg TEXT,
    created_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);
CREATE INDEX idx_status ON mp4_conversion_queue(status);
CREATE INDEX idx_priority ON mp4_conversion_queue(priority);
CREATE INDEX idx_created_at ON mp4_conversion_queue(created_at);
```

### 📁 New Files Created
- `/opt/jumphost/src/core/mp4_converter.py` - Worker process with queue management
- `/opt/jumphost/venv-pyrdp-converter/` - Separate Python environment with PySide6
- `/etc/systemd/system/jumphost-mp4-converter@.service` - Systemd template
- `/var/log/jumphost/rdp_recordings/mp4_cache/` - MP4 output directory
- Database migration: Added `mp4_conversion_queue` table

### 🔧 Modified Files
- `src/core/database.py` - Added `MP4ConversionQueue` model
- `src/web/blueprints/sessions.py` - Added 5 MP4 endpoints
- `src/web/templates/sessions/view.html` - Added conversion UI
- `src/web/static/js/custom.js` - Disabled global alert auto-hide
- `venv-pyrdp-converter/lib/python3.13/site-packages/pyrdp/enum/rdp.py` - RDP version fix
- `venv-pyrdp-converter/lib/python3.13/site-packages/pyrdp/convert/utils.py` - FPS=10

### 📊 Testing Results
- **Small file** (1.8MB .pyrdp): ~15s conversion → 180KB MP4 ✅
- **Medium file** (3.5MB .pyrdp): ~40s conversion → 725KB MP4 ✅
- **Progress tracking**: Real-time updates with accurate ETA ✅
- **Video streaming**: HTML5 player with seek support ✅
- **Queue system**: FIFO + priority working correctly ✅
- **Priority rush**: Moves job to front immediately ✅
- **Concurrent workers**: Both workers process jobs simultaneously ✅
- **Video playback**: `video.load()` fix enables immediate playback ✅

### 🐛 Critical Bugs Fixed
1. **Global Alert Auto-hide**: `custom.js` was hiding all `.alert` elements after 5s
   - Impact: Content disappeared on sessions, users, groups pages
   - Fix: Commented out entire auto-hide block
   - Result: All alerts stay visible unless manually closed

2. **Video Not Playing**: Video player loaded but didn't start playback
   - Root cause: Browser didn't load source when section became visible
   - Fix: Added `video.load()` call when status='completed'
   - Result: Video plays immediately after conversion

3. **Wrong Video URL**: Relative path `/sessions/<id>/mp4/stream` failed
   - Fix: Changed to `url_for('sessions.stream_mp4', session_id=...)`
   - Result: Proper absolute URL generation

### ⚠️ Known Issues
- **Delete MP4 Permission**: Flask runs as p.mojski, workers as root
  - Files owned by root, Flask can't delete
  - Workaround: Admin manual cleanup or chown mp4_cache/ to p.mojski
- **datetime.utcnow() Warnings**: 3 deprecation warnings in Python 3.13
  - Non-critical, functionality works correctly
  - TODO: Replace with `datetime.now(datetime.UTC)`

### 💡 Design Decisions
- **FPS=10**: Balance between quality and speed (3x faster than realtime)
- **2 Workers**: Optimal for VM resources, prevents overload
- **10 Pending Max**: Reasonable queue size, prevents spam
- **2s Polling**: Fast enough for live feel, not too aggressive
- **Separate venv**: Isolates PySide6 dependencies from main app
- **File Glob**: pyrdp-convert adds prefix to filename, use pattern matching

---

---

## � IN PROGRESS: v1.4 - Advanced Access Control & User Experience (January 2026)

### 🎯 Goals: Recursive Groups, Port Forwarding, Curl CLI

**Status**: Planning phase - January 2026

**Strategy**: Build from foundation to interface
1. Recursive groups (infrastructure)
2. Port forwarding (features using new permissions)
3. Curl API (user-friendly interface)

---

### 📋 Feature 1: Recursive Groups & Nested Permissions

**Priority**: 🔴 Critical - Foundation for all access control

**Problem**: Current system supports flat groups only. Need hierarchical organization.

**Requirements**:
- **User Groups**: Users can belong to groups (e.g., "biuro", "ideo")
- **Group Nesting**: Groups can contain other groups (e.g., "biuro" ⊂ "ideo")
- **Permission Inheritance**: User in "biuro" automatically gets "ideo" permissions
- **Server Groups**: Same nesting for servers (e.g., "prod-web" ⊂ "production")
- **Cycle Detection**: Prevent infinite loops (A → B → C → A)

**Use Cases**:
```
Example 1: User Groups
- Group "ideo" (parent)
  └── Group "biuro" (child)
      └── User "p.mojski"
      
Grant for "ideo" → applies to "biuro" → applies to "p.mojski"

Example 2: Server Groups
- Group "production" (parent)
  ├── Group "prod-web" (child)
  │   ├── web01.prod
  │   └── web02.prod
  └── Group "prod-db" (child)
      ├── db01.prod
      └── db02.prod
      
Grant to "production" → access to all 4 servers
```

**Database Changes**:
```sql
-- New Tables
CREATE TABLE user_groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    parent_group_id INTEGER REFERENCES user_groups(id),  -- Recursive!
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE user_group_members (
    id SERIAL PRIMARY KEY,
    user_group_id INTEGER REFERENCES user_groups(id),
    user_id INTEGER REFERENCES users(id),
    added_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_group_id, user_id)
);

-- Extend Existing
ALTER TABLE server_groups ADD COLUMN parent_group_id INTEGER REFERENCES server_groups(id);
ALTER TABLE access_policies ADD COLUMN user_group_id INTEGER REFERENCES user_groups(id);
```

**Algorithm: Recursive Membership Resolution**:
```python
def get_all_user_groups(user_id, db):
    """Get all groups user belongs to (direct + inherited via parent groups)"""
    visited = set()
    queue = get_direct_groups(user_id)  # Start with direct membership
    
    while queue:
        group = queue.pop(0)
        if group.id in visited:
            continue  # Cycle detection
        visited.add(group.id)
        
        # Add parent groups to queue
        if group.parent_group_id:
            parent = db.query(UserGroup).get(group.parent_group_id)
            if parent:
                queue.append(parent)
    
    return visited

def get_all_servers_in_group(group_id, db):
    """Get all servers in group (direct + inherited from child groups)"""
    visited = set()
    queue = [group_id]
    
    while queue:
        gid = queue.pop(0)
        if gid in visited:
            continue
        visited.add(gid)
        
        # Add direct servers
        servers = get_direct_servers(gid)
        visited.update(servers)
        
        # Add child groups to queue
        children = db.query(ServerGroup).filter(ServerGroup.parent_group_id == gid).all()
        queue.extend([c.id for c in children])
    
    return visited
```

**Access Control Integration**:
```python
# In AccessControlEngineV2.check_access_v2()
def check_access_v2(self, db, source_ip, dest_ip, protocol):
    user = self.find_user_by_source_ip(db, source_ip)
    server = self.find_backend_by_proxy_ip(db, dest_ip)
    
    # Get ALL groups user belongs to (including inherited)
    user_groups = get_all_user_groups(user.id, db)
    
    # Check policies for:
    # 1. Direct user access
    # 2. Any of user's groups (direct or inherited)
    policies = db.query(AccessPolicy).filter(
        or_(
            AccessPolicy.user_id == user.id,
            AccessPolicy.user_group_id.in_(user_groups)
        ),
        # ... rest of policy checks
    ).all()
```

**Cycle Detection**:
```python
def validate_no_cycles(group_id, new_parent_id, db):
    """Ensure setting parent_id won't create cycle"""
    visited = set([group_id])
    current = new_parent_id
    
    while current:
        if current in visited:
            raise ValueError(f"Cycle detected: {group_id} -> ... -> {current} -> {group_id}")
        visited.add(current)
        
        parent_group = db.query(UserGroup).get(current)
        current = parent_group.parent_group_id if parent_group else None
```

**Web GUI Changes**:
- User Groups management page (create, nest, assign users)
- Server Groups tree view (drag & drop nesting)
- Policy wizard: Select user OR user group
- Visualization: Group hierarchy tree

**Performance Considerations**:
- Cache group membership in Redis (TTL 5min)
- Indexed queries on parent_group_id
- Limit nesting depth (max 10 levels)

**Migration Path**:
1. Create new tables (Alembic migration)
2. Migrate existing server_groups (all at root level initially)
3. Deploy new AccessControlEngineV2
4. Test with simple 2-level hierarchy
5. Roll out to production

**Status**: 
- [ ] Database schema design
- [ ] Alembic migration
- [ ] Recursive algorithms (membership, cycle detection)
- [ ] Update AccessControlEngineV2
- [ ] Web GUI for group management
- [ ] Testing (edge cases, cycles, performance)

---

### 📋 Feature 2: SSH Port Forwarding (-L / -R)

**Priority**: 🟡 High - Critical for daily productivity

**Problem**: Current SSH proxy doesn't support port forwarding. Users can't use VS Code Remote SSH, database tunnels, or other port forwarding workflows.

**Requirements**:
- **Local Forwarding** (`ssh -L`): Client opens port, forwards to backend
- **Remote Forwarding** (`ssh -R`): Backend opens port, forwards to client
- **Access Control**: New permission `port_forwarding_allowed` (per user or group)
- **Logging**: Track all port forward requests (source, dest, ports)
- **Restrictions**: Configurable allowed destination IPs/ports

**Use Cases**:
```bash
# Local forwarding (ssh -L)
ssh -L 5432:db-backend:5432 jumphost
# Now: localhost:5432 -> jumphost -> db-backend:5432

# Remote forwarding (ssh -R)
ssh -R 8080:localhost:3000 jumphost
# Now: jumphost:8080 -> your-machine:3000

# VS Code Remote SSH
# VS Code opens random high port, forwards stdin/stdout
```

**Paramiko Channels**:
- `direct-tcpip`: Local forwarding (ssh -L)
- `forwarded-tcpip`: Remote forwarding (ssh -R)

**Database Changes**:
```sql
ALTER TABLE users ADD COLUMN port_forwarding_allowed BOOLEAN DEFAULT FALSE;
ALTER TABLE user_groups ADD COLUMN port_forwarding_allowed BOOLEAN DEFAULT FALSE;

CREATE TABLE port_forward_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) REFERENCES sessions(session_id),
    source_ip VARCHAR(45),
    username VARCHAR(255),
    forward_type VARCHAR(20),  -- 'local' or 'remote'
    listen_host VARCHAR(255),
    listen_port INTEGER,
    dest_host VARCHAR(255),
    dest_port INTEGER,
    started_at TIMESTAMP DEFAULT NOW(),
    ended_at TIMESTAMP,
    bytes_sent BIGINT DEFAULT 0,
    bytes_received BIGINT DEFAULT 0
);
```

**SSH Proxy Changes** (`src/proxy/ssh_proxy.py`):
```python
class SSHProxyServerInterface(paramiko.ServerInterface):
    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        elif kind == 'direct-tcpip':  # ssh -L
            return self._check_port_forward_request('local')
        elif kind == 'forwarded-tcpip':  # ssh -R
            return self._check_port_forward_request('remote')
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED
    
    def _check_port_forward_request(self, forward_type):
        # Check if user has port_forwarding_allowed
        if not self.user.port_forwarding_allowed:
            # Check group permissions (recursive!)
            user_groups = get_all_user_groups(self.user.id, db)
            if not any(g.port_forwarding_allowed for g in user_groups):
                logger.warning(f"Port forwarding denied for {self.username}")
                return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED
        
        logger.info(f"Port forwarding {forward_type} allowed for {self.username}")
        return paramiko.OPEN_SUCCEEDED
    
    def check_channel_direct_tcpip_request(self, chanid, origin, destination):
        """Called for ssh -L"""
        dest_addr, dest_port = destination
        
        # Validate destination (optional whitelist)
        if not self._validate_port_forward_destination(dest_addr, dest_port):
            return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED
        
        # Log port forward session
        self._log_port_forward('local', origin, destination)
        
        return paramiko.OPEN_SUCCEEDED
```

**Port Forward Handler**:
```python
def handle_direct_tcpip(channel, origin, destination):
    """Forward traffic between client and destination"""
    try:
        dest_addr, dest_port = destination
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((dest_addr, dest_port))
        
        # Bidirectional forwarding
        while True:
            r, w, x = select.select([channel, sock], [], [])
            if channel in r:
                data = channel.recv(4096)
                if not data:
                    break
                sock.sendall(data)
            if sock in r:
                data = sock.recv(4096)
                if not data:
                    break
                channel.sendall(data)
    finally:
        sock.close()
        channel.close()
```

**Configuration**:
```python
# In config or database
PORT_FORWARD_WHITELIST = {
    'allowed_dest_ips': ['10.30.0.*', '192.168.*'],  # Glob patterns
    'blocked_ports': [22, 3389],  # No forwarding to SSH/RDP ports
    'require_approval': False  # Future: admin approval workflow
}
```

**Web GUI**:
- User profile: Checkbox "Allow Port Forwarding"
- Group settings: Checkbox "Allow Port Forwarding" (inherited by members)
- Active Port Forwards widget (dashboard)
- Audit log: Port forward attempts (granted/denied)

**Status**:
- [ ] Database schema (port_forwarding_allowed, port_forward_sessions)
- [ ] SSH proxy: channel request handlers
- [ ] Bidirectional traffic forwarding
- [ ] Logging and audit
- [ ] Web GUI toggles
- [ ] Testing (ssh -L, ssh -R, VS Code Remote)

---

### 📋 Feature 3: Curl-based CLI API

**Priority**: 🟢 Medium - User experience enhancement

**Problem**: Users need to interact with jumphost from any machine without installing tools. Only `curl` is universally available.

**Requirements**:
- **User-Agent Detection**: Recognize curl, return plain text instead of HTML
- **Simple Endpoints**: Short, memorable URLs
- **Self-Service**: Request access, check status, list grants
- **Admin Approval**: Workflow for sensitive operations
- **No Auth (for reads)**: Use source IP (already authenticated)

**Example Usage**:
```bash
# Check who you are
$ curl jump/whoami
You are: p.mojski (pawel.mojski@example.com)
Source IP: 100.64.0.20
Active grants: 3 servers (5 expire in < 7 days)

# Backend info
$ curl jump/i/10.30.0.140
test-rdp-server (10.30.0.140)
  Proxy IP: 10.0.160.130
  Groups: test-servers, rdp-hosts
  Your access: ✓ RDP (expires 2026-02-01)

# List your grants
$ curl jump/p/list
Active Grants:
  [RDP] 10.30.0.140 (test-rdp-server) - expires 2026-02-01
  [SSH] 10.30.0.200 (linux-dev)       - expires 2026-01-15
  [SSH] 10.30.0.201 (linux-prod)      - permanent

# Request new access
$ curl jump/p/request/ssh/10.30.0.202
Access request created: #42
Server: linux-staging (10.30.0.202)
Protocol: SSH
Status: Pending admin approval
View: http://jump:5000/requests/42

# Add your IP (if multiple IPs)
$ curl -X POST jump/p/add-ip/100.64.0.99
Request created: #43
New IP: 100.64.0.99 will be linked to your account
Status: Pending admin approval
```

**API Endpoints**:
```python
# src/web/blueprints/cli_api.py

@cli_api.route('/whoami')
def whoami():
    source_ip = request.remote_addr
    user = find_user_by_source_ip(source_ip)
    
    if is_curl_request():
        return format_plain_text({
            'user': user.username,
            'email': user.email,
            'source_ip': source_ip,
            'grants': count_active_grants(user)
        })
    else:
        return jsonify({...})  # JSON for browsers

@cli_api.route('/i/<path:ip_or_name>')
def backend_info(ip_or_name):
    server = find_server(ip_or_name)  # By IP or name
    user = find_user_by_source_ip(request.remote_addr)
    
    access = check_access(user, server)
    
    return format_plain_text({
        'server': server,
        'proxy_ip': server.proxy_ip,
        'groups': server.groups,
        'your_access': access
    })

@cli_api.route('/p/request/<protocol>/<ip>')
def request_access(protocol, ip):
    user = find_user_by_source_ip(request.remote_addr)
    server = find_server(ip)
    
    # Create access request (new table)
    req = AccessRequest(
        user_id=user.id,
        server_id=server.id,
        protocol=protocol,
        status='pending',
        requested_at=datetime.now()
    )
    db.add(req)
    db.commit()
    
    # Notify admins (future: email/Slack)
    
    return format_plain_text({
        'request_id': req.id,
        'status': 'pending',
        'url': f'http://{request.host}/requests/{req.id}'
    })
```

**User-Agent Detection**:
```python
def is_curl_request():
    ua = request.headers.get('User-Agent', '').lower()
    return 'curl' in ua or 'wget' in ua
```

**Admin Approval Workflow**:
```sql
CREATE TABLE access_requests (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    server_id INTEGER REFERENCES servers(id),
    protocol VARCHAR(10),
    justification TEXT,
    status VARCHAR(20) DEFAULT 'pending',  -- pending/approved/denied
    requested_at TIMESTAMP DEFAULT NOW(),
    reviewed_by INTEGER REFERENCES users(id),
    reviewed_at TIMESTAMP,
    approval_notes TEXT
);
```

**Web GUI**:
- `/requests` - Pending requests list (admins only)
- Approve/Deny buttons
- Auto-create AccessPolicy on approval

**Shortcuts**:
```bash
# Add to /etc/hosts or DNS
10.0.160.5  jump

# Or create shell alias
alias jh='curl -s jump'
jh /whoami
jh /i/10.30.0.140
```

**Status**:
- [ ] Blueprint: cli_api.py
- [ ] User-agent detection
- [ ] Plain text formatters
- [ ] Endpoints: whoami, info, list, request
- [ ] Database: access_requests table
- [ ] Admin approval GUI
- [ ] Testing with curl
- [ ] Documentation (user guide)

---

## 📋 Backlog: Future Enhancements

### MP4 System Improvements
- [ ] Fix delete MP4 permission issue (chown mp4_cache to p.mojski)
- [ ] Replace datetime.utcnow() with datetime.now(datetime.UTC) (Python 3.13)
- [ ] Configurable FPS per conversion (ENV variable or UI setting)
- [ ] Auto-cleanup old MP4 files (retention policy)
- [ ] WebSocket/SSE for real-time progress (reduce polling)
- [ ] Conversion metrics dashboard (avg time, success rate)

### Session Monitoring
- [ ] SSH session video recording (ttyrec/asciinema format)
- [ ] Session playback speed controls (0.5x, 1x, 2x)
- [ ] Search within session transcripts
- [ ] Export session reports (PDF/JSON)

### Advanced Access Control
- [ ] FreeIPA integration (user sync + authentication)
- [ ] Multi-factor authentication (TOTP)
- [ ] Time-based access (only during business hours)
- [ ] Break-glass emergency access

### Performance & Scaling
- [ ] Redis cache for session state
- [ ] Connection pooling for database
- [ ] Load balancing across multiple jump hosts
- [ ] Separate SSH proxy instances per backend

### Monitoring & Alerting
- [ ] Prometheus metrics export
- [ ] Grafana dashboards
- [ ] Email/Slack alerts for denied access
- [ ] Long session warnings
- [ ] Resource usage monitoring

---

## 🗑️ DEPRECATED: v1.2 - RDP Session Viewer (Completed as v1.3)

This section moved to v1.3 - RDP MP4 Conversion System.

**Original Goal**: Web-based RDP session replay  
**Status**: ✅ COMPLETED in v1.3 with full MP4 conversion pipeline

### Historical Notes (v1.2-dev)
- RDP Recording Metadata Extraction ✅
- Web Interface - Basic Info Display ✅
- JSON conversion with caching ✅
- MP4 conversion blocked by CPU (resolved in v1.3) ✅

---

## 🔄 OLD CONTEXT: v1.2 - RDP Session Viewer (January 2026) - COMPLETED, MOVED TO v1.3

### 🎯 Goal: Web-based RDP Session Replay

**Challenge**: RDP recordings (.pyrdp files) require desktop Qt player for full video replay. Need web-based solution for security audit.

**Current Status**: Backend infrastructure complete, waiting for VM CPU upgrade for MP4 conversion.

### ✅ Completed Work

#### 1. RDP Recording Metadata Extraction
- **JSON Conversion**: `pyrdp-convert -f json` integration
- **Caching System**: `/var/log/jumphost/rdp_recordings/json_cache/`
- **Metadata Parsing**: Host, resolution, username, domain, duration
- **Event Counting**: Keyboard keystrokes, mouse events
- **Function**: `get_rdp_recording_info()` in sessions.py

#### 2. Web Interface - Basic Info Display
- **Session Summary Card**: Host, resolution, duration, event statistics
- **Download Support**: .pyrdp file download button
- **Playback Instructions**: How to use pyrdp-player locally
- **Fallback UI**: If JSON conversion fails, show basic file info
- **Template**: Updated `templates/sessions/view.html`

#### 3. API Endpoints
- **Route**: `/sessions/<id>/rdp-events` - Returns converted JSON
- **Validation**: Checks protocol is RDP, session exists, recording available
- **Error Handling**: 404/500 with error messages

### ⏸️ Blocked: MP4 Video Conversion

**Issue**: PyRDP MP4 export requires:
- PySide6 (Qt for Python)
- CPU instructions: ssse3, sse4.1, sse4.2, popcnt
- Current VM CPU: "Common KVM processor" (basic, missing required flags)

**Solution Path**:
1. ✅ Created separate venv: `/opt/jumphost/venv-pyrdp-converter/`
2. ✅ Installed: PySide6 + av + pyrdp-mitm
3. ❌ **BLOCKED**: CPU doesn't support SSSE3/SSE4 (Qt requirement)
4. 🔜 **NEXT**: Proxmox VM CPU upgrade to `host` type

**Proxmox Configuration Needed**:
```bash
# VM Configuration (GUI or /etc/pve/qemu-server/XXX.conf):
cpu: host
# OR specific flags:
cpu: kvm64,flags=+ssse3;+sse4.1;+sse4.2;+popcnt
```

### 📋 After CPU Upgrade - TODO

1. **Test MP4 Conversion**:
   ```bash
   source /opt/jumphost/venv-pyrdp-converter/bin/activate
   pyrdp-convert -f mp4 -o /tmp/test.mp4 /var/log/jumphost/rdp_recordings/replays/recording.pyrdp
   ```

2. **Implement MP4 Generation**:
   - Background job queue (Celery or simple subprocess)
   - Convert .pyrdp → .mp4 on-demand or scheduled
   - Cache MP4 files in `/var/log/jumphost/rdp_recordings/mp4_cache/`
   - Progress tracking for long conversions

3. **Web Video Player**:
   - HTML5 `<video>` element in session detail page
   - Timeline scrubbing, play/pause controls
   - Keyboard shortcuts (space, arrows)
   - Optional: Download MP4 button

4. **Performance Optimization**:
   - Async conversion (don't block Flask)
   - Queue system for multiple conversions
   - Thumbnail generation for quick preview
   - Bandwidth throttling for large videos

### 🗂️ Files Modified (v1.2-dev)

**Backend**:
- `src/web/blueprints/sessions.py`:
  - Added `get_rdp_recording_info()` - JSON conversion with caching
  - Added `format_duration()` - Human-readable time formatting
  - Added `/sessions/<id>/rdp-events` endpoint
  - Glob pattern matching for pyrdp-convert output filenames

**Frontend**:
- `templates/sessions/view.html`:
  - RDP session summary card (metadata + statistics)
  - Download + playback instructions
  - Placeholder for future video player
  - Graceful fallback if conversion fails

**System**:
- Created `/var/log/jumphost/rdp_recordings/json_cache/` (owned by p.mojski)
- Created `/opt/jumphost/venv-pyrdp-converter/` venv (PySide6 ready)

### 📊 Test Results

**JSON Conversion**:
- ✅ Manual test: 254 events converted in <1s
- ✅ Metadata extraction: host, resolution, username, timestamps
- ✅ Event counting: keyboard (78), mouse (175) for test session
- ✅ Cache system: Checks mtime, avoids re-conversion

**Web Interface**:
- ✅ Session detail shows RDP metadata
- ✅ Download button works
- ✅ Instructions displayed correctly
- ❌ MP4 video player: Blocked by CPU (PySide6 segfault)

### 🐛 Issues Fixed

- Fixed pyrdp-convert output filename pattern (appends source name)
- Fixed JSON cache directory permissions (p.mojski ownership)
- Fixed glob pattern matching for cached JSON files
- Removed non-functional event timeline (replaced with summary)

### 🎯 Success Criteria (After CPU Upgrade)

- [ ] MP4 conversion works without errors
- [ ] Web interface displays embedded video player
- [ ] Video playback smooth (no buffering on 1920x1200)
- [ ] Conversion time acceptable (<30s for 5-minute session)
- [ ] Audit team can review RDP sessions without downloading files

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
- [x] ssh_proxy.service (jumphost-ssh-proxy)
- [x] rdp-proxy.service (direct pyrdp-mitm)
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

## Phase 5: Web Management Interface ✓ COMPLETE

### Task 10: Flask Web GUI ✓ COMPLETE
**Priority**: HIGH
**Status**: 🟢 PRODUCTION READY

**Goal**: Modern web-based management interface for all jumphost operations

#### Completed Features ✓

##### 1. Flask Application Setup ✓
- [x] Flask 3.1.2 with Blueprint architecture
- [x] Flask-Login for session management
- [x] Flask-WTF for form handling with CSRF protection
- [x] Flask-Cors for API endpoints
- [x] Bootstrap 5.3.0 frontend framework
- [x] Bootstrap Icons 1.11.0
- [x] Chart.js 4.4.0 for statistics
- [x] Custom CSS with service status indicators
- [x] Custom JavaScript with AJAX and Chart.js integration

##### 2. Authentication ✓
- [x] Login page with Bootstrap 5 design
- [x] Placeholder authentication (admin/admin)
- [x] Flask-Login integration with User model (UserMixin)
- [x] Session management with secure cookies
- [x] User loader from database
- [x] Logout functionality
- [x] Flash messages for user feedback
- [x] **Ready for Azure AD integration** (Flask-Azure-AD compatible)

##### 3. Dashboard ✓
- [x] Service status monitoring (SSH Proxy, RDP Proxy, PostgreSQL)
- [x] Process uptime calculation with psutil
- [x] Statistics cards:
  - Total users count
  - Total servers count
  - Active policies count
  - Today's connections count
- [x] Today's activity (granted vs denied with success rate)
- [x] Active sessions table (last 5 sessions)
- [x] Recent audit log (last 10 entries with color coding)
- [x] Auto-refresh stats every 30 seconds via AJAX
- [x] API endpoint: `/dashboard/api/stats` (JSON)

##### 4. User Management ✓
- [x] List all users with source IPs and policy counts
- [x] Add new user with multiple source IPs
- [x] Edit user details (username, email, active status)
- [x] View user details:
  - User information table
  - Source IP management (add/delete/toggle active)
  - Associated access policies
- [x] Delete user (cascade delete source IPs and policies)
- [x] Dynamic source IP fields on add form
- [x] Modal dialog for adding source IPs
- [x] Validation and error handling

##### 5. Server Management ✓
- [x] List all servers with proxy IPs and protocols
- [x] Add new server with automatic IP allocation
- [x] Edit server details (name, address, port, protocols, active status)
- [x] View server details:
  - Server information table
  - IP allocation details (proxy IP, NAT ports)
  - Group memberships list
- [x] Delete server
- [x] Enable/disable SSH and RDP protocols
- [x] Optional IP allocation checkbox on add form
- [x] Integration with IPPoolManager

##### 6. Group Management ✓
- [x] List all server groups
- [x] Create new group (name, description)
- [x] Edit group details
- [x] View group with members:
  - Group information table
  - Member servers list with protocols
  - Add/remove servers from group
- [x] Delete group
- [x] Available servers dropdown (excludes current members)
- [x] Modal dialog for adding servers to group

##### 7. Policy Management (Grant Wizard) ✓
- [x] List all access policies with filters:
  - Filter by user
  - Show/hide inactive policies
- [x] Grant access wizard with scope types:
  - **Group scope**: All servers in a group
  - **Server scope**: Single server (all protocols)
  - **Service scope**: Single server + specific protocol
- [x] User selection with dynamic source IP loading
- [x] Source IP dropdown (ANY or specific IP)
- [x] Protocol filtering (NULL, ssh, rdp)
- [x] SSH login restrictions (comma-separated list)
- [x] Temporal access:
  - Start time picker (default: now)
  - Duration in hours (default: permanent)
  - Auto-calculate end_time
- [x] Revoke policy (soft delete - sets is_active=false)
- [x] Delete policy (hard delete from database)
- [x] Dynamic form fields based on scope type
- [x] API endpoint: `/policies/api/user/<id>/ips` (JSON)

##### 8. Monitoring ✓
- [x] Main monitoring page with charts:
  - Hourly connections chart (last 24 hours) - Line chart
  - Top users chart (last 7 days) - Bar chart
- [x] Audit log viewer:
  - Pagination (50 entries per page)
  - Filters: action type, user, date range
  - Color-coded actions (granted=green, denied=red, closed=gray)
  - Full details per entry
- [x] API endpoints:
  - `/monitoring/api/stats/hourly` (JSON)
  - `/monitoring/api/stats/by_user` (JSON)
- [x] Chart.js integration with live updates
- [x] Pagination controls with page numbers

##### 9. UI/UX ✓
- [x] Base template with Bootstrap 5 navbar
- [x] Responsive design (mobile-friendly)
- [x] Dark navbar with brand logo
- [x] Active navigation highlighting
- [x] User dropdown menu with logout
- [x] Flash message container with auto-dismiss (5 seconds)
- [x] Service status indicators (pulsing green dot for running)
- [x] Stats cards with hover effects
- [x] Badges for status (active/inactive, protocols)
- [x] Color-coded audit log entries
- [x] Confirmation dialogs for delete operations
- [x] Loading spinners (prepared)
- [x] Error pages (404, 500)
- [x] Favicon route (prevents 404 errors)

##### 10. Backend Integration ✓
- [x] Database session management (before_request, teardown_request)
- [x] Flask g.db for per-request sessions
- [x] User model with Flask-Login UserMixin
- [x] Template filters:
  - `datetime` - Format datetime as string
  - `timeago` - Relative time (e.g., "5m ago")
- [x] Context processor for global variables
- [x] Error handlers (404, 500)
- [x] All blueprints with proper imports and sys.path fixes

**Files Created**:
```
/opt/jumphost/src/web/
├── app.py (142 lines)
├── blueprints/
│   ├── __init__.py
│   ├── auth.py (50 lines)
│   ├── dashboard.py (190 lines)
│   ├── users.py (150 lines)
│   ├── servers.py (110 lines)
│   ├── groups.py (140 lines)
│   ├── policies.py (150 lines)
│   └── monitoring.py (120 lines)
├── templates/
│   ├── base.html (137 lines)
│   ├── dashboard/index.html
│   ├── users/index.html, view.html, add.html, edit.html
│   ├── servers/index.html, view.html, add.html, edit.html
│   ├── groups/index.html, view.html, add.html, edit.html
│   ├── policies/index.html, add.html
│   ├── monitoring/index.html, audit.html
│   ├── auth/login.html
│   └── errors/404.html, 500.html
└── static/
    ├── css/style.css (185 lines)
    └── js/app.js (215 lines)
```

**Deployment**:
- Development: `python3 app.py` (port 5000)
- Production: `gunicorn --bind 0.0.0.0:5000 --workers 4 app:app`
- Reverse Proxy: nginx → http://localhost:5000

**Security**:
- CSRF protection on all forms
- Session cookies with HTTPOnly flag
- SQL injection prevention via SQLAlchemy ORM
- XSS prevention via Jinja2 autoescaping
- Login required decorators on all routes
- Flash messages for user feedback

**Known Limitations**:
- Authentication is placeholder (admin/admin)
- Need to integrate with Azure AD (Flask-Azure-AD)
- No real-time session monitoring (WebSocket)
- No session recording playback viewer yet
- No bulk operations (mass grant/revoke)

**Next Steps**:
- [ ] Azure AD integration (Flask-Azure-AD)
- [ ] Production deployment with gunicorn + systemd
- [ ] nginx reverse proxy configuration
- [ ] SSL/TLS certificates
- [ ] Session recording playback in web GUI
- [ ] Real-time monitoring with WebSockets
- [ ] Email notifications
- [ ] API documentation (Swagger/OpenAPI)

---

## Questions for User

1. **IP Allocation**: Automatycznie przy dodaniu serwera czy na żądanie?
2. **FreeIPA**: Jaki jest hostname/domain FreeIPA?
3. **Web GUI**: ✓ DONE - Flask + Bootstrap 5
4. **Monitoring**: Prometheus + Grafana OK?
5. **Session Recordings**: Jak długo trzymać? Auto-delete po X dniach?
6. **Azure AD**: Tenant ID, Client ID, Client Secret?
7. **Production**: nginx + SSL certificate?

---

## Changelog

### 2026-01-04 🎉 WEB GUI v1.1 RELEASE + SESSION TRACKING ⭐
- ✅ **Flask Web GUI** fully implemented with Bootstrap 5
- ✅ **7 Blueprints**: dashboard, users, servers, groups, policies, monitoring, auth
- ✅ **25+ Templates**: Complete CRUD interfaces for all resources
- ✅ **Dashboard**: Service monitoring, statistics, charts, recent activity
- ✅ **User Management**: CRUD + multiple source IPs per user
- ✅ **Server Management**: CRUD + automatic IP allocation
- ✅ **Group Management**: CRUD + N:M server relationships
- ✅ **Policy Wizard**: Grant access with group/server/service scopes
- ✅ **Monitoring**: Audit logs with pagination, connection charts
- ✅ **Authentication**: Placeholder (admin/admin) ready for Azure AD
- ✅ **Responsive Design**: Mobile-friendly Bootstrap 5 layout
- ✅ **AJAX Updates**: Dashboard stats refresh, Chart.js integration
- ✅ **Database Integration**: Flask-Login, session management, User model
- ✅ **REAL-TIME SESSION TRACKING** ⭐ (NEW in v1.1):
  - `sessions` table with 18 fields tracking active/historical connections
  - SSH session tracking: Creates on backend auth, closes on channel close
  - RDP session tracking: Creates on access grant, closes on TCP disconnect (observer pattern)
  - Dashboard "Active Sessions" shows: Protocol, User, Server, Backend IP, Source IP, SSH Agent, Duration
  - SSH subsystem detection (sftp, scp), SSH agent forwarding tracking
  - RDP multiplexing: Deduplikacja connections within 10s window
  - Recording path and file size tracked automatically
  - Duration calculation on session close
  - Multiple concurrent sessions supported independently
- ✅ **UTMP/WTMP INTEGRATION** 🎯 (NEW in v1.1):
  - Sessions logged to system utmp/wtmp for audit trail
  - SSH sessions: Registered as ssh0-ssh99 with backend user@server format
  - RDP sessions: Registered as rdp0-rdp99 with server name
  - Custom `jw` command (jumphost w) shows active proxy sessions
  - Compatible with system logging and monitoring tools
  - Automatic login/logout on session start/close
- 📦 **Total**: ~3,700 lines of Python/HTML/CSS/JS for web GUI + session tracking

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
- Backup: `/opt/jumphost/src/proxy/rdp_mitm_backup.py.orig` (2026-01-04)
- Changes: 
  - Added jumphost module imports (database, access_control, Session model)
  - Modified `MITMServerFactory.buildProtocol()` to check source_ip access
  - Uses `deepcopy(config)` for per-connection backend configuration
  - Sets `config.targetHost` from grant before creating RDPMITM
  - Integrated audit logging for RDP connections
  - **SESSION TRACKING** (NEW v1.1): ⭐
    - Creates Session record in database on access granted
    - TCP observer pattern for disconnect detection (client & server)
    - RDP multiplexing: Reuses session for connections within 10s window
    - Observer references preserved in `protocol._jumphost_client_observer` & `_server_observer`
    - Calculates duration and recording file size on session close
    - Multiple concurrent sessions supported independently

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
