# Inside SSH Proxy - Standalone Package Quick Start

## 📦 Package Contents

- **Embedded Python venv** - all dependencies included, no system packages needed
- **SSH Proxy with TPROXY** - transparent proxy support for Tailscale/VPN gateways
- **Tower API integration** - access control, session recording, auditing
- **Systemd service** - automatic startup and management
- **Configuration template** - single config file for all settings

## 🚀 Installation (5 minutes)

### Step 1: Extract Package

```bash
tar xzf inside-ssh-proxy-1.9.0-tproxy.tar.gz
cd inside-ssh-proxy-1.9.0-tproxy/
```

### Step 2: Install

```bash
sudo ./install.sh
```

This will:
- Copy files to `/opt/inside-ssh-proxy/`
- Create directories `/var/log/inside/` and `/var/lib/inside-gate/`
- Install systemd service

### Step 3: Configure

Edit the configuration file:

```bash
sudo nano /opt/inside-ssh-proxy/config/inside.conf
```

**Minimum required settings:**

```ini
[tower]
# Tower API URL (your Inside Tower server)
url = https://tower.yourcompany.com

# Gate API token (from Tower dashboard: Gates → View → API Token)
token = your-gate-api-token-here

[gate]
# Gate name (must match Tower database)
name = tailscale-gateway-01

# Gate hostname
hostname = tailscale.yourcompany.com

[proxy]
# TPROXY mode for transparent proxy
tproxy_enabled = true
tproxy_port = 8022

# NAT mode (traditional jumphost) - optional
nat_enabled = false
```

### Step 4: Start Service

```bash
sudo systemctl start inside-ssh-proxy
sudo systemctl enable inside-ssh-proxy  # Auto-start on boot
```

### Step 5: Verify

```bash
# Check service status
sudo systemctl status inside-ssh-proxy

# Check logs
sudo journalctl -u inside-ssh-proxy -f

# Verify ports listening
sudo ss -tlnp | grep 8022
```

Expected output:
```
● inside-ssh-proxy.service - Inside SSH Proxy (TPROXY Gateway)
   Active: active (running) since Sat 2026-01-11 21:00:00 CET
   
LISTEN 0  128  0.0.0.0:8022  0.0.0.0:*  users:(("python3",pid=1234))
```

### Step 6: Setup iptables TPROXY

See `TPROXY_SETUP.md` for complete iptables configuration.

**Quick example** (intercept all SSH traffic):

```bash
# Enable IP forwarding
sudo sysctl -w net.ipv4.ip_forward=1
sudo sysctl -w net.ipv4.conf.all.route_localnet=1

# TPROXY rule
sudo iptables -t mangle -A PREROUTING -p tcp --dport 22 \
    -j TPROXY --on-port 8022 --on-ip 0.0.0.0 --tproxy-mark 1

# Routing for marked packets
sudo ip rule add fwmark 1 table 100
sudo ip route add local 0.0.0.0/0 dev lo table 100
```

**Test:**

From client machine:
```bash
ssh root@10.210.0.76
```

This should be transparently intercepted by Inside, verified in logs:
```bash
sudo journalctl -u inside-ssh-proxy -f | grep TPROXY
```

## 📁 File Locations

| Path | Description |
|------|-------------|
| `/opt/inside-ssh-proxy/` | Installation directory |
| `/opt/inside-ssh-proxy/config/inside.conf` | Configuration file |
| `/opt/inside-ssh-proxy/bin/inside-ssh-proxy` | Launcher script |
| `/var/log/inside/ssh_proxy.log` | SSH proxy logs |
| `/var/lib/inside-gate/cache.db` | Offline mode cache |
| `/var/lib/inside-gate/recordings/` | Session recordings |
| `/etc/systemd/system/inside-ssh-proxy.service` | Systemd service |

## 🔧 Configuration Reference

### [proxy] - SSH Proxy Settings

```ini
[proxy]
# NAT mode - traditional jumphost with IP pool mapping
nat_enabled = false
nat_host = 0.0.0.0
nat_port = 22

# TPROXY mode - transparent proxy (extracts SO_ORIGINAL_DST)
tproxy_enabled = true
tproxy_host = 0.0.0.0
tproxy_port = 8022
```

### [tower] - Tower API Connection

```ini
[tower]
# Tower API URL (https://tower.company.com or http://localhost:5000)
url = https://tower.yourcompany.com

# Gate authentication token (from Tower dashboard)
token = abc123def456...

# Verify SSL certificate (false for self-signed in dev)
verify_ssl = true
```

### [gate] - Gate Identification

```ini
[gate]
# Gate name (must exist in Tower database)
name = gateway-prod-01

# Hostname (for display in Tower)
hostname = gateway.company.com

# Location description
location = AWS us-east-1

# Version
version = 1.9.0
```

### [logging] - Log Configuration

```ini
[logging]
# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
level = INFO

# Log file path
file = /var/log/inside/ssh_proxy.log

# Log rotation (bytes)
max_size = 10485760

# Number of backup files
backup_count = 5
```

## 🛠️ Management Commands

