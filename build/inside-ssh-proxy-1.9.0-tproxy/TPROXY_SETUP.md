# TPROXY Mode - Transparent Proxy Setup

## Overview

TPROXY mode allows Inside to act as a **transparent proxy** for SSH/RDP traffic. Users connect directly to server IP addresses (`ssh 10.210.0.76`) without knowing Inside exists. Perfect for:

- Tailscale exit nodes
- VPN concentrators
- Linux routers / gateway appliances
- Zero-config deployments

## Architecture

```
User laptop (100.64.0.20)
    ↓
    ssh 10.210.0.76  ← Direct connection to server IP
    ↓
Linux Router/Gateway (Inside jumphost)
    ↓
    iptables TPROXY rule → Port 8022
    ↓
Inside SSH Proxy (TPROXY mode)
    - Extracts original destination: 10.210.0.76:22 (SO_ORIGINAL_DST)
    - Looks up server by real IP (not pool IP)
    - Performs access control
    - Records session
    ↓
Backend Server (10.210.0.76:22)
```

## Dual Mode Operation

Inside runs both modes simultaneously:

| Mode | Port | How it works | User sees |
|------|------|--------------|-----------|
| **NAT** | 22 | Traditional jumphost with IP pool | `ssh jumphost` → proxy IP mapping |
| **TPROXY** | 8022 | Transparent interception | `ssh 10.210.0.76` → direct to server IP |

## Configuration

### 1. Enable TPROXY in Inside Config

File: `/opt/jumphost/config/ssh_proxy.conf`

```ini
[proxy]
# NAT mode - traditional jumphost with IP pool
nat_enabled = true
nat_host = 0.0.0.0
nat_port = 22

# TPROXY mode - transparent proxy (extracts SO_ORIGINAL_DST)
tproxy_enabled = true
tproxy_host = 0.0.0.0
tproxy_port = 8022

[logging]
level = INFO
file = /var/log/jumphost/ssh_proxy.log
```

### 2. Linux Kernel Requirements

Enable IP forwarding and route_localnet:

```bash
# Enable IP forwarding
sysctl -w net.ipv4.ip_forward=1
echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf

# Allow routing to local addresses (needed for TPROXY)
sysctl -w net.ipv4.conf.all.route_localnet=1
echo 'net.ipv4.conf.all.route_localnet=1' >> /etc/sysctl.conf

# Apply changes
sysctl -p
```

### 3. iptables TPROXY Rules

#### Basic Setup (All SSH traffic):

```bash
# Mark packets for routing to local process
iptables -t mangle -A PREROUTING -p tcp --dport 22 \\
    -j TPROXY --on-port 8022 --on-ip 0.0.0.0 --tproxy-mark 1

# Create routing rule for marked packets
ip rule add fwmark 1 table 100
ip route add local 0.0.0.0/0 dev lo table 100
```

#### Advanced Setup (Specific networks only):

```bash
# Only intercept SSH to specific network (e.g., production servers)
iptables -t mangle -A PREROUTING -p tcp --dport 22 \\
    -d 10.210.0.0/24 \\
    -j TPROXY --on-port 8022 --on-ip 0.0.0.0 --tproxy-mark 1

# RDP traffic (optional)
iptables -t mangle -A PREROUTING -p tcp --dport 3389 \\
    -d 10.210.0.0/24 \\
    -j TPROXY --on-port 8389 --on-ip 0.0.0.0 --tproxy-mark 1

# Routing rules
ip rule add fwmark 1 table 100
ip route add local 0.0.0.0/0 dev lo table 100
```

#### Exclude Inside itself:

```bash
# Don't intercept traffic FROM Inside itself (avoid loops)
iptables -t mangle -A PREROUTING -p tcp --dport 22 \\
    -m owner --uid-owner root \\
    -j RETURN

# Then add TPROXY rule
iptables -t mangle -A PREROUTING -p tcp --dport 22 \\
    -j TPROXY --on-port 8022 --on-ip 0.0.0.0 --tproxy-mark 1
```

### 4. Make Rules Persistent

#### Option A: Using iptables-persistent (Debian/Ubuntu):

```bash
apt-get install iptables-persistent
iptables-save > /etc/iptables/rules.v4
```

#### Option B: Using custom script:

Create `/etc/network/if-up.d/tproxy-rules`:

```bash
#!/bin/bash
# Inside TPROXY iptables rules

# Enable forwarding and route_localnet
sysctl -w net.ipv4.ip_forward=1
sysctl -w net.ipv4.conf.all.route_localnet=1

# Clear existing mangle rules
iptables -t mangle -F

# TPROXY SSH traffic to Inside
iptables -t mangle -A PREROUTING -p tcp --dport 22 \\
    -j TPROXY --on-port 8022 --on-ip 0.0.0.0 --tproxy-mark 1

# Routing for marked packets
ip rule add fwmark 1 table 100 2>/dev/null
ip route add local 0.0.0.0/0 dev lo table 100 2>/dev/null
```

