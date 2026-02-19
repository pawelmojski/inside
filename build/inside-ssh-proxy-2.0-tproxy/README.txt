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
