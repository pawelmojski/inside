#!/bin/bash
# Inside SSH Proxy Installation Script

set -e

if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: This script must be run as root"
    exit 1
fi

INSTALL_DIR="/opt/inside-ssh-proxy"
CONFIG_DIR="/opt/inside-ssh-proxy/config"
LOG_DIR="/var/log/inside"
DATA_DIR="/var/lib/inside-gate"

echo "===================================="
echo "Inside SSH Proxy Installation"
echo "===================================="
echo ""

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 not found. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}' | cut -d. -f1-2)
echo "Detected Python: $PYTHON_VERSION"

# Create directories
echo "Creating directories..."
mkdir -p "$LOG_DIR"
mkdir -p "$DATA_DIR"
mkdir -p "$CONFIG_DIR"

# Copy files
echo "Installing to ${INSTALL_DIR}..."
if [ -d "$INSTALL_DIR" ]; then
    echo "WARNING: ${INSTALL_DIR} already exists. Backing up..."
    mv "$INSTALL_DIR" "${INSTALL_DIR}.backup.$(date +%s)"
fi

# Copy everything
cp -r . "$INSTALL_DIR"

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv "$INSTALL_DIR/lib/venv"

# Install dependencies
echo "Installing Python dependencies..."
"$INSTALL_DIR/lib/venv/bin/pip" install --upgrade pip wheel setuptools >/dev/null 2>&1
"$INSTALL_DIR/lib/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

echo "Dependencies installed:"
"$INSTALL_DIR/lib/venv/bin/pip" list | grep -E "(paramiko|sqlalchemy|cryptography|pytz|requests)" || true

# Set permissions
chown -R root:root "$INSTALL_DIR"
chmod +x "$INSTALL_DIR/bin/inside-ssh-proxy"
chmod 700 "$DATA_DIR"
chmod 755 "$LOG_DIR"

# Install systemd service
echo "Installing systemd service..."
cp "$INSTALL_DIR/systemd/inside-ssh-proxy.service" /etc/systemd/system/
systemctl daemon-reload

# Configuration check
if [ ! -f "$CONFIG_DIR/inside.conf" ]; then
    echo ""
    echo "===================================="
    echo "⚠️  CONFIGURATION REQUIRED"
    echo "===================================="
    echo ""
    echo "Please edit the configuration file:"
    echo "  $CONFIG_DIR/inside.conf"
    echo ""
    echo "Required settings:"
    echo "  1. [tower] url - Tower API URL"
    echo "  2. [tower] token - Your gate authentication token"
    echo "  3. [gate] name - Gate name (must match Tower)"
    echo ""
    echo "After configuration, start the service:"
    echo "  systemctl start inside-ssh-proxy"
    echo "  systemctl enable inside-ssh-proxy"
    echo ""
else
    echo ""
    echo "Configuration file already exists:"
    echo "  $CONFIG_DIR/inside.conf"
    echo ""
fi

echo "===================================="
echo "Installation complete!"
echo "===================================="
echo ""
echo "Next steps:"
echo "  1. Configure: nano $CONFIG_DIR/inside.conf"
echo "  2. Start: systemctl start inside-ssh-proxy"
echo "  3. Enable: systemctl enable inside-ssh-proxy"
echo "  4. Check logs: journalctl -u inside-ssh-proxy -f"
echo ""
echo "TPROXY iptables setup:"
echo "  See: $INSTALL_DIR/TPROXY_SETUP.md"
echo ""