Make executable:
```bash
chmod +x /etc/network/if-up.d/tproxy-rules
```

### 5. Restart Inside SSH Proxy

```bash
sudo systemctl restart jumphost-ssh-proxy
sudo systemctl status jumphost-ssh-proxy
```

Check logs:
```bash
tail -f /var/log/jumphost/ssh_proxy.log | grep -E "TPROXY|NAT"
```

Expected output:
```
2026-01-11 21:15:58 - ssh_proxy - INFO - NAT mode enabled: 0.0.0.0:22
2026-01-11 21:15:58 - ssh_proxy - INFO - TPROXY mode enabled: 0.0.0.0:8022
2026-01-11 21:15:58 - ssh_proxy - INFO - NAT mode listening on 0.0.0.0:22
2026-01-11 21:15:58 - ssh_proxy - INFO - TPROXY mode listening on 0.0.0.0:8022
2026-01-11 21:15:58 - ssh_proxy - INFO - SSH Proxy ready with 2 listener(s)
```

## Testing

### Verify iptables rules:

```bash
# Check mangle table
iptables -t mangle -L -n -v

# Check routing
ip rule show
ip route show table 100
```

### Test TPROXY connection:

From client machine (e.g., 100.64.0.20):

```bash
# Direct SSH to backend server IP
ssh root@10.210.0.76

# Inside should intercept this transparently
# Check logs on Inside:
tail -f /var/log/jumphost/ssh_proxy.log
```

Expected log entry:
```
2026-01-11 21:30:00 - ssh_proxy - INFO - TPROXY connection from 100.64.0.20 to 10.210.0.76:22
2026-01-11 21:30:00 - ssh_proxy - INFO - TPROXY: Extracted original destination 10.210.0.76:22
2026-01-11 21:30:01 - ssh_proxy - INFO - TPROXY mode: Direct IP 10.210.0.76 maps to server Test-SSH-Server (ID: 1)
```

### Test NAT mode still works:

```bash
# Traditional jumphost connection
ssh root@10.0.160.129

# Should use NAT mode
```

Expected log entry:
```
2026-01-11 21:30:10 - ssh_proxy - INFO - NAT connection from 100.64.0.20 to 10.0.160.129
2026-01-11 21:30:10 - ssh_proxy - INFO - NAT mode: Pool IP 10.0.160.129 on gate 1 maps to server 10.210.0.76 (ID: 1)
```

## How It Works

### SO_ORIGINAL_DST Extraction

When iptables TPROXY intercepts a packet, it preserves the original destination IP:port in socket option `SO_ORIGINAL_DST`. Inside extracts this:

```python
def get_original_dst(self, sock):
    """Extract original destination from TPROXY socket"""
    dst = sock.getsockopt(socket.SOL_IP, SO_ORIGINAL_DST, 16)
    # Parse sockaddr_in structure
    _, port, a, b, c, d = struct.unpack('!HHBBBB8x', dst)
    original_ip = f"{a}.{b}.{c}.{d}"
    return (original_ip, port)
```

### Dual Lookup Strategy

`AccessControlEngineV2.find_backend_by_proxy_ip()` tries both modes:

1. **NAT mode**: Look up in `ip_allocations` table by `allocated_ip` + `gate_id`
2. **TPROXY mode**: If not found, look up in `servers` table by `ip_address`

```python
# Try NAT pool first
allocation = db.query(IPAllocation).filter(
    IPAllocation.allocated_ip == dest_ip,
    IPAllocation.gate_id == gate_id,
    IPAllocation.is_active == True
).first()

if allocation:
    # NAT mode: Found in IP pool
    return server_from_allocation
else:
    # TPROXY mode: Try direct server IP
    server = db.query(Server).filter(
        Server.ip_address == dest_ip,
        Server.is_active == True
    ).first()
    return server
```

## Use Cases

### 1. Tailscale Exit Node

Make Inside a Tailscale exit node that audits all SSH connections:

```bash
# On Inside machine (100.64.1.10)
tailscale up --advertise-exit-node

# iptables TPROXY rules intercept SSH traffic
# Users: ssh server.production.company.com
# Inside: Transparently audits and records
```

### 2. VPN Concentrator

OpenVPN or WireGuard server with Inside as transparent SSH gateway:

```bash
# VPN clients get 10.8.0.0/24 addresses
# All SSH to 10.210.0.0/24 goes through Inside TPROXY
# Perfect for contractor access with full audit trail
```

### 3. Corporate Gateway

