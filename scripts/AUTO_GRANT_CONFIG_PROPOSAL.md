# Auto-Grant Configuration Strategy - Proposal

## Problem

Need configurable auto-grant settings:
1. **Editable timeout**: 60 minutes inactivity timeout (currently hardcoded)
2. **Enable/disable toggle**: Auto-grant, auto-user, auto-server creation
3. **Where to configure**: Per-gate? Per-instance? Centralized in Tower?

---

## Proposal: 3-Tier Configuration Model

### Tier 1: Global Defaults (config/settings.yaml)

**Scope**: Entire Inside instance (all gates)  
**Use case**: Default policy for new gates, fallback when gate-specific config not set

```yaml
# config/settings.yaml
auto_grant:
  enabled: true  # Master switch
  duration_days: 7
  inactivity_timeout_minutes: 60
  port_forwarding_allowed: true
  
auto_user_create:
  enabled: false  # Not implemented yet
  default_user_group: "Auto-Registered Users"
  
auto_server_create:
  enabled: false  # Not implemented yet
  default_server_group: "Auto-Discovered"
```

**Pros**:
- Simple, file-based configuration
- Version controlled (git)
- Easy to set global policy

**Cons**:
- Requires restart to change
- No per-gate customization
- Not hot-reloadable

---

### Tier 2: Per-Gate Configuration (Database - gates table)

**Scope**: Individual gate  
**Use case**: Different gates have different policies (DMZ vs internal, prod vs dev)

**Database Schema Changes**:

```sql
-- Migration: Add auto-grant config to gates table
ALTER TABLE gates ADD COLUMN auto_grant_enabled BOOLEAN DEFAULT NULL;
ALTER TABLE gates ADD COLUMN auto_grant_duration_days INTEGER DEFAULT NULL;
ALTER TABLE gates ADD COLUMN auto_grant_inactivity_timeout_minutes INTEGER DEFAULT NULL;
ALTER TABLE gates ADD COLUMN auto_grant_port_forwarding BOOLEAN DEFAULT NULL;

-- NULL = inherit from global config
-- Non-NULL = override global config

-- Example: DMZ gate with stricter policy
UPDATE gates SET 
    auto_grant_enabled = true,
    auto_grant_duration_days = 1,  -- Only 1 day in DMZ
    auto_grant_inactivity_timeout_minutes = 30,  -- Shorter timeout
    auto_grant_port_forwarding = false  -- No port forwarding in DMZ
WHERE name = 'gate-dmz';

-- Example: Internal gate inherits global config
-- (all columns NULL = use global defaults)
```

**Web UI**:
- Gate configuration page → "Auto-Grant Settings" section
- Checkboxes: Enable/Disable
- Input fields: Duration (days), Timeout (minutes)
- "Reset to defaults" button (sets all to NULL)

**Pros**:
- Per-gate customization
- Hot-reloadable (no restart needed)
- Web UI editable
- NULL = inherit global (simple default)

**Cons**:
- More complex database schema
- Need UI for editing

---

### Tier 3: Runtime Override (optional - for testing)

**Scope**: Temporary override via API  
**Use case**: Testing, emergency disable

```bash
# Temporarily disable auto-grant on specific gate
curl -X POST https://tower/api/v1/gates/5/auto-grant \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"enabled": false}'

# Re-enable
curl -X POST https://tower/api/v1/gates/5/auto-grant \
     -d '{"enabled": true}'
```

**Pros**:
- Emergency kill switch
- Testing without DB changes

**Cons**:
- Lost on restart (unless persisted)
- Complexity

---

## Recommended Implementation: Tier 1 + Tier 2

**Priority order**:
1. Check gate-specific config (gates table)
2. If NULL → use global config (settings.yaml)
3. If global empty → hardcoded defaults

**Example Logic** (src/core/access_control_v2.py):

```python
def get_auto_grant_config(self, db: Session, gate_id: int) -> dict:
    """Get auto-grant configuration with fallback chain"""
    gate = db.query(Gate).filter(Gate.id == gate_id).first()
    
    # Load global defaults from config
    from src.config import settings
    global_config = settings.get('auto_grant', {})
    
    # Build config with fallback chain: gate → global → hardcoded
    config = {
        'enabled': (
            gate.auto_grant_enabled if gate.auto_grant_enabled is not None 
            else global_config.get('enabled', True)
        ),
        'duration_days': (
            gate.auto_grant_duration_days if gate.auto_grant_duration_days is not None
            else global_config.get('duration_days', 7)
        ),
        'inactivity_timeout_minutes': (
            gate.auto_grant_inactivity_timeout_minutes 
            if gate.auto_grant_inactivity_timeout_minutes is not None
            else global_config.get('inactivity_timeout_minutes', 60)
        ),
        'port_forwarding_allowed': (
            gate.auto_grant_port_forwarding
            if gate.auto_grant_port_forwarding is not None
            else global_config.get('port_forwarding_allowed', True)
        )
    }
    
    return config

def _create_auto_grant(self, db, user, server, protocol, now, source_ip, gate_id):
    """Create auto-grant using gate-specific configuration"""
    config = self.get_auto_grant_config(db, gate_id)
    
    if not config['enabled']:
        logger.warning(f"Auto-grant disabled for gate {gate_id}")
        return None
    
    auto_grant = AccessPolicy(
        user_id=user.id,
        target_server_id=server.id,
        protocol=protocol,
        port_forwarding_allowed=config['port_forwarding_allowed'],
        start_time=now,
        end_time=now + timedelta(days=config['duration_days']),
        inactivity_timeout_minutes=config['inactivity_timeout_minutes'],
        # ... rest of fields
    )
    
    return auto_grant
```

