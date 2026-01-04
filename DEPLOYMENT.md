# Jumphost v1.0 - Deployment & Rollback Guide

## 📦 Milestone v1.0 Package Contents

**Date**: 2026-01-04  
**Version**: 1.0  
**Status**: Production Ready ✅

---

## 🗂️ Available Backups

### 1. Full Project Archive (with Git)
```
/opt/jumphost-v1.0-COMPLETE-20260104_121009.tar.gz (159KB)
```
- ✅ Complete source code
- ✅ Git repository with full history
- ✅ All documentation (README, MILESTONE, ROADMAP, etc.)
- ✅ Database migrations (Alembic)
- ✅ CLI tools
- ✅ Test scripts
- ❌ Excludes: venv, logs, __pycache__

### 2. Source Code Archive (without Git)
```
/opt/jumphost-v1.0-20260104_120754.tar.gz (145KB)
```
- ✅ Source code
- ✅ Documentation
- ❌ Excludes: .git, venv, logs

### 3. Modified External Dependency
```
/opt/jumphost/pyrdp_mitm_py_MODIFIED_v1.0_20260104.py (7.6KB)
```
- Modified file: `venv/lib/python3.13/site-packages/pyrdp/core/mitm.py`
- Changes: Access Control V2 integration with destination IP extraction

### 4. Working SSH Proxy Backup
```
/opt/jumphost/src/proxy/ssh_proxy.py.working_backup_20260104_113741 (21KB)
```
- Working version before any risky changes
- Includes: SSH login forwarding + agent forwarding fixes

---

## 🚀 Fresh Deployment

### Prerequisites
```bash
# System requirements
- Debian 13 (Trixie)
- Python 3.13+
- PostgreSQL 17+
- Network: 10.0.160.128/25 available
```

### Step 1: Extract Archive
```bash
cd /opt
sudo tar xzf jumphost-v1.0-COMPLETE-20260104_121009.tar.gz
cd jumphost
```

### Step 2: Setup Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install paramiko sqlalchemy psycopg2-binary alembic python-dotenv asciinema pyrdp
```

### Step 3: Restore Modified PyRDP
```bash
# Copy modified mitm.py to PyRDP installation
cp pyrdp_mitm_py_MODIFIED_v1.0_20260104.py \
   venv/lib/python3.13/site-packages/pyrdp/core/mitm.py
```

### Step 4: Database Setup
```bash
# Create database
sudo -u postgres createdb jumphost
sudo -u postgres createuser jumphost_user

# Configure credentials
cp .env.example .env
# Edit .env with database credentials

# Run migrations
source venv/bin/activate
alembic upgrade head
```

### Step 5: Start Services
```bash
# SSH Proxy
sudo python3 /opt/jumphost/src/proxy/ssh_proxy.py &

# RDP Proxy
sudo nohup ./venv/bin/pyrdp-mitm -a 0.0.0.0 -l 3389 \
  -o /var/log/jumphost/rdp_recordings 127.0.0.1 \
  > /var/log/jumphost/rdp_proxy.log 2>&1 &
```

### Step 6: Verify Services
```bash
# Check processes
ps auxwww | grep -E '(ssh_proxy|pyrdp-mitm)' | grep -v grep

