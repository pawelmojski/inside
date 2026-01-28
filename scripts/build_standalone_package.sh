#!/bin/bash
# Build standalone Inside SSH Proxy package for Tailscale/VPN gateway deployment
# This creates a self-contained package with embedded Python venv and all dependencies

set -e

VERSION="1.11.1-tproxy"
BUILD_DIR="build/inside-ssh-proxy-${VERSION}"
PACKAGE_NAME="inside-ssh-proxy-${VERSION}.tar.gz"

echo "===================================="
echo "Inside SSH Proxy Standalone Builder"
echo "===================================="
echo "Version: ${VERSION}"
echo ""

# Clean previous build
if [ -d "build" ]; then
    echo "Cleaning previous build..."
    rm -rf build
fi

# Create build structure
echo "Creating build directory structure..."
mkdir -p "${BUILD_DIR}"/{bin,lib,src,config,systemd}

# Copy source code
echo "Copying source code..."
cp -r src/proxy "${BUILD_DIR}/src/"
cp -r src/core "${BUILD_DIR}/src/"
cp -r src/gate "${BUILD_DIR}/src/"

# Clean up backup files
find "${BUILD_DIR}/src" -name "*.backup*" -delete
find "${BUILD_DIR}/src" -name "*.working_backup*" -delete
find "${BUILD_DIR}/src" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Copy Python requirements file
echo "Creating requirements.txt..."
cat > "${BUILD_DIR}/requirements.txt" << 'EOF'
paramiko>=4.0.0
cryptography>=46.0.0
sqlalchemy>=2.0.0
requests>=2.32.0
pytz>=2025.2
python-dotenv>=1.0.0
python-dateutil>=2.8.0
EOF

# Copy configuration
echo "Copying configuration template..."
cp config/ssh_proxy_standalone.conf "${BUILD_DIR}/config/inside.conf"

# NOTE: No pre-built venv - will be created during installation
# This avoids glibc and Python version compatibility issues

# Create wrapper script
echo "Creating launcher script..."
cat > "${BUILD_DIR}/bin/inside-ssh-proxy" << 'EOF'
#!/bin/bash
# Inside SSH Proxy Launcher

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

# Add source to Python path
export PYTHONPATH="${BASE_DIR}/src:${PYTHONPATH}"

# Default config location
CONFIG_FILE="${CONFIG_FILE:-${BASE_DIR}/config/inside.conf}"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "ERROR: Configuration file not found: $CONFIG_FILE"
    echo "Please copy config/inside.conf.example to config/inside.conf and configure it."
    exit 1
fi

# Set config environment variables for both ssh_proxy and gate config
export INSIDE_SSH_PROXY_CONFIG="$CONFIG_FILE"
export INSIDE_GATE_CONFIG="$CONFIG_FILE"

# Run SSH proxy with venv Python (NOT system python3!)
exec "${BASE_DIR}/lib/venv/bin/python3" "${BASE_DIR}/src/proxy/ssh_proxy.py" "$@"
EOF

chmod +x "${BUILD_DIR}/bin/inside-ssh-proxy"

# Create systemd service file
echo "Creating systemd service..."
cat > "${BUILD_DIR}/systemd/inside-ssh-proxy.service" << 'EOF'
[Unit]
Description=Inside SSH Proxy (TPROXY Gateway)
After=network.target
Documentation=https://github.com/company/inside

[Service]
Type=simple
User=root
Group=root

# Working directory
WorkingDirectory=/opt/inside-ssh-proxy

# Environment
Environment="CONFIG_FILE=/opt/inside-ssh-proxy/config/inside.conf"

# Start command
ExecStart=/opt/inside-ssh-proxy/bin/inside-ssh-proxy

# Restart policy
Restart=on-failure
RestartSec=5s

# Security hardening
NoNewPrivileges=false
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/inside /var/lib/inside-gate

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=inside-ssh-proxy

[Install]
WantedBy=multi-user.target
EOF

# Create installation script
echo "Creating install.sh..."
cat > "${BUILD_DIR}/install.sh" << 'EOF'
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
EOF

chmod +x "${BUILD_DIR}/install.sh"

# Create uninstall script
echo "Creating uninstall.sh..."
cat > "${BUILD_DIR}/uninstall.sh" << 'EOF'
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
EOF

chmod +x "${BUILD_DIR}/uninstall.sh"

# Copy documentation
echo "Copying documentation..."
cp TPROXY_SETUP.md "${BUILD_DIR}/"
cp QUICKSTART.md "${BUILD_DIR}/"
cp scripts/deploy_tailscale.sh "${BUILD_DIR}/"
chmod +x "${BUILD_DIR}/deploy_tailscale.sh"
cp README.md "${BUILD_DIR}/" 2>/dev/null || echo "No README.md found, skipping..."

# Create README for package
cat > "${BUILD_DIR}/README.txt" << 'EOF'
================================================================================
Inside SSH Proxy - Standalone Package
================================================================================

This is a standalone deployment package for Inside SSH Proxy, designed for
Tailscale exit nodes, VPN gateways, and transparent proxy deployments.

FEATURES:
  - TPROXY transparent proxy mode
  - Embedded Python virtual environment (no system dependencies)
  - Tower API integration for access control
  - Session recording and auditing
  - iptables TPROXY support

QUICK START:
  1. Extract package:
       tar xzf inside-ssh-proxy-*.tar.gz
       cd inside-ssh-proxy-*/

  2. Install:
       sudo ./install.sh

  3. Configure:
       sudo nano /opt/inside-ssh-proxy/config/inside.conf
       
       Required settings:
         [tower] url = http://your-tower-server:5000
         [tower] token = your-gate-api-token
         [gate] name = your-gate-name

  4. Start service:
       sudo systemctl start inside-ssh-proxy
       sudo systemctl enable inside-ssh-proxy

  5. Check status:
       sudo systemctl status inside-ssh-proxy
       sudo journalctl -u inside-ssh-proxy -f

  6. Setup iptables TPROXY (see TPROXY_SETUP.md):
       sudo iptables -t mangle -A PREROUTING -p tcp --dport 22 \
           -j TPROXY --on-port 8022 --on-ip 0.0.0.0 --tproxy-mark 1

SUPPORT:
  - Documentation: TPROXY_SETUP.md
  - Logs: /var/log/inside/ssh_proxy.log
  - Config: /opt/inside-ssh-proxy/config/inside.conf

================================================================================
EOF

# Create version file
echo "${VERSION}" > "${BUILD_DIR}/VERSION"

# Create tarball
echo ""
echo "Creating package..."
cd build
tar czf "../${PACKAGE_NAME}" "inside-ssh-proxy-${VERSION}"
cd ..

echo ""
echo "===================================="
echo "✅ Build complete!"
echo "===================================="
echo ""
echo "Package: ${PACKAGE_NAME}"
echo "Size: $(du -h "${PACKAGE_NAME}" | cut -f1)"
echo ""
echo "To deploy:"
echo "  1. Copy ${PACKAGE_NAME} to target server"
echo "  2. Extract: tar xzf ${PACKAGE_NAME}"
echo "  3. Install: cd inside-ssh-proxy-${VERSION} && sudo ./install.sh"
echo "  4. Configure: sudo nano /opt/inside-ssh-proxy/config/inside.conf"
echo "  5. Start: sudo systemctl start inside-ssh-proxy"
echo ""