### Service Control

```bash
# Start service
sudo systemctl start inside-ssh-proxy

# Stop service
sudo systemctl stop inside-ssh-proxy

# Restart service
sudo systemctl restart inside-ssh-proxy

# Enable auto-start on boot
sudo systemctl enable inside-ssh-proxy

# Disable auto-start
sudo systemctl disable inside-ssh-proxy

# Check status
sudo systemctl status inside-ssh-proxy
```

### Logs

```bash
# Follow live logs
sudo journalctl -u inside-ssh-proxy -f

# View last 100 lines
sudo journalctl -u inside-ssh-proxy -n 100

# View logs for specific time range
sudo journalctl -u inside-ssh-proxy --since "1 hour ago"

# View raw log file
sudo tail -f /var/log/inside/ssh_proxy.log
```

### Debugging

```bash
# Test configuration (dry-run)
sudo /opt/inside-ssh-proxy/bin/inside-ssh-proxy --test-config

# Verbose logging
sudo systemctl stop inside-ssh-proxy
sudo /opt/inside-ssh-proxy/bin/inside-ssh-proxy --verbose

# Check connectivity to Tower
curl -H "Authorization: Bearer YOUR-TOKEN" https://tower.company.com/api/v1/gate/heartbeat
```

## 🔄 Updates

### Update Package

```bash
# Stop service
sudo systemctl stop inside-ssh-proxy

# Backup configuration
sudo cp /opt/inside-ssh-proxy/config/inside.conf /opt/inside.conf.backup

# Extract new package
tar xzf inside-ssh-proxy-X.X.X-tproxy.tar.gz
cd inside-ssh-proxy-X.X.X-tproxy/

# Install (will backup old installation)
sudo ./install.sh

# Restore configuration
sudo cp /opt/inside.conf.backup /opt/inside-ssh-proxy/config/inside.conf

# Restart service
sudo systemctl start inside-ssh-proxy
```

## 🗑️ Uninstall

```bash
cd /opt/inside-ssh-proxy/
sudo ./uninstall.sh
```

You'll be asked whether to keep configuration and logs.

## 🐛 Troubleshooting

### Service won't start

```bash
# Check logs
sudo journalctl -u inside-ssh-proxy -n 50

# Common issues:
# 1. Configuration file missing/invalid
sudo nano /opt/inside-ssh-proxy/config/inside.conf

# 2. Port already in use
sudo ss -tlnp | grep 8022

# 3. Permission denied
sudo chown -R root:root /opt/inside-ssh-proxy
```

### Can't connect to Tower

```bash
# Check Tower URL in config
grep "^url" /opt/inside-ssh-proxy/config/inside.conf

# Test connectivity
curl -I https://tower.company.com

# Check SSL verification setting if self-signed cert
# Set verify_ssl = false in [tower] section for dev/testing
```

### TPROXY not working

```bash
# Check iptables rules
sudo iptables -t mangle -L -n -v

# Check routing
sudo ip rule show | grep 100
sudo ip route show table 100

# Check kernel support
cat /proc/net/ip_tables_matches | grep TPROXY

# Enable route_localnet
sudo sysctl -w net.ipv4.conf.all.route_localnet=1
```

### Sessions not appearing in Tower

```bash
# Check Tower API token
grep "^token" /opt/inside-ssh-proxy/config/inside.conf

# Check gate exists in Tower database
# Tower dashboard → Gates → Should see your gate name

# Check logs for API errors
sudo journalctl -u inside-ssh-proxy | grep -i "tower\|api"
```

## 📚 Use Cases

### 1. Tailscale Exit Node

Make this gate a Tailscale exit node that audits all SSH:

```bash
# Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh

# Advertise as exit node
sudo tailscale up --advertise-exit-node

# Setup TPROXY to intercept SSH
sudo iptables -t mangle -A PREROUTING -p tcp --dport 22 \
    -j TPROXY --on-port 8022 --on-ip 0.0.0.0 --tproxy-mark 1
```

Users connecting via Tailscale will have all SSH audited transparently!

### 2. WireGuard VPN Gateway

VPN concentrator with transparent SSH auditing:

```bash
# WireGuard already configured (wg0 interface)
# Add TPROXY rule for VPN clients
sudo iptables -t mangle -A PREROUTING -i wg0 -p tcp --dport 22 \
    -j TPROXY --on-port 8022 --on-ip 0.0.0.0 --tproxy-mark 1
```

### 3. Corporate Internet Gateway

Edge firewall with SSH auditing:

```bash
# Intercept outbound SSH from internal network
sudo iptables -t mangle -A PREROUTING -s 192.168.0.0/16 -p tcp --dport 22 \
    -j TPROXY --on-port 8022 --on-ip 0.0.0.0 --tproxy-mark 1
```

## 🔗 Links

- **Full TPROXY Setup Guide**: `TPROXY_SETUP.md`
- **Tower Documentation**: https://tower.yourcompany.com/docs
- **Support**: support@yourcompany.com

## 📝 License

Copyright © 2026 Your Company. All rights reserved.