# Check logs
tail -f /var/log/jumphost/rdp_proxy.log
tail -f /var/log/jumphost/ssh/*.log
```

---

## 🔄 Rollback Procedures

### Scenario 1: Rollback SSH Proxy Only
```bash
cd /opt/jumphost/src/proxy

# Kill current SSH proxy
sudo pkill -f ssh_proxy.py

# Restore backup
cp ssh_proxy.py.working_backup_20260104_113741 ssh_proxy.py

# Restart
sudo python3 ssh_proxy.py &
```

### Scenario 2: Rollback RDP Proxy Only
```bash
# Kill current RDP proxy
sudo pkill -f pyrdp-mitm

# Restore modified mitm.py
cd /opt/jumphost
cp pyrdp_mitm_py_MODIFIED_v1.0_20260104.py \
   venv/lib/python3.13/site-packages/pyrdp/core/mitm.py

# Restart
sudo nohup ./venv/bin/pyrdp-mitm -a 0.0.0.0 -l 3389 \
  -o /var/log/jumphost/rdp_recordings 127.0.0.1 \
  > /var/log/jumphost/rdp_proxy.log 2>&1 &
```

### Scenario 3: Full System Rollback
```bash
# Stop all services
sudo pkill -f ssh_proxy.py
sudo pkill -f pyrdp-mitm

# Backup current state (if needed)
cd /opt
sudo mv jumphost jumphost.BACKUP-$(date +%Y%m%d_%H%M%S)

# Restore from archive
sudo tar xzf jumphost-v1.0-COMPLETE-20260104_121009.tar.gz
cd jumphost

# Recreate venv and restore PyRDP modification
python3 -m venv venv
source venv/bin/activate
pip install paramiko sqlalchemy psycopg2-binary alembic python-dotenv asciinema pyrdp

cp pyrdp_mitm_py_MODIFIED_v1.0_20260104.py \
   venv/lib/python3.13/site-packages/pyrdp/core/mitm.py

# Database already exists, no need to recreate
# Start services (see Step 5 above)
```

### Scenario 4: Database Rollback
```bash
# Rollback to specific migration
cd /opt/jumphost
source venv/bin/activate
alembic downgrade <revision>  # e.g., alembic downgrade -1

# Or full rollback to base
alembic downgrade base

# Then upgrade to v1.0
alembic upgrade head
```

---

## 🔍 Verification Tests

### Test 1: SSH Connection
```bash
# From authorized source IP
ssh -A username@10.0.160.129

# Expected: Connects to backend, session recorded
# Log: /var/log/jumphost/ssh/session_*.json
```

### Test 2: RDP Connection
```bash
# Windows
mstsc /v:10.0.160.130

# Linux
xfreerdp /v:10.0.160.130 /u:Administrator

# Expected: Connects to backend, session recorded
# Log: /var/log/jumphost/rdp_recordings/replays/rdp_replay_*.pyrdp
```

### Test 3: Access Denial
```bash
# From unauthorized source IP
ssh username@10.0.160.129

# Expected: Connection denied with audit log
# Log: Check database audit_logs table
```

### Test 4: Check Database
```bash
psql jumphost -c "SELECT * FROM users;"
psql jumphost -c "SELECT * FROM user_source_ips;"
psql jumphost -c "SELECT * FROM access_policies;"
psql jumphost -c "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 10;"
```

---

## 📊 Git Repository Info

### View History
```bash
cd /opt/jumphost
git log --oneline --graph --all
```

### View Specific Release
```bash
git show v1.0
```

### Compare with Previous State
```bash
# Show all changes in v1.0
git diff <parent-commit> v1.0

# Show specific file changes
git show v1.0:src/proxy/ssh_proxy.py
```

### Create New Branch for Testing
```bash
git checkout -b testing-v1.1
# Make changes...
git add .
git commit -m "Testing new feature"

# Rollback to v1.0 if needed
git checkout master
```

---

## 🛠️ Troubleshooting

### SSH Proxy Not Starting
```bash
# Check if port 22 is available
sudo netstat -tlnp | grep :22

# Check logs
tail -50 /var/log/jumphost/ssh/*.log

# Check Python errors
sudo python3 /opt/jumphost/src/proxy/ssh_proxy.py
# (run in foreground to see errors)
```

### RDP Proxy Not Starting
```bash
# Check if port 3389 is available
sudo netstat -tlnp | grep :3389

# Check PyRDP logs
tail -50 /var/log/jumphost/rdp_proxy.log

# Verify PyRDP modification
diff /opt/jumphost/pyrdp_mitm_py_MODIFIED_v1.0_20260104.py \
     /opt/jumphost/venv/lib/python3.13/site-packages/pyrdp/core/mitm.py
```

### Database Connection Issues
```bash
# Test database connection
psql jumphost -c "SELECT version();"

# Check .env configuration
cat /opt/jumphost/.env

# Verify Alembic current version
cd /opt/jumphost
source venv/bin/activate
alembic current
# Should show: 8419b886bc6d (head)
```

### Access Control Not Working
```bash
# Check if user exists
psql jumphost -c "SELECT * FROM users WHERE username='<user>';"

# Check if source IP registered
psql jumphost -c "SELECT * FROM user_source_ips WHERE source_ip='<ip>';"

# Check if policy exists
psql jumphost -c "SELECT * FROM access_policies WHERE user_id=(SELECT id FROM users WHERE username='<user>');"

# Check IP allocations
psql jumphost -c "SELECT * FROM ip_allocations;"
```

---

## 📞 Support

**Contact**: p.mojski@ideosoftware.com  
**Emergency Rollback**: Use full system rollback (Scenario 3)  
**Documentation**: README.md, FLEXIBLE_ACCESS_CONTROL_V2.md, ROADMAP.md

---

## ✅ Checklist for Production Deployment

- [ ] System requirements met (Debian 13, Python 3.13, PostgreSQL 17)
- [ ] Network configuration (10.0.160.128/25 pool available)
- [ ] Archive extracted to /opt/jumphost
- [ ] Virtual environment created and dependencies installed
- [ ] Modified PyRDP file restored
- [ ] Database created and migrations applied
- [ ] .env configured with correct credentials
- [ ] SSH proxy started and listening on port 22
- [ ] RDP proxy started and listening on port 3389
- [ ] Test connections verified (authorized + denied)
- [ ] Session recording directories exist and writable
- [ ] Logs accessible and readable
- [ ] Audit logs working in database
- [ ] Backups stored safely for rollback

---

*Last Updated: 2026-01-04 12:10*
