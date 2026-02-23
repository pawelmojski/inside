#!/bin/bash
# Build standalone Inside Tower package for management console deployment
# This creates a self-contained package with embedded Python venv and all dependencies

set -e

VERSION="2.1.1"
BUILD_DIR="build/inside-tower-${VERSION}"
PACKAGE_NAME="inside-tower-${VERSION}.tar.gz"

echo "===================================="
echo "Inside Tower Standalone Builder"
echo "===================================="
echo "Version: ${VERSION}"
echo ""

# Clean previous build
if [ -d "build/inside-tower-${VERSION}" ]; then
    echo "Cleaning previous build..."
    rm -rf "build/inside-tower-${VERSION}"
fi

# Create build structure
echo "Creating build directory structure..."
mkdir -p "${BUILD_DIR}"/{bin,lib,src,config,systemd,scripts}

# Copy source code
echo "Copying source code..."
cp -r src/web "${BUILD_DIR}/src/"
cp -r src/core "${BUILD_DIR}/src/"
cp -r src/api "${BUILD_DIR}/src/"
cp -r src/proxy "${BUILD_DIR}/src/"

# Clean up backup files and __pycache__
find "${BUILD_DIR}/src" -name "*.backup*" -delete
find "${BUILD_DIR}/src" -name "*.working_backup*" -delete
find "${BUILD_DIR}/src" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Copy SAML configuration
echo "Copying SAML configuration..."
cp config/saml_config.py "${BUILD_DIR}/config/"

# Create requirements-tower.txt
echo "Creating requirements.txt..."
cp "requirements-tower.txt" "${BUILD_DIR}/requirements.txt"

# Copy configuration template
echo "Creating configuration template..."
cat > "${BUILD_DIR}/config/tower.conf" << 'EOF'
# Inside Tower Configuration
# =========================

[database]
# PostgreSQL connection URL
url = postgresql://tower_user:CHANGE_THIS_PASSWORD@localhost/inside_tower

[flask]
# Flask secret key - CHANGE THIS IN PRODUCTION!
# Generate with: python3 -c "import secrets; print(secrets.token_hex(32))"
secret_key = CHANGE_THIS_SECRET_KEY_BEFORE_PRODUCTION

# Debug mode (disable in production)
debug = false

[server]
# Flask development server settings (gunicorn overrides these)
host = 0.0.0.0
port = 5000

[socketio]
# CORS allowed origins for WebSocket connections
# Use * for development, restrict to specific domains in production
cors_allowed_origins = *

[logging]
# Logging configuration
level = INFO
file = /var/log/inside/tower/tower.log
EOF

