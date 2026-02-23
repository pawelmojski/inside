# Inside - Instrukcja Instalacji

> **Wersja:** 2.1.2  
> **Data:** 23 lutego 2026  
> **Platforma:** Debian/Ubuntu Linux

## Spis treści

1. [Wymagania systemowe](#wymagania-systemowe)
2. [Architektura](#architektura)
3. [Instalacja Tower (Serwer zarządzający)](#instalacja-tower)
4. [Instalacja Gate (Proxy SSH/RDP)](#instalacja-gate)
5. [Konfiguracja pierwszego użytkownika](#konfiguracja-pierwszego-użytkownika)
6. [Konfiguracja pierwszego serwera](#konfiguracja-pierwszego-serwera)
7. [Weryfikacja instalacji](#weryfikacja-instalacji)
8. [Rozwiązywanie problemów](#rozwiązywanie-problemów)

---

## Wymagania systemowe

### Tower (Serwer zarządzający)

- **System operacyjny:** Debian 11/12 lub Ubuntu 20.04/22.04
- **Python:** 3.9 lub nowszy
- **Baza danych:** PostgreSQL 12 lub nowszy
- **RAM:** Minimum 2 GB
- **Przestrzeń dyskowa:** Minimum 10 GB
- **Sieć:** Port 5000/tcp (HTTP/HTTPS)

### Gate (Proxy SSH/RDP)

- **System operacyjny:** Debian 11/12 lub Ubuntu 20.04/22.04  
- **Python:** 3.9 lub nowszy
- **RAM:** Minimum 1 GB
- **Przestrzeń dyskowa:** Minimum 5 GB
- **Sieć:** 
  - Port 22/tcp (SSH proxy)
  - Port 3389/tcp (RDP proxy, opcjonalnie)
  - Pula adresów IP dla NAT mode (np. 10-20 adresów)

---

## Architektura

Inside składa się z dwóch głównych komponentów:

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
│  Serwery docelowe   │
│  (SSH/RDP servers)  │
└─────────────────────┘
```

**Tryby pracy:**
- **NAT mode** - Gate używa puli adresów IP do mapowania serwerów (domyślnie, opisane w tej instrukcji)
- **TPROXY mode** - Transparentne przekierowanie bez puli IP (wymaga dodatkowej konfiguracji)

---

## Instalacja Tower

### Krok 1: Przygotowanie systemu

```bash
# Zaktualizuj system
apt update && apt upgrade -y

# Zmień port SSH na 2222 (uwolnienie portu 22 dla Gate)
sed -i 's/#Port 22/Port 2222/' /etc/ssh/sshd_config
sed -i 's/^Port 22/Port 2222/' /etc/ssh/sshd_config
systemctl restart sshd

# UWAGA: Od teraz SSH działa na porcie 2222
# Połącz się: ssh -p 2222 user@host
```

### Krok 2: Konfiguracja puli adresów IP (NAT mode)

Gate wymaga puli adresów IP do mapowania serwerów w trybie NAT. Liczba adresów = liczba serwerów docelowych.

**Przykład:** Pula 10.21.37.150-170 (21 adresów)

```bash
# Znajdź nazwę interfejsu sieciowego
ip addr show

# Dodaj adresy IP do interfejsu (przykład: eth0)
for ip in $(seq 150 170); do
    ip addr add 10.21.37.$ip/24 dev eth0
done

# Weryfikacja
ip addr show eth0 | grep 10.21.37

# Aby zmiany były trwałe po restarcie, dodaj do /etc/network/interfaces:
cat >> /etc/network/interfaces << 'EOF'

# Inside Gate IP Pool
post-up for ip in $(seq 150 170); do ip addr add 10.21.37.$ip/24 dev eth0; done
EOF
```

### Krok 3: Pobranie i instalacja Tower

```bash
# Pobierz paczkę Tower
cd /tmp
wget https://init1.pl/inside/inside-tower-2.1.2.tar.gz

# Rozpakuj
tar -xzf inside-tower-2.1.2.tar.gz
cd inside-tower-2.1.2

# Uruchom instalator (jako root)
./install.sh
```

**Instalator automatycznie:**
- Zainstaluje PostgreSQL (jeśli nie istnieje)
- Utworzy bazę danych `inside_tower`
- Utworzy użytkownika systemowego `inside`
- Zainstaluje Tower w `/opt/inside-tower`
- Utworzy usługę systemd `inside-tower`
- Uruchomi Tower na porcie 5000

### Krok 4: Weryfikacja Tower

```bash
# Sprawdź status usługi
systemctl status inside-tower

# Sprawdź logi
journalctl -u inside-tower -f

# Sprawdź dostępność
curl http://localhost:5000
```

**Domyślne dane logowania:**
- URL: `http://IP_SERWERA:5000`
- Username: `admin`
- Password: `admin` (lub wartość z `ADMIN_PASSWORD` w install.sh)

---

## Instalacja Gate

### Krok 1: Konfiguracja Gate w Tower GUI

1. **Zaloguj się do Tower:**
   - Otwórz przeglądarkę: `http://IP_SERWERA:5000`
   - Login: `admin` / `admin`

2. **Utwórz Gate:**
   - Menu: **Gates** → **Add Gate**
   - Wypełnij formularz:
     ```
     Name: gate01
     Hostname: IP_SERWERA (np. 10.21.37.100)
     Network: 10.21.37.0/24
     IP Pool Start: 10.21.37.150
     IP Pool End: 10.21.37.170
     ```
   - Kliknij **Add Gate**

3. **Zapisz API Token:**
   - Po utworzeniu Gate, u góry strony pojawi się **API Token**
   - **WAŻNE:** Skopiuj token - nie będzie ponownie wyświetlony!
   - Przykład: `aR9kF3mN7pQ2sT6vX8yZ1bD4gH5jL0wE`

### Krok 2: Instalacja Gate

```bash
# Pobierz paczkę Gate
cd /tmp
wget https://init1.pl/inside/inside-gate-ssh-2.1.2.tar.gz

# Rozpakuj
tar -xzf inside-gate-ssh-2.1.2.tar.gz
cd inside-gate-ssh-2.1.2

# Uruchom instalator (jako root)
./install.sh
```

### Krok 3: Konfiguracja API Token

```bash
# Edytuj konfigurację Gate
nano /opt/inside-gate/config/inside.conf

# Znajdź linię:
# token = CHANGE_THIS_TOKEN_TO_YOUR_GATE_API_TOKEN

# Zmień na swój token:
token = aR9kF3mN7pQ2sT6vX8yZ1bD4gH5jL0wE

# Zapisz (Ctrl+O) i wyjdź (Ctrl+X)
```

### Krok 4: Uruchomienie Gate

```bash
# Uruchom usługę Gate
systemctl start inside-gate-ssh

# Sprawdź status
systemctl status inside-gate-ssh

# Monitoruj logi
journalctl -u inside-gate-ssh -f
```

**Oczekiwane logi (poprawna konfiguracja):**

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

## Konfiguracja pierwszego użytkownika

### Krok 1: Dodanie użytkownika (Person)

1. **Przejdź do Tower GUI:**
   - Menu: **Persons** → **Add Person**

2. **Wypełnij formularz:**
   ```
   Full Name: Jan Kowalski
   Username: j.kowalski
   Email: jan.kowalski@example.com
   Source IP: 192.168.1.100 (IP klienta)
   ```

3. **Kliknij "Create Person"**

### Krok 2: Dodanie adresu IP klienta

**Uwaga:** Czasami IP nie jest dodawany automatycznie podczas tworzenia użytkownika.

**Jeśli IP nie zostało dodane:**

1. Przejdź do **Persons** → kliknij na użytkownika `j.kowalski`
2. Przewiń w dół do sekcji **IP Addresses**
3. Kliknij **Add IP Address**
4. Wypełnij:
   ```
   IP Address: 192.168.1.100
   Description: Laptop Jan Kowalski
   ```
5. Kliknij **Add IP**

### Krok 3: Weryfikacja użytkownika

- Przejdź do **Persons** → lista użytkowników
- Sprawdź czy użytkownik `j.kowalski` jest widoczny
- Kliknij na użytkownika i zweryfikuj czy ma przypisany IP `192.168.1.100`

---

## Konfiguracja pierwszego serwera

### Krok 1: Dodanie serwera

1. **Przejdź do Tower GUI:**
   - Menu: **Servers** → **Add Server**

2. **Wypełnij formularz:**
   ```
   Name: prod-web-01
   Real IP Address: 10.50.20.10 (rzeczywisty IP serwera)
   Protocol: SSH
   Port: 22
   Description: Production Web Server
   ```

3. **Checkboxy (pozostaw domyślnie zaznaczone):**
   - ✓ Active
   - ✓ Auditing enabled

4. **Kliknij "Add Server"**

### Krok 2: Sprawdzenie przydzielonego IP z puli

Po utworzeniu serwera, Tower automatycznie przydzieli mu adres IP z puli Gate:

```
Server: prod-web-01
Real IP: 10.50.20.10
Pool IP: 10.21.37.150 (przydzielony z puli Gate)
```

**WAŻNE:** W trybie NAT, użytkownicy łączą się na IP z puli (10.21.37.150), **nie** na rzeczywisty IP serwera (10.50.20.10).

**Jak sprawdzić przydzielony Pool IP:**
- Menu: **Servers** → kliknij na `prod-web-01`
- Zobacz pole **Pool IP** lub **NAT Address**

---

## Konfiguracja polityki dostępu

### Krok 1: Utwórz politykę dostępu

1. Menu: **Policies** → **Add Policy**
2. Wypełnij:
   ```
   Name: Allow j.kowalski to prod-web-01
   Persons: j.kowalski
   Servers: prod-web-01
   Grant Type: ALLOW
   ```
3. Kliknij **Add Policy**

### Krok 2: Testowe połączenie SSH

```bash
# Z komputera użytkownika (192.168.1.100)
ssh username@10.21.37.150

# Gdzie:
# - username = login SSH na serwerze docelowym (prod-web-01)
# - 10.21.37.150 = IP z puli przydzielony serwerowi prod-web-01
```

**Proces autoryzacji:**
1. Klient (192.168.1.100) łączy się z Gate (10.21.37.150:22)
2. Gate rozpoznaje IP klienta → użytkownik `j.kowalski`
3. Gate sprawdza w Tower czy `j.kowalski` ma dostęp do `10.21.37.150`
4. Tower mapuje `10.21.37.150` → serwer `prod-web-01` (10.50.20.10)
5. Tower sprawdza polityki dostępu
6. Gate nawiązuje połączenie SSH do 10.50.20.10 i przekazuje sesję użytkownikowi

---

## Weryfikacja instalacji

### Sprawdzenie usług

```bash
# Tower
systemctl status inside-tower
curl http://localhost:5000/api/v1/health

# Gate
systemctl status inside-gate-ssh
ss -tlnp | grep :22
```

### Sprawdzenie logów

```bash
# Tower logs
journalctl -u inside-tower -n 50
tail -f /var/log/inside/tower/access.log
tail -f /var/log/inside/tower/error.log

# Gate logs
journalctl -u inside-gate-ssh -n 50
tail -f /var/log/inside/gate/ssh.log
```

### Test połączenia end-to-end

1. **Sprawdź czy Gate widzi Tower:**
   ```bash
   journalctl -u inside-gate-ssh | grep "Tower API"
   # Powinno pokazać: "Tower API connection successful"
   ```

2. **Sprawdź czy Gate nasłuchuje na porcie 22:**
   ```bash
   ss -tlnp | grep :22
   # Powinno pokazać: python3 listening on 0.0.0.0:22
   ```

3. **Test SSH z perspektywy Gate:**
   ```bash
   # Na serwerze Gate
   ssh -p 22 localhost
   # Powinno pokazać banner Inside Gate
   ```

---

## Rozwiązywanie problemów

### Problem: Tower nie startuje

**Objawy:**
```bash
systemctl status inside-tower
# Status: failed
```

**Rozwiązanie:**

```bash
# Sprawdź logi błędów
journalctl -u inside-tower -n 100

# Typowe przyczyny:
# 1. PostgreSQL nie działa
systemctl status postgresql
systemctl start postgresql

# 2. Błąd połączenia z bazą danych
# Sprawdź: /opt/inside-tower/config/tower.conf
grep database_url /opt/inside-tower/config/tower.conf

# 3. Port 5000 zajęty
ss -tlnp | grep :5000
```

### Problem: Gate nie może połączyć się z Tower

**Objawy:**
```
journalctl -u inside-gate-ssh | grep ERROR
# ERROR: Failed to connect to Tower API
```

**Rozwiązanie:**

```bash
# 1. Sprawdź czy Tower działa
systemctl status inside-tower
curl http://localhost:5000

# 2. Sprawdź API token w konfiguracji Gate
grep token /opt/inside-gate/config/inside.conf

# 3. Sprawdź URL Tower w konfiguracji Gate
grep tower_url /opt/inside-gate/config/inside.conf
# Powinno być: tower_url = http://localhost:5000

# 4. Sprawdź w Tower GUI czy Gate jest aktywny
# Menu: Gates → gate01 → Status: powinien być zielony
```

### Problem: Nie można połączyć się przez SSH

**Objawy:**
```bash
ssh user@10.21.37.150
# Connection refused lub timeout
```

**Rozwiązanie:**

```bash
# 1. Sprawdź czy Gate nasłuchuje na porcie 22
ss -tlnp | grep :22

# 2. Sprawdź czy IP 10.21.37.150 jest w puli Gate
# Tower GUI: Gates → gate01 → IP Pool Range

# 3. Sprawdź czy użytkownik ma politykę dostępu
# Tower GUI: Policies → sprawdź czy istnieje ALLOW policy dla użytkownika i serwera

# 4. Sprawdź logi Gate przy próbie połączenia
journalctl -u inside-gate-ssh -f
# Połącz się z innego terminala i obserwuj logi

# 5. Sprawdź czy source IP klienta jest dodany do użytkownika
# Tower GUI: Persons → użytkownik → IP Addresses
```

### Problem: SSH loguje ale od razu rozłącza

**Objawy:**
```bash
ssh user@10.21.37.150
# Connection closed by remote host
```

**Rozwiązanie:**

```bash
# 1. Sprawdź czy serwer docelowy jest dostępny z Gate
# Na serwerze Gate:
ssh user@10.50.20.10  # rzeczywisty IP serwera
# Jeśli nie działa - problem sieciowy, firewall lub routing

# 2. Sprawdź logi Gate dla szczegółów
journalctl -u inside-gate-ssh | grep ERROR

# 3. Sprawdź czy login/hasło są poprawne na serwerze docelowym

# 4. Sprawdź czy Tower zwraca grant
# Na Gate sprawdź logi:
journalctl -u inside-gate-ssh | grep "Access granted\|Access denied"
```

### Problem: Socket.IO zwraca 400 Bad Request

**Objawy:**
- W przeglądarce (konsola F12): błędy WebSocket 400
- Live session view nie działa

**Rozwiązanie:**

```bash
# 1. Sprawdź worker class w gunicorn
ps aux | grep gunicorn | grep inside-tower
# Powinno zawierać: --worker-class geventwebsocket.gunicorn.workers.GeventWebSocketWorker

# 2. Sprawdź liczbę workers
# Powinien być 1 worker (bez Redis message queue)
ps aux | grep gunicorn | grep inside-tower | wc -l
# Powinno pokazać 2 (master + 1 worker)

# 3. Napraw konfigurację
nano /opt/inside-tower/bin/inside-tower
# Znajdź: --workers X
# Zmień na: --workers 1
# Znajdź: --worker-class
# Powinno być: geventwebsocket.gunicorn.workers.GeventWebSocketWorker

# 4. Restart Tower
systemctl restart inside-tower
```

---

## Zarządzanie usługami

### Restart usług

```bash
# Tower
systemctl restart inside-tower

# Gate
systemctl restart inside-gate-ssh

# Wszystkie usługi Inside
systemctl restart inside-tower inside-gate-ssh
```

### Wyłączenie/włączenie autostartu

```bash
# Wyłącz autostart
systemctl disable inside-tower
systemctl disable inside-gate-ssh

# Włącz autostart
systemctl enable inside-tower
systemctl enable inside-gate-ssh
```

### Backup bazy danych

```bash
# Utwórz katalog backup
mkdir -p /backup/inside

# Backup Tower database
sudo -u postgres pg_dump inside_tower > /backup/inside/tower_$(date +%Y%m%d_%H%M%S).sql

# Backup z kompresją
sudo -u postgres pg_dump inside_tower | gzip > /backup/inside/tower_$(date +%Y%m%d_%H%M%S).sql.gz

# Restore z backup
sudo -u postgres psql inside_tower < /backup/inside/tower_20260223_120000.sql

# Restore z gzip
gunzip -c /backup/inside/tower_20260223_120000.sql.gz | sudo -u postgres psql inside_tower
```

### Upgrade do nowszej wersji

```bash
# 1. Backup bazy danych
sudo -u postgres pg_dump inside_tower > /backup/inside/tower_before_upgrade_$(date +%Y%m%d).sql

# 2. Zatrzymaj usługi
systemctl stop inside-tower inside-gate-ssh

# 3. Pobierz nową wersję
cd /tmp
wget https://init1.pl/inside/inside-tower-2.1.3.tar.gz
wget https://init1.pl/inside/inside-gate-ssh-2.1.3.tar.gz

# 4. Rozpakuj i uruchom upgrade (Tower)
tar -xzf inside-tower-2.1.3.tar.gz
cd inside-tower-2.1.3
./upgrade.sh  # jeśli dostępny, w przeciwnym razie ./install.sh

# 5. Rozpakuj i uruchom upgrade (Gate)
cd /tmp
tar -xzf inside-gate-ssh-2.1.3.tar.gz
cd inside-gate-ssh-2.1.3
./upgrade.sh  # jeśli dostępny, w przeciwnym razie ./install.sh

# 6. Uruchom usługi
systemctl start inside-tower inside-gate-ssh

# 7. Sprawdź status
systemctl status inside-tower inside-gate-ssh
```

---

## Konfiguracja produkcyjna

### HTTPS dla Tower (Nginx reverse proxy)

```bash
# Zainstaluj Nginx i Certbot
apt install nginx certbot python3-certbot-nginx

# Konfiguracja Nginx
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

    # WebSocket support dla live sessions
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

# Aktywuj konfigurację
ln -s /etc/nginx/sites-available/inside-tower /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx

# Certyfikat SSL (Let's Encrypt)
certbot --nginx -d tower.example.com
```

### Firewall (UFW)

```bash
# Włącz UFW
ufw default deny incoming
ufw default allow outgoing

# Tower
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS (Tower)'
ufw allow 5000/tcp comment 'Inside Tower HTTP (direct)'

# Gate
ufw allow 22/tcp comment 'SSH (Inside Gate Proxy)'
ufw allow 3389/tcp comment 'RDP (Inside Gate Proxy)'

# Management SSH (zmieniony port)
ufw allow 2222/tcp comment 'SSH Management'

# Aktywuj firewall
ufw enable

# Sprawdź status
ufw status verbose
```

### Automatyczne backup (cron)

```bash
# Utwórz skrypt backup
cat > /usr/local/bin/inside-backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backup/inside"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Backup database
sudo -u postgres pg_dump inside_tower | gzip > "$BACKUP_DIR/tower_$DATE.sql.gz"

# Usuń backupy starsze niż 30 dni
find "$BACKUP_DIR" -name "tower_*.sql.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR/tower_$DATE.sql.gz"
EOF

chmod +x /usr/local/bin/inside-backup.sh

# Dodaj do crontab (codziennie o 2:00)
crontab -e
# Dodaj linię:
0 2 * * * /usr/local/bin/inside-backup.sh >> /var/log/inside-backup.log 2>&1
```

---

## Często zadawane pytania (FAQ)

### Czy Tower i Gate mogą być na różnych serwerach?

**Tak.** Tower i Gate mogą być na osobnych serwerach. W konfiguracji Gate (`/opt/inside-gate/config/inside.conf`) ustaw:

```ini
tower_url = http://TOWER_IP:5000
```

Upewnij się że Gate ma dostęp sieciowy do Tower na porcie 5000.

### Jak dodać więcej adresów IP do puli Gate?

1. Dodaj adresy IP do interfejsu:
   ```bash
   for ip in $(seq 171 200); do
       ip addr add 10.21.37.$ip/24 dev eth0
   done
   ```

2. Zaktualizuj pulę w Tower GUI:
   - Gates → gate01 → Edit
   - Zmień **IP Pool End** na `10.21.37.200`

### Czy mogę mieć wiele Gate podłączonych do jednego Tower?

**Tak.** Możesz mieć wiele Gate (w różnych lokalizacjach/sieciach) podłączonych do jednego Tower. Każdy Gate ma swój unikalny API token i pulę IP.

### Jak zmienić hasło admin?

**Opcja 1: Przez GUI (zalecane)**
1. Zaloguj się jako admin
2. Menu: Users → admin → Change Password

**Opcja 2: Przez CLI**
```bash
cd /opt/inside-tower
sudo -u inside PYTHONPATH=/opt/inside-tower \
    DATABASE_URL="postgresql://tower_user:PASSWORD@localhost/inside_tower" \
    ./lib/venv/bin/python3 scripts/create_admin_user.py
```

### Gdzie są zapisywane nagrania sesji?

Nagrania sesji SSH/RDP są zapisywane w:
```
/var/log/inside/tower/recordings/YYYYMMDD/username_server_date_time.rec
```

Możesz je odtwarzać przez Tower GUI: Sessions → szczegóły sesji → Play Recording

---

## Wsparcie i dokumentacja

- **Dokumentacja techniczna:** [GitHub Wiki](https://github.com/company/inside/wiki)
- **Issues i bug reports:** [GitHub Issues](https://github.com/company/inside/issues)
- **Email kontaktowy:** support@example.com

---

## Licencja

Inside © 2026 - Proprietary Software  
All rights reserved.