---

## Alternative: SystemConfig Table (Most Flexible)

**Create dedicated config table**:

```sql
CREATE TABLE system_config (
    id SERIAL PRIMARY KEY,
    category VARCHAR(50) NOT NULL,  -- 'auto_grant', 'auto_user', 'auto_server'
    key VARCHAR(100) NOT NULL,      -- 'enabled', 'duration_days', 'timeout_minutes'
    value TEXT,                     -- JSON or plain value
    gate_id INTEGER REFERENCES gates(id),  -- NULL = global
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by_user_id INTEGER REFERENCES users(id),
    UNIQUE(category, key, gate_id)
);

-- Examples:
INSERT INTO system_config (category, key, value, gate_id) VALUES
    ('auto_grant', 'enabled', 'true', NULL),  -- Global
    ('auto_grant', 'duration_days', '7', NULL),
    ('auto_grant', 'enabled', 'false', 5),  -- Gate 5 override
    ('auto_grant', 'duration_days', '1', 5);  -- Gate 5: 1 day only
```

**Pros**:
- Most flexible
- Hot-reloadable
- Audit trail (updated_by_user_id)
- Can add new settings without schema changes

**Cons**:
- More complex queries
- Overkill for simple use case

---

## Web UI Mock (Gate Configuration Page)

```
┌─────────────────────────────────────────────────────────────┐
│ Gate: gate-dmz (10.30.0.76)                                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Auto-Grant Configuration                                     │
│ ────────────────────────────────────────────────────────────│
│                                                              │
│ ☑ Enable Auto-Grant                                         │
│   Automatically create 7-day grants for first-time access   │
│                                                              │
│ Grant Duration: [7] days            [Use global: 7 days]    │
│ Inactivity Timeout: [30] minutes    [Use global: 60 min]    │
│                                                              │
│ Additional Permissions:                                      │
│ ☐ Port Forwarding Allowed           [Use global: ✓]         │
│                                                              │
│ [Reset to Global Defaults]  [Save Changes]                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Recommendation Summary

**Implement**: **Tier 1 (Global config.yaml) + Tier 2 (Per-gate DB columns)**

**Phase 1** (Immediate):
1. Add columns to `gates` table (auto_grant_enabled, duration_days, timeout_minutes, port_forwarding)
2. Update `_create_auto_grant()` to read config from gate
3. Fallback to hardcoded defaults if both NULL

**Phase 2** (Web UI):
1. Add "Auto-Grant Settings" section to gate edit page
2. Show current values (gate-specific or inherited)
3. Allow admins to override or reset to global

**Phase 3** (Global config):
1. Add `config/settings.yaml` with auto_grant section
2. Load config on Tower startup
3. Update fallback chain: gate → global config → hardcoded

**Benefits**:
- ✅ Editable per-gate (different policies for DMZ vs internal)
- ✅ Global defaults for consistency
- ✅ Hot-reloadable via Web UI
- ✅ Simple implementation (just DB columns)
- ✅ Audit trail via database updated_at
- ✅ Easy to extend (auto_user, auto_server in future)

---

## Migration Script

```sql
-- migration_v1_12_0_auto_grant_config.sql

-- Add auto-grant configuration columns to gates table
ALTER TABLE gates 
    ADD COLUMN auto_grant_enabled BOOLEAN DEFAULT NULL,
    ADD COLUMN auto_grant_duration_days INTEGER DEFAULT NULL,
    ADD COLUMN auto_grant_inactivity_timeout_minutes INTEGER DEFAULT NULL,
    ADD COLUMN auto_grant_port_forwarding BOOLEAN DEFAULT NULL;

-- Add indexes for common queries
CREATE INDEX idx_gates_auto_grant_enabled ON gates(auto_grant_enabled) WHERE auto_grant_enabled IS NOT NULL;

-- Comments for clarity
COMMENT ON COLUMN gates.auto_grant_enabled IS 'Enable auto-grant creation for this gate. NULL = inherit global config.';
COMMENT ON COLUMN gates.auto_grant_duration_days IS 'Auto-grant duration in days (default: 7). NULL = inherit global config.';
COMMENT ON COLUMN gates.auto_grant_inactivity_timeout_minutes IS 'Session inactivity timeout (default: 60). NULL = inherit global config.';
COMMENT ON COLUMN gates.auto_grant_port_forwarding IS 'Allow port forwarding in auto-grants. NULL = inherit global config.';

-- Example: Set DMZ gate to stricter policy
-- UPDATE gates SET 
--     auto_grant_duration_days = 1,
--     auto_grant_inactivity_timeout_minutes = 30,
--     auto_grant_port_forwarding = false
-- WHERE name = 'gate-dmz';
```

---

## Questions for Decision

1. **Scope preference**:
   - A) Per-gate configuration (recommended)
   - B) Global only (simpler but less flexible)
   - C) SystemConfig table (most flexible but complex)

2. **Default behavior**:
   - A) Auto-grant enabled by default (opt-out)
   - B) Auto-grant disabled by default (opt-in)

3. **Web UI priority**:
   - A) Implement immediately (Phase 1 + 2)
   - B) Start with DB columns, UI later

4. **Future auto-user/auto-server**:
   - A) Add columns now (auto_user_create_enabled, auto_server_create_enabled)
   - B) Wait until needed

Które podejście preferujesz?
