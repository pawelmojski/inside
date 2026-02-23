# Inside - Installation Guide

> **Version:** 2.1.2  
> **Date:** February 23, 2026  
> **Platform:** Debian/Ubuntu Linux

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Architecture](#architecture)
3. [Tower Installation (Management Server)](#tower-installation)
4. [Gate Installation (SSH/RDP Proxy)](#gate-installation)
5. [First User Configuration](#first-user-configuration)
6. [First Server Configuration](#first-server-configuration)
7. [Installation Verification](#installation-verification)
8. [Troubleshooting](#troubleshooting)

---

## System Requirements

### Tower (Management Server)

- **Operating System:** Debian 11/12 or Ubuntu 20.04/22.04
- **Python:** 3.9 or newer
- **Database:** PostgreSQL 12 or newer
- **RAM:** Minimum 2 GB
- **Disk Space:** Minimum 10 GB
- **Network:** Port 5000/tcp (HTTP/HTTPS)

### Gate (SSH/RDP Proxy)

- **Operating System:** Debian 11/12 or Ubuntu 20.04/22.04  
- **Python:** 3.9 or newer
- **RAM:** Minimum 1 GB
- **Disk Space:** Minimum 5 GB
- **Network:** 
  - Port 22/tcp (SSH proxy)
  - Port 3389/tcp (RDP proxy, optional)
  - IP address pool for NAT mode (e.g., 10-20 addresses)

---

## Architecture

Inside consists of two main components:

```
┌─────────────────────┐
│   Inside Tower      │  Port 5000 (Web GUI + API)
│  (Management)       │  PostgreSQL Database
└──────────┬──────────┘
           │ HTTP API
           │
┌──────────▼──────────┐
│   Inside Gate       │  Port 22 (SSH Proxy)
│   (SSH/RDP Proxy)   │  Port 3389 (RDP Proxy)
└──────────┬──────────┘
           │ SSH/RDP
           │
┌──────────▼──────────┐
│  Target servers     │
│  (SSH/RDP servers)  │
└─────────────────────┘
```

**Operating Modes:**
- **NAT mode** - Gate uses an IP address pool to map servers (default, described in this guide)
- **TPROXY mode** - Transparent redirection without IP pool (requires additional configuration)

---

## Tower Installation

### Step 1: System Preparation

```bash
# Update system
apt update && apt upgrade -y

# Change SSH port to 2222 (free port 22 for Gate)
sed -i 's/#Port 22/Port 2222/' /etc/ssh/sshd_config
sed -i 's/^Port 22/Port 2222/' /etc/ssh/sshd_config
systemctl restart sshd

# WARNING: SSH now runs on port 2222
# Connect with: ssh -p 2222 user@host
```

### Step 2: IP Address Pool Configuration (NAT mode)

Gate requires an IP address pool to map servers in NAT mode. Number of addresses = number of target servers.

**Example:** Pool 10.21.37.150-170 (21 addresses)

```bash
# Find network interface name
ip addr show

# Add IP addresses to interface (example: eth0)
for ip in $(seq 150 170); do
    ip addr add 10.21.37.$ip/24 dev eth0
done

# Verification
ip addr show eth0 | grep 10.21.37

# To make changes persistent after reboot, add to /etc/network/interfaces:
cat >> /etc/network/interfaces << 'EOF'

# Inside Gate IP Pool
post-up for ip in $(seq 150 170); do ip addr add 10.21.37.$ip/24 dev eth0; done
EOF
```

### Step 3: Download and Install Tower

```bash
# Download Tower package
cd /tmp
wget https://init1.pl/inside/inside-tower-2.1.2.tar.gz

# Extract
tar -xzf inside-tower-2.1.2.tar.gz
cd inside-tower-2.1.2

# Run installer (as root)
./install.sh
```

**The installer automatically:**
- Installs PostgreSQL (if not present)
- Creates database `inside_tower`
- Creates system user `inside`
- Installs Tower in `/opt/inside-tower`
- Creates systemd service `inside-tower`
- Starts Tower on port 5000

### Step 4: Tower Verification

```bash
# Check service status
systemctl status inside-tower

# Check logs
journalctl -u inside-tower -f

# Check availability
curl http://localhost:5000
```

**Default credentials:**
- URL: `http://SERVER_IP:5000`
- Username: `admin`
- Password: `admin` (or value from `ADMIN_PASSWORD` in install.sh)

---

## Gate Installation

### Step 1: Gate Configuration in Tower GUI

1. **Login to Tower:**
   - Open browser: `http://SERVER_IP:5000`
   - Login: `admin` / `admin`

2. **Create Gate:**
   - Menu: **Gates** → **Add Gate**
   - Fill in the form:
     ```
     Name: gate01
     Hostname: SERVER_IP (e.g., 10.21.37.100)
     Network: 10.21.37.0/24
     IP Pool Start: 10.21.37.150
     IP Pool End: 10.21.37.170
     ```
   - Click **Add Gate**

3. **Save API Token:**
   - After creating Gate, an **API Token** will appear at the top of the page
   - **IMPORTANT:** Copy the token - it won't be displayed again!
   - Example: `aR9kF3mN7pQ2sT6vX8yZ1bD4gH5jL0wE`

### Step 2: Gate Installation

```bash
# Download Gate package
cd /tmp
wget https://init1.pl/inside/inside-gate-ssh-2.1.2.tar.gz

# Extract
tar -xzf inside-gate-ssh-2.1.2.tar.gz
cd inside-gate-ssh-2.1.2

# Run installer (as root)
./install.sh
```

### Step 3: API Token Configuration

```bash
# Edit Gate configuration
nano /opt/inside-gate/config/inside.conf

# Find line:
# token = CHANGE_THIS_TOKEN_TO_YOUR_GATE_API_TOKEN

# Change to your token:
token = aR9kF3mN7pQ2sT6vX8yZ1bD4gH5jL0wE

# Save (Ctrl+O) and exit (Ctrl+X)
```

### Step 4: Start Gate

```bash
# Start Gate service
systemctl start inside-gate-ssh

# Check status
systemctl status inside-gate-ssh

# Monitor logs
journalctl -u inside-gate-ssh -f
```

**Expected logs (correct configuration):**

```
Feb 23 23:59:03 hostname inside-gate-ssh[1234]: 2026-02-23 23:59:03,247 - ssh_proxy - INFO - Loading custom messages from Tower API
Feb 23 23:59:03 hostname inside-gate-ssh[1234]: 2026-02-23 23:59:03,279 - ssh_proxy - INFO - Custom messages loaded successfully (5 configured)
Feb 23 23:59:03 hostname inside-gate-ssh[1234]: 2026-02-23 23:59:03,446 - src.proxy.session_multiplexer - INFO - SessionMultiplexerRegistry initialized
Feb 23 23:59:03 hostname inside-gate-ssh[1234]: 2026-02-23 23:59:03,484 - src.proxy.lazy_relay_manager - INFO - LazyRelayManager initialized for gate gate01
Feb 23 23:59:03 hostname inside-gate-ssh[1234]: 2026-02-23 23:59:03,485 - ssh_proxy - INFO - Starting SSH Proxy Server
Feb 23 23:59:03 hostname inside-gate-ssh[1234]: 2026-02-23 23:59:03,487 - ssh_proxy - INFO - NAT mode listening on 0.0.0.0:22
Feb 23 23:59:03 hostname inside-gate-ssh[1234]: 2026-02-23 23:59:03,487 - ssh_proxy - INFO - SSH Proxy ready with 1 listener(s)
```

---

## First User Configuration

### Step 1: Add User (Person)

1. **Go to Tower GUI:**
   - Menu: **Persons** → **Add Person**

2. **Fill in the form:**
   ```
   Full Name: John Doe
   Username: j.doe
   Email: john.doe@example.com
   Source IP: 192.168.1.100 (client IP)
   ```

3. **Click "Create Person"**

### Step 2: Add Client IP Address

**Note:** Sometimes IP is not added automatically during user creation.

**If IP was not added:**

1. Go to **Persons** → click on user `j.doe`
2. Scroll down to **IP Addresses** section
3. Click **Add IP Address**
4. Fill in:
   ```
   IP Address: 192.168.1.100
   Description: John Doe Laptop
   ```
5. Click **Add IP**

### Step 3: User Verification

- Go to **Persons** → user list
- Check if user `j.doe` is visible
- Click on the user and verify IP `192.168.1.100` is assigned

---

## First Server Configuration

### Step 1: Add Server

1. **Go to Tower GUI:**
   - Menu: **Servers** → **Add Server**

2. **Fill in the form:**
   ```
   Name: prod-web-01
   Real IP Address: 10.50.20.10 (actual server IP)
   Protocol: SSH
   Port: 22
   Description: Production Web Server
   ```

3. **Checkboxes (leave default checked):**
   - ✓ Active
   - ✓ Auditing enabled

4. **Click "Add Server"**

### Step 2: Check Assigned Pool IP

After creating the server, Tower automatically assigns an IP from the Gate pool:

```
Server: prod-web-01
Real IP: 10.50.20.10
Pool IP: 10.21.37.150 (assigned from Gate pool)
```

**IMPORTANT:** In NAT mode, users connect to the pool IP (10.21.37.150), **not** to the real server IP (10.50.20.10).

**How to check assigned Pool IP:**
- Menu: **Servers** → click on `prod-web-01`
- See **Pool IP** or **NAT Address** field

---

## Access Policy Configuration

### Step 1: Create Access Policy

1. Menu: **Policies** → **Add Policy**
2. Fill in:
   ```
   Name: Allow j.doe to prod-web-01
   Persons: j.doe
   Servers: prod-web-01
   Grant Type: ALLOW
   ```
3. Click **Add Policy**

### Step 2: Test SSH Connection

```bash
# From user's computer (192.168.1.100)
ssh username@10.21.37.150

# Where:
# - username = SSH login on target server (prod-web-01)
# - 10.21.37.150 = pool IP assigned to server prod-web-01
```

**Authorization process:**
1. Client (192.168.1.100) connects to Gate (10.21.37.150:22)
2. Gate recognizes client IP → user `j.doe`
3. Gate checks in Tower if `j.doe` has access to `10.21.37.150`
4. Tower maps `10.21.37.150` → server `prod-web-01` (10.50.20.10)
5. Tower checks access policies
6. Gate establishes SSH connection to 10.50.20.10 and relays the session

---

## Installation Verification

### Service Check

```bash
# Tower
systemctl status inside-tower
curl http://localhost:5000/api/v1/health

# Gate
systemctl status inside-gate-ssh
ss -tlnp | grep :22
```

### Log Check

```bash
# Tower logs
journalctl -u inside-tower -n 50
tail -f /var/log/inside/tower/access.log
tail -f /var/log/inside/tower/error.log

# Gate logs
journalctl -u inside-gate-ssh -n 50
tail -f /var/log/inside/gate/ssh.log
```

### End-to-End Connection Test

1. **Check if Gate sees Tower:**
   ```bash
   journalctl -u inside-gate-ssh | grep "Tower API"
   # Should show: "Tower API connection successful"
   ```

2. **Check if Gate listens on port 22:**
   ```bash
   ss -tlnp | grep :22
   # Should show: python3 listening on 0.0.0.0:22
   ```

3. **SSH test from Gate perspective:**
   ```bash
   # On Gate server
   ssh -p 22 localhost
   # Should show Inside Gate banner
   ```

---

## Troubleshooting

### Problem: Tower doesn't start

**Symptoms:**
```bash
systemctl status inside-tower
# Status: failed
```

**Solution:**

```bash
# Check error logs
journalctl -u inside-tower -n 100

# Common causes:
# 1. PostgreSQL not running
systemctl status postgresql
systemctl start postgresql

# 2. Database connection error
# Check: /opt/inside-tower/config/tower.conf
grep database_url /opt/inside-tower/config/tower.conf

# 3. Port 5000 occupied
ss -tlnp | grep :5000
```

### Problem: Gate cannot connect to Tower

**Symptoms:**
```
journalctl -u inside-gate-ssh | grep ERROR
# ERROR: Failed to connect to Tower API
```

**Solution:**

```bash
# 1. Check if Tower is running
systemctl status inside-tower
curl http://localhost:5000

# 2. Check API token in Gate configuration
grep token /opt/inside-gate/config/inside.conf

# 3. Check Tower URL in Gate configuration
grep tower_url /opt/inside-gate/config/inside.conf
# Should be: tower_url = http://localhost:5000

# 4. Check in Tower GUI if Gate is active
# Menu: Gates → gate01 → Status: should be green
```

### Problem: Cannot connect via SSH

**Symptoms:**
```bash
ssh user@10.21.37.150
# Connection refused or timeout
```

**Solution:**

```bash
# 1. Check if Gate listens on port 22
ss -tlnp | grep :22

# 2. Check if IP 10.21.37.150 is in Gate pool
# Tower GUI: Gates → gate01 → IP Pool Range

# 3. Check if user has access policy
# Tower GUI: Policies → check for ALLOW policy for user and server

# 4. Check Gate logs during connection attempt
journalctl -u inside-gate-ssh -f
# Connect from another terminal and watch logs

# 5. Check if client source IP is added to user
# Tower GUI: Persons → user → IP Addresses
```

### Problem: SSH connects but disconnects immediately

**Symptoms:**
```bash
ssh user@10.21.37.150
# Connection closed by remote host
```

**Solution:**

```bash
# 1. Check if target server is reachable from Gate
# On Gate server:
ssh user@10.50.20.10  # real server IP
# If doesn't work - network issue, firewall, or routing problem

# 2. Check Gate logs for details
journalctl -u inside-gate-ssh | grep ERROR

# 3. Check if login/password are correct on target server

# 4. Check if Tower returns grant
# On Gate check logs:
journalctl -u inside-gate-ssh | grep "Access granted\|Access denied"
```

### Problem: Socket.IO returns 400 Bad Request

**Symptoms:**
- In browser console (F12): WebSocket 400 errors
- Live session view doesn't work

**Solution:**

```bash
# 1. Check worker class in gunicorn
ps aux | grep gunicorn | grep inside-tower
# Should contain: --worker-class geventwebsocket.gunicorn.workers.GeventWebSocketWorker

# 2. Check number of workers
# Should be 1 worker (without Redis message queue)
ps aux | grep gunicorn | grep inside-tower | wc -l
# Should show 2 (master + 1 worker)

# 3. Fix configuration
nano /opt/inside-tower/bin/inside-tower
# Find: --workers X
# Change to: --workers 1
# Find: --worker-class
# Should be: geventwebsocket.gunicorn.workers.GeventWebSocketWorker

# 4. Restart Tower
systemctl restart inside-tower
```

---

## Service Management

### Service Restart

```bash
# Tower
systemctl restart inside-tower

# Gate
systemctl restart inside-gate-ssh

# All Inside services
systemctl restart inside-tower inside-gate-ssh
```

### Enable/Disable Autostart

```bash
# Disable autostart
systemctl disable inside-tower
systemctl disable inside-gate-ssh

# Enable autostart
systemctl enable inside-tower
systemctl enable inside-gate-ssh
```

### Database Backup

```bash
# Create backup directory
mkdir -p /backup/inside

# Backup Tower database
sudo -u postgres pg_dump inside_tower > /backup/inside/tower_$(date +%Y%m%d_%H%M%S).sql

# Backup with compression
sudo -u postgres pg_dump inside_tower | gzip > /backup/inside/tower_$(date +%Y%m%d_%H%M%S).sql.gz

# Restore from backup
sudo -u postgres psql inside_tower < /backup/inside/tower_20260223_120000.sql

# Restore from gzip
gunzip -c /backup/inside/tower_20260223_120000.sql.gz | sudo -u postgres psql inside_tower
```

### Upgrade to Newer Version

```bash
# 1. Backup database
sudo -u postgres pg_dump inside_tower > /backup/inside/tower_before_upgrade_$(date +%Y%m%d).sql

# 2. Stop services
systemctl stop inside-tower inside-gate-ssh

# 3. Download new version
cd /tmp
wget https://init1.pl/inside/inside-tower-2.1.3.tar.gz
wget https://init1.pl/inside/inside-gate-ssh-2.1.3.tar.gz

# 4. Extract and run upgrade (Tower)
tar -xzf inside-tower-2.1.3.tar.gz
cd inside-tower-2.1.3
./upgrade.sh  # if available, otherwise ./install.sh

# 5. Extract and run upgrade (Gate)
cd /tmp
tar -xzf inside-gate-ssh-2.1.3.tar.gz
cd inside-gate-ssh-2.1.3
./upgrade.sh  # if available, otherwise ./install.sh

# 6. Start services
systemctl start inside-tower inside-gate-ssh

# 7. Check status
systemctl status inside-tower inside-gate-ssh
```

---

## Production Configuration

### HTTPS for Tower (Nginx reverse proxy)

```bash
# Install Nginx and Certbot
apt install nginx certbot python3-certbot-nginx

# Nginx configuration
cat > /etc/nginx/sites-available/inside-tower << 'EOF'
server {
    listen 80;
    server_name tower.example.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support for live sessions
    location /socket.io {
        proxy_pass http://localhost:5000/socket.io;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

# Activate configuration
ln -s /etc/nginx/sites-available/inside-tower /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx

# SSL Certificate (Let's Encrypt)
certbot --nginx -d tower.example.com
```

### Firewall (UFW)

```bash
# Enable UFW
ufw default deny incoming
ufw default allow outgoing

# Tower
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS (Tower)'
ufw allow 5000/tcp comment 'Inside Tower HTTP (direct)'

# Gate
ufw allow 22/tcp comment 'SSH (Inside Gate Proxy)'
ufw allow 3389/tcp comment 'RDP (Inside Gate Proxy)'

# Management SSH (changed port)
ufw allow 2222/tcp comment 'SSH Management'

# Activate firewall
ufw enable

# Check status
ufw status verbose
```

### Automatic Backup (cron)

```bash
# Create backup script
cat > /usr/local/bin/inside-backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backup/inside"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Backup database
sudo -u postgres pg_dump inside_tower | gzip > "$BACKUP_DIR/tower_$DATE.sql.gz"

# Remove backups older than 30 days
find "$BACKUP_DIR" -name "tower_*.sql.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR/tower_$DATE.sql.gz"
EOF

chmod +x /usr/local/bin/inside-backup.sh

# Add to crontab (daily at 2:00 AM)
crontab -e
# Add line:
0 2 * * * /usr/local/bin/inside-backup.sh >> /var/log/inside-backup.log 2>&1
```

---

## Frequently Asked Questions (FAQ)

### Can Tower and Gate be on different servers?

**Yes.** Tower and Gate can be on separate servers. In Gate configuration (`/opt/inside-gate/config/inside.conf`) set:

```ini
tower_url = http://TOWER_IP:5000
```

Ensure Gate has network access to Tower on port 5000.

### How to add more IP addresses to Gate pool?

1. Add IP addresses to interface:
   ```bash
   for ip in $(seq 171 200); do
       ip addr add 10.21.37.$ip/24 dev eth0
   done
   ```

2. Update pool in Tower GUI:
   - Gates → gate01 → Edit
   - Change **IP Pool End** to `10.21.37.200`

### Can I have multiple Gates connected to one Tower?

**Yes.** You can have multiple Gates (in different locations/networks) connected to one Tower. Each Gate has its unique API token and IP pool.

### How to change admin password?

**Option 1: Via GUI (recommended)**
1. Login as admin
2. Menu: Users → admin → Change Password

**Option 2: Via CLI**
```bash
cd /opt/inside-tower
sudo -u inside PYTHONPATH=/opt/inside-tower \
    DATABASE_URL="postgresql://tower_user:PASSWORD@localhost/inside_tower" \
    ./lib/venv/bin/python3 scripts/create_admin_user.py
```

### Where are session recordings stored?

SSH/RDP session recordings are stored in:
```
/var/log/inside/tower/recordings/YYYYMMDD/username_server_date_time.rec
```

You can replay them via Tower GUI: Sessions → session details → Play Recording

---

## Support and Documentation

- **Technical documentation:** [GitHub Wiki](https://github.com/company/inside/wiki)
- **Issues and bug reports:** [GitHub Issues](https://github.com/company/inside/issues)
- **Contact email:** support@example.com

---

## License

Inside © 2026 - Proprietary Software  
All rights reserved.
