# Inside SSH Proxy - Standalone Package

## 📦 Kompletna paczka dla Tailscale Exit Gateway

**Wersja:** 1.9.0-tproxy  
**Rozmiar:** 23MB  
**Plik:** `inside-ssh-proxy-1.9.0-tproxy.tar.gz`

### ✅ Co zawiera paczka?

- **Embedded Python venv** - wszystkie zależności (paramiko, sqlalchemy, pytz, cryptography)
- **SSH Proxy z TPROXY** - transparent proxy dla Tailscale/VPN
- **Tower API integration** - kontrola dostępu, nagrywanie sesji
- **Systemd service** - auto-start, zarządzanie
- **Unified config** - jeden plik konfiguracyjny (`inside.conf`)
- **Dokumentacja** - QUICKSTART.md, TPROXY_SETUP.md
- **Deployment script** - automatyczna instalacja dla Tailscale

### 🚀 Szybka instalacja (3 minuty)

```bash
# 1. Skopiuj paczkę na Tailscale gateway
scp inside-ssh-proxy-1.9.0-tproxy.tar.gz root@gateway:~

# 2. Zaloguj się i rozpakuj
ssh root@gateway
tar xzf inside-ssh-proxy-1.9.0-tproxy.tar.gz
cd inside-ssh-proxy-1.9.0-tproxy/

# 3. Automatyczna instalacja z konfiguracją
sudo ./deploy_tailscale.sh

# Albo ręcznie:
sudo ./install.sh
sudo nano /opt/inside-ssh-proxy/config/inside.conf
sudo systemctl start inside-ssh-proxy
```

### 📝 Minimalna konfiguracja

Wystarczy edytować `/opt/inside-ssh-proxy/config/inside.conf`:

```ini
[tower]
url = https://tower.firma.pl
token = twoj-gate-api-token

[gate]
name = tailscale-gateway-01

[proxy]
tproxy_enabled = true
tproxy_port = 8022
```

### 🔧 iptables TPROXY

```bash
# Jedna komenda - transparent proxy dla SSH
sudo iptables -t mangle -A PREROUTING -p tcp --dport 22 \
    -j TPROXY --on-port 8022 --on-ip 0.0.0.0 --tproxy-mark 1

sudo ip rule add fwmark 1 table 100
sudo ip route add local 0.0.0.0/0 dev lo table 100
```

### 📂 Struktura po instalacji

```
/opt/inside-ssh-proxy/
├── bin/
│   └── inside-ssh-proxy          # Launcher
├── config/
│   └── inside.conf               # Konfiguracja (edytować!)
├── lib/venv/                     # Python + zależności
├── src/                          # Kod źródłowy
├── QUICKSTART.md                 # Quick start guide
├── TPROXY_SETUP.md               # TPROXY documentation
└── deploy_tailscale.sh           # Auto deployment

/var/log/inside/
└── ssh_proxy.log                 # Logi

/var/lib/inside-gate/
├── cache.db                      # Offline cache
└── recordings/                   # Nagrania sesji

/etc/systemd/system/
└── inside-ssh-proxy.service      # Systemd unit
```

### 🔍 Weryfikacja

```bash
# Status
sudo systemctl status inside-ssh-proxy

# Logi
sudo journalctl -u inside-ssh-proxy -f

# Port nasłuchuje
sudo ss -tlnp | grep 8022

# Gate w Tower
# Dashboard → Gates → Powinien być widoczny
```

### 📚 Dokumentacja

- **QUICKSTART.md** - pełny przewodnik instalacji
- **TPROXY_SETUP.md** - konfiguracja iptables, use cases, troubleshooting
- **deploy_tailscale.sh** - interaktywny skrypt instalacyjny

### 🎯 Use Case: Tailscale Exit Node

```bash
# 1. Zainstaluj Inside SSH Proxy (jak wyżej)

# 2. Włącz Tailscale exit node
sudo tailscale up --advertise-exit-node

# 3. Setup TPROXY (intercept SSH)
sudo iptables -t mangle -A PREROUTING -p tcp --dport 22 \
    -j TPROXY --on-port 8022 --on-ip 0.0.0.0 --tproxy-mark 1

# 4. Gotowe!
# Użytkownicy łączący się przez Tailscale będą mieli SSH audytowane
```

### 🔄 Update

```bash
# Backup config
sudo cp /opt/inside-ssh-proxy/config/inside.conf ~/inside.conf.backup

# Nowa wersja
tar xzf inside-ssh-proxy-X.X.X-tproxy.tar.gz
cd inside-ssh-proxy-X.X.X-tproxy/
sudo ./install.sh

# Restore config
sudo cp ~/inside.conf.backup /opt/inside-ssh-proxy/config/inside.conf
sudo systemctl restart inside-ssh-proxy
```

### 🗑️ Uninstall

```bash
cd /opt/inside-ssh-proxy/
sudo ./uninstall.sh
```

### 💡 Kluczowe features

✅ **Zero system dependencies** - embedded Python venv  
✅ **Unified config** - jeden plik dla proxy + Tower API  
✅ **TPROXY support** - transparent proxy bez NAT  
✅ **Systemd integration** - auto-start, logging  
✅ **Offline mode** - działa gdy Tower offline (cache)  
✅ **Session recording** - pełny audit trail  
✅ **Easy deployment** - rozpakowuję, konfiguruję, uruchamiam

---

**Built:** $(date)  
**Builder:** `/opt/jumphost/scripts/build_standalone_package.sh`