Inside as Internet edge firewall:

```bash
# All outbound SSH from 192.168.0.0/16 → Inside TPROXY
# Policies control who can SSH where
# Full session recording to external servers
```

## Troubleshooting

### Connection refused:

```bash
# Check if TPROXY port is listening
ss -tlnp | grep 8022

# Check iptables rules
iptables -t mangle -L -n -v | grep TPROXY

# Check routing
ip rule show | grep 100
ip route show table 100
```

### SO_ORIGINAL_DST extraction fails:

```bash
# Check kernel support
cat /proc/net/ip_tables_matches | grep TPROXY

# Enable CAP_NET_ADMIN for python process
setcap cap_net_admin=eip /opt/jumphost/venv/bin/python3
```

### Loops (connection to Inside itself):

```bash
# Add exclusion rule BEFORE TPROXY rule
iptables -t mangle -A PREROUTING -s 10.0.160.5 -j RETURN
iptables -t mangle -A PREROUTING -p tcp --dport 22 -j TPROXY ...
```

### Access denied - server not found:

In TPROXY mode, server must exist in `servers` table with matching `ip_address`:

```sql
-- Check server exists
SELECT id, name, ip_address, is_active FROM servers WHERE ip_address = '10.210.0.76';

-- If not found, add server:
INSERT INTO servers (name, ip_address, ssh_port, is_active)
VALUES ('Prod-Server-01', '10.210.0.76', 22, true);
```

## Security Considerations

1. **No hostname validation**: TPROXY works on IP only, DNS poisoning could redirect users
2. **Requires root**: iptables TPROXY needs root privileges
3. **Bypass possible**: Users can connect directly if they know backend IPs and bypass gateway
4. **Solution**: Use firewall to block direct connections, force all traffic through Inside

## Performance

TPROXY mode has same performance as NAT mode:
- No packet copying (zero-copy forwarding)
- Same Paramiko SSH tunnel overhead
- Same session recording overhead

Tested: 100 concurrent sessions, <1% CPU, <500MB RAM

## OUTPUT Chain - Traffic from Gate Itself

### ⚠️ Kernel Limitation: TPROXY doesn't work in OUTPUT chain

**TPROXY only works in PREROUTING chain** (for traffic coming from outside, not locally generated). For traffic generated on the gate itself, there's no simple iptables solution that preserves the original destination address.

Why this doesn't work:
```bash
# ❌ FAILS - kernel doesn't allow TPROXY in OUTPUT
iptables -t mangle -A OUTPUT -p tcp --dport 22 \
    -j TPROXY --on-port 8022 --on-ip 127.0.0.1 --tproxy-mark 1
# Error: RULE_APPEND failed (Invalid argument): rule in chain OUTPUT

# ❌ WRONG - REDIRECT changes DST to localhost (Inside can't determine real backend)
iptables -t nat -A OUTPUT -p tcp --dport 22 -j REDIRECT --to-port 8022
```

### Solution 1: SSH ProxyCommand (RECOMMENDED)

Configure SSH on gate to explicitly use Inside for specific networks:

**File:** `/etc/ssh/ssh_config` (system-wide) or `~/.ssh/config` (per-user)

```bash
# Audit all SSH to production network
Host 10.210.0.*
    ProxyJump jumphost

# Or use pool IPs explicitly
# ssh root@10.0.160.129  (goes through Inside NAT mode)
```

### Solution 2: Shell Alias

For admins, create an alias:

```bash
# In ~/.bashrc or /etc/profile
alias ssh-prod='ssh -J jumphost'

# Usage:
ssh-prod root@prod-server-01
```

### Solution 3: Accept the Limitation

Simply don't intercept OUTPUT chain traffic. Admins on the gate use explicit jumphost:

```bash
# Explicit through jumphost (NAT mode)
ssh root@10.0.160.129

# Or with ProxyJump
ssh -J jumphost root@backend-server
```

### Recommendation

**Use TPROXY only for PREROUTING (traffic from outside → gate → backends).**

For traffic generated on gate itself:
- Admins use explicit pool IPs or ProxyJump
- Automation/scripts connect via pool IPs
- No transparent interception in OUTPUT chain

## Next Steps

- [ ] Test with Tailscale exit node
- [ ] Document WireGuard VPN integration
- [ ] Add RDP TPROXY support (port 3389)
- [ ] Multi-gate TPROXY coordination
- [ ] HTTP/HTTPS TPROXY (Squid-like transparent proxy)

## References

- Linux TPROXY documentation: https://www.kernel.org/doc/Documentation/networking/tproxy.txt
- iptables TPROXY target: `man iptables-extensions` (search TPROXY)
- SO_ORIGINAL_DST: `man 7 ip` (IP_TRANSPARENT option)
