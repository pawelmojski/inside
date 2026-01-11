#!/bin/bash
# Inside SSH Proxy Uninstallation Script

set -e

if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: This script must be run as root"
    exit 1
fi

INSTALL_DIR="/opt/inside-ssh-proxy"

echo "===================================="
echo "Inside SSH Proxy Uninstallation"
echo "===================================="
echo ""

# Stop service
if systemctl is-active --quiet inside-ssh-proxy; then
    echo "Stopping service..."
    systemctl stop inside-ssh-proxy
fi

# Disable service
if systemctl is-enabled --quiet inside-ssh-proxy 2>/dev/null; then
    echo "Disabling service..."
    systemctl disable inside-ssh-proxy
fi

# Remove systemd service
if [ -f /etc/systemd/system/inside-ssh-proxy.service ]; then
    echo "Removing systemd service..."
    rm /etc/systemd/system/inside-ssh-proxy.service
    systemctl daemon-reload
fi

# Remove installation directory
if [ -d "$INSTALL_DIR" ]; then
    echo "Removing installation directory..."
    read -p "Do you want to keep configuration and logs? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Keeping /var/log/inside and /var/lib/inside-gate"
    else
        echo "Removing logs and data..."
        rm -rf /var/log/inside
        rm -rf /var/lib/inside-gate
    fi
    
    rm -rf "$INSTALL_DIR"
fi

echo ""
echo "===================================="
echo "Uninstallation complete!"
echo "===================================="