# Create database initialization script
echo "Creating database initialization script..."
cat > "${BUILD_DIR}/scripts/init_database.py" << 'EOFPY'
#!/usr/bin/env python3
"""
Initialize Inside Tower database with schema and default admin user.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def main():
    print("=" * 60)
    print("Inside Tower - Database Initialization")
    print("=" * 60)
    print()
    
    try:
        from src.core.database import Base, engine, SessionLocal, User
        
        # Create all tables from SQLAlchemy models
        print("Creating database schema...")
        Base.metadata.create_all(bind=engine)
        print("✓ Database schema created successfully")
        print()
        
        # Check if admin user already exists
        db = SessionLocal()
        try:
            existing_admin = db.query(User).filter(User.username == 'admin').first()
            if existing_admin:
                print("⚠ Admin user already exists, skipping creation")
                return 0
            
            # Create default admin user
            # Note: This system uses SAML authentication (Azure AD)
            # The hardcoded admin/admin is only for initial setup/emergency access
            print("Creating default admin user...")
            
            admin = User(
                username='admin',
                email='admin@localhost',
                full_name='System Administrator',
                is_active=True,
                permission_level=0  # 0 = SuperAdmin
            )
            db.add(admin)
            db.commit()
            
            print("✓ Default admin user created")
            print()
            print("Default credentials (hardcoded in Flask auth.py):")
            print("  Username: admin")
            print("  Password: admin")
            print()
            print("⚠ NOTES:")
            print("  - This system uses SAML (Azure AD) for authentication")
            print("  - The admin/admin hardcoded credentials are for emergency access")
            print("  - Configure SAML in config/tower.conf for production use")
            
            return 0
            
        finally:
            db.close()
            
    except ImportError as e:
        print(f"✗ ERROR: Failed to import required modules: {e}")
        print()
        print("Make sure you're running this from the Tower installation directory")
        print("and that the virtual environment is activated.")
        return 1
        
    except Exception as e:
        print(f"✗ ERROR: Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
EOFPY

chmod +x "${BUILD_DIR}/scripts/init_database.py"

# Create wrapper launcher script
echo "Creating launcher script..."
cat > "${BUILD_DIR}/bin/inside-tower" << 'EOF'
#!/bin/bash
# Inside Tower Launcher (Gunicorn wrapper)

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

# Export BASE_DIR for application
export BASE_DIR="${BASE_DIR}"
export LOG_DIR="${LOG_DIR:-/var/log/inside/tower}"

# Add source to Python path
export PYTHONPATH="${BASE_DIR}:${PYTHONPATH}"

# Default config location
CONFIG_FILE="${CONFIG_FILE:-${BASE_DIR}/config/tower.conf}"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "ERROR: Configuration file not found: $CONFIG_FILE"
    echo "Please configure ${BASE_DIR}/config/tower.conf"
    exit 1
fi

# Export config path for Flask app
export TOWER_CONFIG="$CONFIG_FILE"

# Change to web directory
cd "${BASE_DIR}/src/web"

# Run with gunicorn (production WSGI server)
# Use geventwebsocket worker for Flask-SocketIO WebSocket support
exec "${BASE_DIR}/lib/venv/bin/gunicorn" \
    --bind 0.0.0.0:5000 \
    --workers 1 \
    --worker-class geventwebsocket.gunicorn.workers.GeventWebSocketWorker \
    --timeout 120 \
    --access-logfile /var/log/inside/tower/access.log \
    --error-logfile /var/log/inside/tower/error.log \
    --log-level info \
    "app:app"
EOF

chmod +x "${BUILD_DIR}/bin/inside-tower"

# Create systemd service file
echo "Creating systemd service..."
cat > "${BUILD_DIR}/systemd/inside-tower.service" << 'EOF'
[Unit]
Description=Inside Tower - Management Console
After=network.target postgresql.service
Wants=postgresql.service
Documentation=https://github.com/company/inside

[Service]
Type=simple
User=inside
Group=inside

# Working directory
WorkingDirectory=/opt/inside-tower/src/web

# Environment
Environment="BASE_DIR=/opt/inside-tower"
Environment="LOG_DIR=/var/log/inside/tower"
Environment="CONFIG_FILE=/opt/inside-tower/config/tower.conf"
Environment="PYTHONPATH=/opt/inside-tower"
Environment="DATABASE_URL=postgresql://DB_USER:DB_PASSWORD@localhost/inside_tower"

# Start command
ExecStart=/opt/inside-tower/bin/inside-tower

# Restart policy
Restart=on-failure
RestartSec=10s

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/inside/tower /var/lib/inside-tower

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=inside-tower

[Install]
WantedBy=multi-user.target
EOF

# Create installation script
echo "Creating install.sh..."
cat > "${BUILD_DIR}/install.sh" << 'EOFINSTALL'
#!/bin/bash
# Inside Tower Installation Script

set -e

# ============================================
# CONFIGURATION - Edit these variables
# ============================================
DB_USER="tower_user"
DB_PASSWORD="tower123"
DB_NAME="inside_tower"
ADMIN_USERNAME="admin"
ADMIN_PASSWORD="admin"
# ============================================

if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: This script must be run as root"
    exit 1
fi

echo "==========================================="
echo "Inside Tower Installation"
echo "==========================================="
echo ""
echo "Configuration:"
echo "  Database: ${DB_NAME}"
echo "  DB User: ${DB_USER}"
echo "  Admin: ${ADMIN_USERNAME}/${ADMIN_PASSWORD}"
echo ""

INSTALL_DIR="/opt/inside-tower"
CONFIG_DIR="${INSTALL_DIR}/config"
LOG_DIR="/var/log/inside/tower"
DATA_DIR="/var/lib/inside-tower"

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
REQUIRED_VERSION="3.9"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "ERROR: Python 3.9 or higher is required (found: $PYTHON_VERSION)"
    exit 1
fi
echo "✓ Python $PYTHON_VERSION detected"
echo ""

# Check PostgreSQL installation
echo "Checking PostgreSQL..."
if ! command -v psql &> /dev/null; then
    echo "PostgreSQL not found. Installing..."
    
    # Detect package manager
    if command -v apt-get &> /dev/null; then
        apt-get update
        apt-get install -y postgresql postgresql-contrib
    elif command -v yum &> /dev/null; then
        yum install -y postgresql-server postgresql-contrib
        postgresql-setup --initdb
        systemctl enable postgresql
        systemctl start postgresql
    else
        echo "ERROR: Unable to install PostgreSQL automatically."
        echo "Please install PostgreSQL manually and run this script again."
        exit 1
    fi
    
    echo "✓ PostgreSQL installed"
else
    echo "✓ PostgreSQL detected"
    
    # Check if PostgreSQL is running
    if ! systemctl is-active --quiet postgresql; then
        echo "Starting PostgreSQL..."
        systemctl start postgresql
    fi
fi
echo ""

# Setup PostgreSQL database
echo "Setting up PostgreSQL database..."
# Drop existing database and user if they exist
sudo -u postgres psql -c "DROP DATABASE IF EXISTS ${DB_NAME};" 2>/dev/null || true
sudo -u postgres psql -c "DROP USER IF EXISTS ${DB_USER};" 2>/dev/null || true

# Create new user and database
sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';"
sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"
echo "✓ Database created: ${DB_NAME}"
echo ""

# Check if installation directory exists
if [ -d "$INSTALL_DIR" ]; then
    echo "Removing existing installation..."
    systemctl stop inside-tower 2>/dev/null || true
    rm -rf "$INSTALL_DIR"
fi

# Create system user
echo "Creating system user 'inside'..."
if ! id -u inside &>/dev/null; then
    useradd --system --home-dir "$INSTALL_DIR" --shell /bin/false inside
    echo "✓ User 'inside' created"
else
    echo "✓ User 'inside' already exists"
fi
echo ""

# Create directories
echo "Creating directories..."
mkdir -p "$LOG_DIR"
mkdir -p "$DATA_DIR"
mkdir -p "$DATA_DIR/recordings"
mkdir -p "$DATA_DIR/mp4_queue"
echo "✓ Directories created"
echo ""

# Copy files
echo "Installing files to $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
cp -r ./* "$INSTALL_DIR/"
echo "✓ Files installed"
echo ""

# Update configuration with database password
echo "Configuring database connection..."
sed -i "s|tower_user:CHANGE_THIS_PASSWORD|${DB_USER}:${DB_PASSWORD}|g" "${CONFIG_DIR}/tower.conf"

# Generate secret key
echo "Generating Flask secret key..."
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
sed -i "s|CHANGE_THIS_SECRET_KEY_BEFORE_PRODUCTION|${SECRET_KEY}|g" "${CONFIG_DIR}/tower.conf"
echo "✓ Configuration updated"
echo ""

# Create Python virtual environment
echo "Creating Python virtual environment..."
cd "$INSTALL_DIR"
python3 -m venv lib/venv
echo "✓ Virtual environment created"
echo ""

# Install Python dependencies
echo "Installing Python dependencies (this may take a few minutes)..."
"$INSTALL_DIR/lib/venv/bin/pip" install --upgrade pip setuptools wheel
"$INSTALL_DIR/lib/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
echo "✓ Dependencies installed"
echo ""

# Set permissions
echo "Setting permissions..."
chown -R inside:inside "$INSTALL_DIR"
chown -R inside:inside "$LOG_DIR"
chown -R inside:inside "$DATA_DIR"
chmod 750 "$INSTALL_DIR"
chmod 755 "$INSTALL_DIR/bin/inside-tower"
chmod 755 "$INSTALL_DIR/scripts/init_database.py"
echo "✓ Permissions set"
echo ""

# Initialize database
echo "Initializing database..."
export PYTHONPATH="$INSTALL_DIR"
export DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@localhost/${DB_NAME}"
export ADMIN_PASSWORD="${ADMIN_PASSWORD}"

sudo -u inside \
    PYTHONPATH="$INSTALL_DIR" \
    DATABASE_URL="$DATABASE_URL" \
    ADMIN_PASSWORD="${ADMIN_PASSWORD}" \
    "$INSTALL_DIR/lib/venv/bin/python3" \
    "$INSTALL_DIR/scripts/init_database.py"

echo ""

# Update systemd service with DATABASE_URL
echo "Installing systemd service..."
sed -i "s|DB_USER:DB_PASSWORD|${DB_USER}:${DB_PASSWORD}|g" "$INSTALL_DIR/systemd/inside-tower.service"
sed -i "s|inside_tower|${DB_NAME}|g" "$INSTALL_DIR/systemd/inside-tower.service"
cp "$INSTALL_DIR/systemd/inside-tower.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable inside-tower
echo "✓ Service installed"
echo ""

# Start service
echo "Starting Inside Tower..."
systemctl start inside-tower
echo ""

# Wait a moment for service to start
sleep 3

# Check service status
if systemctl is-active --quiet inside-tower; then
    echo "==========================================="
    echo "✓ Installation Complete!"
    echo "==========================================="
    echo ""
    echo "Inside Tower is running on port 5000"
    echo ""
    echo "Default credentials:"
    echo "  Username: ${ADMIN_USERNAME}"
    echo "  Password: ${ADMIN_PASSWORD}"
    echo ""
    echo "Service management:"
    echo "  systemctl status inside-tower"
    echo "  systemctl restart inside-tower"
    echo ""
    echo "Logs:"
    echo "  journalctl -u inside-tower -f"
    echo ""
else
    echo "==========================================="
    echo "⚠ Installation failed"
    echo "==========================================="
    echo ""
    echo "Check logs: journalctl -u inside-tower -n 50"
    echo ""
    exit 1
fi
EOFINSTALL

chmod +x "${BUILD_DIR}/install.sh"

# Create uninstall script
echo "Creating uninstall.sh..."
cat > "${BUILD_DIR}/uninstall.sh" << 'EOFUNINSTALL'
#!/bin/bash
# Inside Tower Uninstallation Script

set -e

if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: This script must be run as root"
    exit 1
fi

echo "==========================================="
echo "Inside Tower Uninstallation"
echo "==========================================="
echo ""

INSTALL_DIR="/opt/inside-tower"

# Stop and disable service
if systemctl is-active --quiet inside-tower; then
    echo "Stopping Inside Tower service..."
    systemctl stop inside-tower
fi

if systemctl is-enabled --quiet inside-tower 2>/dev/null; then
    echo "Disabling Inside Tower service..."
    systemctl disable inside-tower
fi

# Remove systemd service
if [ -f "/etc/systemd/system/inside-tower.service" ]; then
    echo "Removing systemd service..."
    rm /etc/systemd/system/inside-tower.service
    systemctl daemon-reload
fi

# Remove installation directory
if [ -d "$INSTALL_DIR" ]; then
    echo "Removing installation directory..."
    rm -rf "$INSTALL_DIR"
    echo "✓ Installation directory removed"
fi

echo ""
echo "==========================================="
echo "Uninstallation complete"
echo "==========================================="
echo ""
EOFUNINSTALL

chmod +x "${BUILD_DIR}/uninstall.sh"

# Create README
echo "Creating README..."
cat > "${BUILD_DIR}/README.md" << 'EOFREADME'
# Inside Tower - Standalone Package

This is a self-contained deployment package for Inside Tower management console.

## Requirements

- Linux (Ubuntu 20.04+, Debian 11+, RHEL 8+, or similar)
- Python 3.9 or higher
- PostgreSQL 12 or higher
- 1GB RAM minimum (2GB recommended)
- 10GB disk space

## Installation

1. **Install PostgreSQL** (if not already installed):
   ```bash
   # Ubuntu/Debian
   sudo apt install postgresql postgresql-contrib
   
   # RHEL/CentOS
   sudo yum install postgresql-server postgresql-contrib
   sudo postgresql-setup --initdb
   sudo systemctl enable postgresql
   sudo systemctl start postgresql
   ```

2. **Create database**:
   ```bash
   sudo -u postgres psql
   ```
   ```sql
   CREATE USER tower_user WITH PASSWORD 'your_secure_password';
   CREATE DATABASE inside_tower OWNER tower_user;
   \q
   ```

3. **Run installer**:
   ```bash
   sudo ./install.sh
   ```

4. **Access Tower**:
   - URL: http://your-server:5000
   - Username: admin
   - Password: admin

5. **Configure reverse proxy** (nginx/apache/haproxy) for HTTPS access

## Service Management

```bash
# Status
systemctl status inside-tower

# Start
systemctl start inside-tower

# Stop
systemctl stop inside-tower

# Restart
systemctl restart inside-tower

# Logs
journalctl -u inside-tower -f
tail -f /var/log/inside/tower/access.log
tail -f /var/log/inside/tower/error.log
```

## Configuration

Edit `/opt/inside-tower/config/tower.conf` and restart the service.

## Uninstallation

```bash
sudo ./uninstall.sh
```

## Support

For issues and documentation, see: https://github.com/company/inside
EOFREADME

# Create package tarball
echo ""
echo "Creating package archive..."
cd build
tar czf "${PACKAGE_NAME}" "inside-tower-${VERSION}"
cd ..

# Calculate package size
PACKAGE_SIZE=$(du -h "build/${PACKAGE_NAME}" | cut -f1)

echo ""
echo "==========================================="
echo "✓ Build Complete!"
echo "==========================================="
echo ""
echo "Package: build/${PACKAGE_NAME}"
echo "Size: ${PACKAGE_SIZE}"
echo ""
echo "To install on target system:"
echo "  1. Copy package to target: scp build/${PACKAGE_NAME} user@server:/tmp/"
echo "  2. Extract: tar xzf ${PACKAGE_NAME}"
echo "  3. Install: cd inside-tower-${VERSION} && sudo ./install.sh"
echo ""
