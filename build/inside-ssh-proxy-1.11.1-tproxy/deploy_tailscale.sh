#!/bin/bash
# Quick deployment script for Tailscale exit gateway
# Run this on your Tailscale exit node after extracting the package

set -e

echo "=========================================="
echo "Inside SSH Proxy - Tailscale Deployment"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: This script must be run as root (sudo)"
    exit 1
fi

# Prompt for Tower details
echo "Please enter Tower API details:"
read -p "Tower URL (e.g., https://tower.company.com): " TOWER_URL
read -p "Gate API Token: " GATE_TOKEN
read -p "Gate Name (e.g., tailscale-exit-01): " GATE_NAME

# Install package
echo ""
echo "Installing Inside SSH Proxy..."
./install.sh

# Configure
echo ""
echo "Configuring..."
cat > /opt/inside-ssh-proxy/config/inside.conf << EOF
# Inside SSH Proxy - Standalone Configuration
# Tailscale Exit Gateway Deployment

[proxy]
# NAT mode disabled for transparent proxy deployment
nat_enabled = false
nat_host = 0.0.0.0
nat_port = 22

# TPROXY mode for transparent SSH interception
tproxy_enabled = true
tproxy_host = 0.0.0.0
tproxy_port = 8022

[tower]
url = ${TOWER_URL}
token = ${GATE_TOKEN}
verify_ssl = true

[gate]
name = ${GATE_NAME}
hostname = $(hostname -f)
location = Tailscale Exit Node
version = 1.9.0

cache_enabled = true
cache_ttl = 30
cache_path = /var/lib/inside-gate/cache.db

offline_mode_enabled = true
offline_cache_duration = 300

[heartbeat]
interval = 30
timeout = 10

[api]
timeout = 10
retry_attempts = 3
retry_backoff = 2.0

[logging]
level = INFO
file = /var/log/inside/ssh_proxy.log
max_size = 10485760
backup_count = 5

[advanced]
recording_path = /var/lib/inside-gate/recordings
host_key_path = /var/lib/inside-gate/ssh_host_key
max_sessions = 1000
session_timeout = 0
EOF

# Start service
echo ""
echo "Starting service..."
systemctl start inside-ssh-proxy
systemctl enable inside-ssh-proxy

# Setup iptables TPROXY
echo ""
read -p "Setup iptables TPROXY rules now? [Y/n] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    echo "Setting up iptables TPROXY..."
    
    # Enable IP forwarding
    sysctl -w net.ipv4.ip_forward=1
    sysctl -w net.ipv4.conf.all.route_localnet=1
    echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf
    echo 'net.ipv4.conf.all.route_localnet=1' >> /etc/sysctl.conf
    
    # TPROXY rule for SSH
    iptables -t mangle -A PREROUTING -p tcp --dport 22 \
        -j TPROXY --on-port 8022 --on-ip 0.0.0.0 --tproxy-mark 1
    
    # Routing for marked packets
    ip rule add fwmark 1 table 100 2>/dev/null || true
    ip route add local 0.0.0.0/0 dev lo table 100 2>/dev/null || true
    
    # Save iptables rules (if iptables-persistent available)
    if command -v netfilter-persistent &> /dev/null; then
        netfilter-persistent save
        echo "iptables rules saved with netfilter-persistent"
    else
        echo "WARNING: iptables-persistent not found. Rules will not persist after reboot."
        echo "Install with: apt-get install iptables-persistent"
    fi
fi

echo ""
echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo ""
echo "Service Status:"
systemctl status inside-ssh-proxy --no-pager | head -10
echo ""
echo "Listening Ports:"
ss -tlnp | grep 8022 || echo "WARNING: Port 8022 not listening!"
echo ""
echo "iptables TPROXY Rules:"
iptables -t mangle -L PREROUTING -n -v | grep TPROXY || echo "No TPROXY rules found"
echo ""
echo "Next Steps:"
echo "  1. Verify gate appears in Tower dashboard"
echo "  2. Test SSH connection: ssh user@backend-server-ip"
echo "  3. Check logs: journalctl -u inside-ssh-proxy -f"
echo ""
echo "Documentation:"
echo "  - Quick Start: QUICKSTART.md"
echo "  - TPROXY Setup: TPROXY_SETUP.md"
echo ""
