# Inside - SSH Access Control, Który Naprawdę Działa

**Enterprise SSH gateway z obsługą natywnego klienta, zero zmian w backendzie, oraz Teleport-style session sharing.**

[![Status](https://img.shields.io/badge/status-production-brightgreen)]()
[![Version](https://img.shields.io/badge/version-2.0-blue)]()
[![Python](https://img.shields.io/badge/python-3.13-blue)]()

---

## Dlaczego Inside Istnieje

Współczesne zespoły infrastrukturalne polegają na SSH każdego dnia — na serwerach, switchach, routerach, firewallach, storage appliances, hypervisorach, nodach Kubernetes, cloud VMs. Każda warstwa prawdziwej infrastruktury oddycha przez SSH.

**Branża ma problem.**

Tradycyjne SSH gateway wymuszają wybór: Zainstaluj agenty wszędzie, albo strać kompatybilność z natywnym SSH. Większość enterprise nie może zainstalować agentów na legacy hardware — i nie powinna musieć.

Wszystkie istniejące rozwiązania zawodzą gdy dotkniesz:
- 10-letnie Cisco switche
- Stare ASA firewalle
- ProCurve / Dell / Juniper urządzenia
- Storage appliances
- Stare ESXi lub iLO firmware
- Legacy Linux z OpenSSH 5/6
- Cokolwiek co nie może uruchomić vendor agenta
- Cokolwiek co po prostu wystawia SSH i nic więcej

**To jest miejsce gdzie żyje prawdziwy świat.**

Każde enterprise ma długi ogon starych ale krytycznych systemów, które nie będą wymienione i nie mogą być modyfikowane. Kontrola dostępu musi tam działać — inaczej to nie jest kontrola dostępu.

---

## Co Wyróżnia Inside

Inside dostarcza enterprise access control zachowując natywne SSH — kombinacja rzadko spotykana w komercyjnych produktach.

### Inside vs Konkurencja

| Funkcja | Inside | Teleport | StrongDM | Tradycyjny PAM |
|---------|--------|----------|----------|-----------------|
| **Natywny klient SSH** | ✅ Standardowy `ssh` | ⚠️ Wymaga `tsh` | ⚠️ Custom client | ❌ Web console |
| **Zmiany w backendzie** | ✅ Zero | ❌ Agent lub CA | ❌ Wymagany agent | ❌ Agent + PAM |
| **Legacy hardware** | ✅ Działa | ❌ Brak wsparcia agent | ❌ Brak wsparcia agent | ❌ Brak wsparcia agent |
| **User experience** | `ssh user@host` | `tsh ssh user@host` | Custom syntax | Web GUI |
| **Port forwarding** | ✅ Natywny `-L/-R/-D` | ⚠️ Via tsh tunnel | ⚠️ Limited | ❌ Not supported |
| **SCP/SFTP** | ✅ Standardowe narzędzia | ⚠️ Via tsh | ⚠️ Limited | ❌ Web upload |
| **Agent forwarding** | ✅ Natywny `-A` | ⚠️ Wymaga setup | ❌ Not supported | ❌ Not supported |
| **Session sharing** | ✅ Natywny SSH | ✅ tsh join | ❌ | ❌ |
| **Czas wdrożenia** | 1 godzina | Tygodnie/miesiące | Tygodnie | Miesiące |
| **Koszt** | Open source | $10-50/user/msc | $$$ | $$$$ |

---

## Kluczowa Innowacja: "Bycie Wewnątrz"

**Inside nie zarządza tożsamościami. Inside zarządza tym, kiedy prawdziwi ludzie mogą być wewnątrz Twojej infrastruktury.**

Nie "dostęp", nie "tożsamość", nie "kontrola" — każdy od razu rozumie:

- **Kto jest wewnątrz** w tej chwili
- **Kto może być wewnątrz** (i kiedy)
- **Co robi będąc wewnątrz**
- **Kiedy przestaje być wewnątrz**

Idealny język operacyjny:

*"Kto jest wewnątrz produkcji teraz?"*

*"Był wewnątrz przez 30 minut."*

*"Ta obecność trwa do 14:30."*

*"Nikt nie może być wewnątrz bez grantu."*

Brzmi jak rzeczywistość, nie jak system.

---

## Jak To Działa

**Wersja 30-Sekundowa:**

```
Komputer Osoby → Brama Inside → Serwer Backendowy
  (gdziekolwiek)    (jedno miejsce)    (10.0.x.x)
```

Z perspektywy osoby: `ssh serwer.firma.pl` — działa jak normalny SSH/RDP.

Za kulisami: Inside sprawdza "czy ta osoba ma ważny grant W TEJ CHWILI?" i albo pozwala, albo odmawia.

**Architektura:**

Inside to transparentny MITM SSH gateway z jedną kluczową zaletą:
- **Klient używa natywnego SSH** (`ssh -A user@host`)
- **Backend używa natywnego SSH daemon** (OpenSSH, IOS, ASA… cokolwiek)
- **Inside siedzi pośrodku**, niewidoczny dla obu stron
- **Autentykacja backendu** przez prawdziwy SSH key użytkownika (agent forwarding)

Wszystko inne — MFA (v2.1), kontrola dostępu, audit, session replay, session sharing — dzieje się transparentnie w gateway.

Ponieważ Inside operuje na poziomie protokołu SSH, nie na poziomie OS czy agenta, nie nakłada żadnych wymagań na urządzenia.

Wszystko inne — MFA, kontrola dostępu, audit, session replay, session sharing — dzieje się transparentnie w gateway.

**Jeśli mówi SSH — Inside to rozumie.**

---

## Kluczowe Koncepcje

### Person (Osoba)

Prawdziwy człowiek — nie username.
- Ma imię i nazwisko (np. "Jan Kowalski")
- Ma source IP (biuro, dom, VPN, mobile)
- **NIE loguje się do systemów** — osoby wchodzą do środowisk

### Grant

Pozwolenie na bycie wewnątrz.
- Definiuje **gdzie** (które serwery/grupy)
- Definiuje **jak długo** (8 godzin, tydzień, na stałe)
- Definiuje **pod jakimi warunkami** (okna czasowe, protokoły, dozwolone loginy SSH)

Nie rola, nie grupa — tylko konkretne pozwolenie które wygasa.

Granty są tworzone przez **Web Management Interface** — prosty wizard w 4 krokach:
1. **Who (Kto)** - Wybierz osobę (lub grupę użytkowników)
2. **Where (Gdzie)** - Wybierz serwery (lub grupę serwerów)
3. **How (Jak)** - Protokół (SSH/RDP), czas trwania, harmonogram
4. **Review (Przegląd)** - Potwierdź i utwórz

### Stay (Obecność)

Fakt bycia wewnątrz.
- **Stay zaczyna się** gdy osoba wchodzi (pierwsze połączenie)
- **Stay kończy się** gdy grant wygasa lub zostaje odwołany
- **Stay może mieć wiele sesji** (disconnect/reconnect dozwolone)
- Osoba **pozostaje wewnątrz** nawet między połączeniami

Ta koncepcja jest unikalna dla Inside. "Stay" grupuje całą aktywność podczas jednego okresu, czyniąc audyty trywialnymi:

*"Pokaż mi wszystkich którzy byli wewnątrz produkcji ostatni miesiąc"* → Gotowe. Jedno zapytanie.

**Jak Działa Stay:**

1. **Stay Rozpoczyna Się** - Osoba łączy się pierwszy raz (grant zwalidowany)
2. **Wiele Sesji** - Osoba może disconnect/reconnect swobodnie (ten sam stay trwa)
3. **Stay Aktywny** - Widoczny w real-time dashboard: "Alice jest wewnątrz prod-db-01"
4. **Stay Kończy Się** - Gdy grant wygasa, admin odwołuje, lub okno harmonogramu się zamyka
5. **Auto-Terminacja** - Aktywne sesje terminate, osoba nie może już wejść

### Session (Sesja)

Pojedyncze połączenie TCP w ramach stay.
- Połączenie SSH (terminal)
- Połączenie RDP (pulpit)
- Połączenie HTTP (web GUI - wkrótce)

Szczegół techniczny. Stay jest tym, co się liczy dla accountability.

### Username

Techniczny identyfikator w systemach backendowych (root, admin, backup, etc.)
- **NIE reprezentuje osoby**
- Inside mapuje `username → person` transparentnie
- Brak zmian w hostach, klientach, AAD, czy targetach

**To jest kluczowy punkt architektury:** Inside dostarcza accountability bez naruszania istniejących systemów.

---

## NOWOŚĆ w v2.0: Session Sharing (Teleport-Style)

**Dołącz do live SSH sessions używając natywnego SSH — nie web emulatora.**

Admin console (SSH-based TUI) pozwala upoważnionym użytkownikom:

**Watch Mode (Read-Only):**
```bash
# Połącz się z admin console
ssh admin@gate.firma.pl

# Wybierz "Watch Session"
# Wybierz z listy aktywnych sesji
# Oglądaj real-time output (cichy obserwator)
```

**Join Mode (Read-Write):**
```bash
# Połącz się z admin console
ssh admin@gate.firma.pl

# Wybierz "Join Session"
# Wybierz z listy aktywnych sesji
# Interaguj z sesją (pair programming, szkolenie)
```

**Jak To Działa:**
- `SessionMultiplexer` - Jedna sesja SSH → wielu widzów
- Ring buffer (50KB) - Nowi widzowie dostają ostatnią historię
- Input queue - Komendy od uczestników są kolejkowane
- Thread-safe broadcasting - Real-time output do wszystkich widzów
- Announcements - "*** alice joined ***" widoczne dla właściciela

**Żaden inny vendor nie robi tego z natywnymi klientami SSH.**

Teleport wymaga `tsh join`. Inside wymaga tylko `ssh`.

---

## Wpływ Biznesowy

**Tradycyjna SSH Access Control:**
- Deploy agentów na 500 serwerów: Tygodnie pracy
- Modyfikacja backend configs: Change management nightmare
- Szkolenie użytkowników z nowych clientów: Opór i tickety support
- Wymiana legacy devices: Budget explosion
- Złożoność rollback: Wysokie ryzyko

**Z Inside:**
- Deploy gateway: 1 godzina
- Backend changes: Zero
- User training: Zero (ta sama komenda `ssh`)
- Legacy support: Wszystko działa
- Rollback: Wyłącz gateway

### Realne Metryki

- **Czas przygotowania audytu:** 3 tygodnie → 2 godziny (Stay timeline + session replay)
- **Czas wdrożenia:** 6 miesięcy → 1 dzień (brak zmian w backendzie)
- **Pokrycie:** 100% infrastruktury SSH (włącznie z 10-letnimi urządzeniami)
- **Compliance:** ISO 27001, SOC 2, GDPR gotowe out-of-box
- **Zakłócenie dla użytkowników:** Zero (natywne narzędzia działają dalej)

### Porównanie Kosztów

- **Teleport:** $10-50 na użytkownika miesięcznie + koszty wdrożenia
- **StrongDM:** Podobne ceny + vendor lock-in
- **Tradycyjny PAM:** $50k-500k licencja + 6 miesięcy wdrożenia
- **Inside:** Open source + opcjonalne commercial support

---

## Interfejs Zarządzania Web

**Całe zarządzanie odbywa się przez Web GUI** (port 5000). Nie ma narzędzi CLI.

### Dashboard

Widok real-time z auto-refresh co 5 sekund:
- **Kto jest wewnątrz teraz** - Aktywne stays z nazwiskami osób, serwerami, czasem trwania
- **Ostatnie wejścia** - 100 ostatnich prób połączenia (sukces + odmowy)
- **Granty wygasające wkrótce** - Ostrzeżenia dla grantów < 1 godzina
- **Statystyki** - Stays dzisiaj, aktywne sesje, dostępne nagrania

### Grant Creation Wizard

Prosty proces w 4 krokach:
1. **Who (Kto)** - Wybierz osobę (lub grupę użytkowników z dropdown)
2. **Where (Gdzie)** - Wybierz serwery (lub grupę serwerów z dropdown)
3. **How (Jak)** - Protokół (SSH/RDP/Oba), czas trwania (1h-30d lub stały), harmonogram (opcjonalnie)
4. **Review (Przegląd)** - Podsumowanie ze wszystkimi szczegółami, potwierdź i utwórz

Grant staje się aktywny natychmiast.

### Universal Search (Mega-Wyszukiwarka)

Znajdź wszystko z 11+ filtrami:
- Imię osoby, username
- Serwer, grupa serwerów, target IP
- Protokół (SSH/RDP), status (aktywny/zakończony/odmowa)
- Zakres dat (od-do)
- Grant ID, session ID
- Powód odmowy

Eksport wyników do CSV. Auto-refresh co 2 sekundy.

### Live Session View

Oglądaj aktywne sesje SSH w czasie rzeczywistym:
- Terminal output aktualizowany co 2 sekundy
- Zobacz co osoba pisze teraz
- Idealne do szkoleń, supportu, monitoringu bezpieczeństwa

**Uwaga:** v2.0 Admin Console zapewnia lepszą jakość live view przez SSH (nie przeglądarką).

### Session Recordings (Nagrania Sesji)

Odtwarzaj przeszłe sesje:
- **SSH** - Player terminala (asciinema-style) z pause/play/prędkość
- **RDP** - MP4 video player (HTML5) z timeline scrubbing

Pełna historia, przeszukiwalna, eksportowalna.

### Kontrola Dostępu
- Multiple source IPs per person
- Server groups
- Granular scope
- Protocol filtering
- SSH login restrictions
- Temporal grants
- Schedule windows
- Recursive groups
- **MFA enforcement** - Wymuszanie MFA per grant via Azure AD SAML
- **MFA per stay** - Pierwsza sesja wymaga MFA, kolejne pomijają (persistent auth)

### Zarządzanie Sesjami
- Live monitoring
- Session sharing (watch/join) - v2.0
- Recording (SSH terminal + RDP video)
- Playback z built-in players
- Search z wieloma filtrami
- Auto-termination po wygaśnięciu grantu
- 50KB history buffer

### Admin Console (v2.0)
SSH-based TUI dla operacji uprzywilejowanych:
1. Active Stays
2. Active Sessions  
3. Join Session (read-write)
4. Watch Session (read-only)
5. Kill Session
6-8. W przygotowaniu

### Auditing
- Entry attempts (success + denial)
- Grant changes z pełną historią
- Stay timeline
- Session recordings
- CSV export

### User Experience
- Transparent - standard SSH/RDP clients
- No agents
- Native tools (ssh, scp, sftp, VSCode Remote, Ansible)
- Port forwarding works
- File transfer works
- Agent forwarding works

---

## Przykład z Życia

**Problem:** Problem z produkcyjną bazą danych o 9 rano. DBA potrzebuje natychmiastowego dostępu.

**Tradycyjne podejście:**
1. Utwórz konto VPN (15 minut)
2. Utwórz SSH key (5 minut)
3. Dodaj key do prod-db (10 minut + change ticket)
4. DBA się łączy (w końcu!)
5. Pamiętaj żeby odwołać później (**zazwyczaj zapomniane**)

**Z Inside:**
1. Admin otwiera Web GUI (30 sekund)
2. Grant Creation Wizard: "dba-jan" → "prod-db-01" → "4 godziny" → Utwórz
3. DBA natychmiast łączy się: `ssh dba-jan@prod-db-01.firma.pl`

**Rezultat:**
- Dostęp przyznany w 30 sekund
- Automatycznie wygasa po 4 godzinach
- Pełne nagranie sesji
- Audit trail: "Jan był wewnątrz prod-db-01 od 09:00 do 13:00"

---

## Roadmap

### ✅ v2.0 (Obecna - Luty 2026)

**KILLER FEATURES:**

**Session Multiplexing (Teleport-Style)**
- Admin Console (SSH-based TUI)
- SessionMultiplexer z ring buffer (50KB)
- Join Session (read-write mode)
- Watch Session (read-only mode)
- Real-time broadcasting
- Session sharing z natywnymi klientami SSH

**Integracja MFA z Azure AD**
- Autentykacja Azure AD SAML
- MFA per stay (pierwsza sesja wymaga MFA, kolejne pomijają)
- Wymuszanie MFA per grant (flaga grant.mfa_required)
- MFA challenge z autentykacją w przeglądarce
- Automatyczna persistence sesji via SSH key fingerprint

### 🎯 v2.1 (Planowana - Q2 2026)

**Rozszerzenia Admin Console**
- Opcja 6: Przeglądarka Audit Logs (przeszukiwalna, filtrowalna)
- Opcja 7: Grant Debug interface (diagnostyka odmów dostępu)
- Opcja 8: MFA Status checker (widok aktywnych sesji MFA)
- Odtwarzanie nagrań sesji w admin console
- Info o sesjach cross-gate (gdy multi-gate wdrożone)

### 💡 v2.2 (Przyszłość)

**Cross-Gate Session Joining + RDP Multiplexing**
- Redis pub/sub dla session registry
- Dołączanie do sesji przez różne gaty
- RDP session sharing

### 🚀 v3.0 (Commercial Release)

**HTTP/HTTPS Proxy + Licensing**
- MITM proxy dla legacy web GUIs
- Commercial licensing system
- Self-hosted z support contracts

---

## Quick Start

**Instalacja** (identyczna jak w wersji angielskiej):

Szczegółowy opis instalacji, konfiguracji i pierwszego grantu dostępny w [README.md](README.md) w sekcji "Quick Start".

**Kluczowe kroki:**
1. Sklonuj repo i zainstaluj zależności
2. Setup PostgreSQL database
3. Skonfiguruj inside.conf
4. Uruchom serwisy (ssh-proxy, rdp-proxy, flask)
5. Otwórz Web GUI: http://gateway:5000
6. Dodaj osobę (Management → Persons)
7. Dodaj serwer (Management → Servers)
8. Utwórz grant (Dashboard → New Grant → Wizard)
9. Osoba łączy się: `ssh username@gateway`

---

## TL;DR

**Inside w jednym zdaniu:**

*Enterprise SSH gateway używający natywnych klientów SSH, który dostarcza time-limited grants, pełne nagrania sesji, real-time session sharing i kompletny audit trail — wdrożony w 1 godzinę bez zmian w backendzie.*

**Kluczowe Zalety:**

- **Native SSH** - Działa ze standardowym `ssh`, `scp`, `sftp`, Ansible, VSCode Remote
- **Zero Zmian w Backendzie** - Brak agentów, brak configs, brak modyfikacji
- **Legacy Support** - 10-letnie Cisco switche, ASAs, storage appliances — cokolwiek z SSH
- **Session Sharing** - Join/watch live sessions używając natywnego SSH (Teleport-style)
- **Stay-Centric** - Person accountability, nie username accountability
- **1-Godzinne Wdrożenie** - Nie 6 miesięcy

**Jeden wizard do przyznania dostępu:**

Web GUI → New Grant → Who: alice | Where: prod-db | How: 8h → Create

**Jedno miejsce żeby zobaczyć wszystko:**
```
Dashboard → Kto jest wewnątrz w tej chwili
```

**Dlaczego Inside:**

Twoi devs już znają SSH — po co zmuszać ich do nauki `tsh`?

Twoje serwery już mają SSHD — po co instalować agenty?

Twoje workflow już używa `scp` — po co je zmieniać?

Inside: Enterprise features, zero zakłóceń, ułamek kosztu.

---

## Zaczynamy

**Repository:** https://github.com/pawelmojski/inside

**Status:** Production (v2.0 z session multiplexing)

**Licencja:** Open source (dostępne opcje commercial support)

**Kontakt:**
- Pytania: Otwórz issue na GitHub
- Zapytania komercyjne: Zobacz [DOCUMENTATION.md](DOCUMENTATION.md)
- Beta testing: Early access dla v2.1 (MFA integration)

**Następne Kroki:**
1. Gwiazdka na repo ⭐
2. Wypróbuj quick start installation
3. Dołącz do dyskusji na GitHub Issues
4. Przyczyń się do projektu

---

**Zbudowane dla enterprise zmęczonych wyborem między bezpieczeństwem a użytecznością.**

**Inside daje Ci jedno i drugie.**
# Admin (30 sekund):
inside grant dba-john --server prod-db-01 --duration 4h

# DBA (natychmiast):
ssh dba-john@prod-db-01.firma.pl
```

- ✅ Dostęp przyznany w 30 sekund
- ✅ Automatycznie wygasa za 4 godziny
- ✅ Pełne nagranie sesji
- ✅ Ślad audytowy: "John był wewnątrz prod-db-01 od 09:00 do 13:00"

---

## 🎨 Interfejs Web do Zarządzania

### Dashboard

Widok w czasie rzeczywistym:
- **Kto jest wewnątrz teraz** (aktywne stay)
- **Ostatnie wejścia** (ostatnie 100 prób)
- **Granty wygasające wkrótce**
- **Statystyki** (obecności dzisiaj, dostępne nagrania)

Auto-odświeżanie co 5 sekund.

### Kreator Tworzenia Grantów

Prosty proces 4-etapowy:
1. **Kto** - Wybierz osobę (lub grupę użytkowników)
2. **Gdzie** - Wybierz serwery (lub grupę serwerów)
3. **Jak** - Protokół (SSH/RDP), czas trwania, harmonogram
4. **Przegląd** - Potwierdź i utwórz

### Uniwersalne Wyszukiwanie (Mega-Wyszukiwarka)

Znajdź cokolwiek z 11+ filtrami:
- Imię osoby, username
- Serwer, grupa, IP
- Protokół, status
- Zakres dat
- Grant ID, session ID
- Powód odmowy

Eksport wyników do CSV. Auto-odświeżanie co 2 sekundy.

### Podgląd Sesji Na Żywo

Oglądaj aktywne sesje SSH w czasie rzeczywistym:
- Wyjście terminala (odświeżanie co 2 sekundy)
- Co osoba pisze w tej chwili
- Idealne do szkoleń, wsparcia, audytów

### Nagrania Sesji

Odtwarzaj przeszłe sesje:
- **SSH** - Odtwarzacz terminala (jak asciinema)
- **RDP** - Odtwarzacz wideo MP4
- Pełna historia, przeszukiwalna, eksportowalna

---

## 💎 Funkcje

### Kontrola Dostępu
- ✅ **Wiele IP źródłowych na osobę** - Dom, biuro, VPN, mobile
- ✅ **Grupy serwerów** - Przyznaj dostęp do całych grup ("Wszystkie serwery produkcyjne")
- ✅ **Szczegółowy zakres** - Poziom grupy, serwera lub protokołu
- ✅ **Filtrowanie protokołów** - Tylko SSH, tylko RDP lub oba
- ✅ **Ograniczenia loginów SSH** - Zezwalaj tylko na konkretne konta systemowe (usernames)
- ✅ **Granty czasowe** - Ograniczone czasowo z automatycznym wygaśnięciem
- ✅ **Okna harmonogramu** - Dostęp tylko Pon-Pt 9-17, cyklicznie co tydzień
- ✅ **Rekurencyjne grupy** - Grupy użytkowników z dziedziczeniem

### Zarządzanie Obecnościami (Stay)
- ✅ **Monitoring na żywo** - Zobacz kto jest wewnątrz w czasie rzeczywistym
- ✅ **Podgląd SSH na żywo** - Oglądaj sesję terminala w trakcie
- ✅ **Nagrywanie** - SSH (terminal) i RDP (wideo)
- ✅ **Odtwarzanie** - Przeglądaj przeszłe obecności
- ✅ **Wyszukiwanie** - Znajdź obecności po osobie, serwerze, czasie, statusie
- ✅ **Auto-odświeżanie** - Dashboard co 5s, wyszukiwarka co 2s
- ✅ **Wygaśnięcie grantu** - Sesje przerywane gdy grant się kończy (osoby dostają wcześniejsze ostrzeżenie)

### Audytowanie
- ✅ **Próby wejścia** - Zarówno udane jak i odmówione
- ✅ **Zmiany grantów** - Pełny ślad audytowy z historią
- ✅ **Powody odmowy** - Jasne logowanie dlaczego wejście zostało odmówione
- ✅ **Eksport** - Eksport CSV do raportowania/zgodności

### Doświadczenie Użytkownika
- ✅ **Przezroczyste** - Działa ze standardowymi klientami SSH/RDP
- ✅ **Bez agentów** - Zero oprogramowania na kliencie lub backendzie
- ✅ **Natywne narzędzia** - Używaj ssh, mstsc, PuTTY - cokolwiek wolisz
- ✅ **Port forwarding** - SSH -L, -R, -D działają (jeśli grant pozwala)
- ✅ **Transfer plików** - scp, sftp działają normalnie

---

## 🚀 Dlaczego Inside Jest Inny

### 1️⃣ Natychmiastowy Model Mentalny

Nie "dostęp", nie "tożsamość", nie "kontrola".

Każdy natychmiast rozumie:
- Kto jest wewnątrz
- Kto może być wewnątrz
- Co robi będąc wewnątrz
- Kiedy przestaje być wewnątrz

Nie trzeba tłumaczyć architektury.

### 2️⃣ Praktyczna Rzeczywistość vs. Teoretyczny Ideał

To pokazuje praktyczną różnicę między teorią a realnym IT:

| Aspekt | Inside | Tradycyjne IAM/PAM |
|--------|--------|---------------------|
| **Czas wdrożenia** | 1 godzina | Miesiące |
| **Inwazyjność** | Zero zmian w klientach/serwerach | Agenty, konfiguracje wszędzie |
| **Akceptacja użytkowników** | Użytkownicy niczego nie zauważają | Programiści protestują |
| **Kontrola i audyt** | Pełna odpowiedzialność per stay | Słabe śledzenie sesji |
| **Skalowalność** | Każdy nowy VM/serwer auto-chroniony | Konfiguracja per-host |

💡 **Puenta dla CTO/CISO:**

*"Nie zmieniamy świata - dajemy Ci pełną odpowiedzialność i audyt w realnym IT w godzinę, nie w miesiące."*

### 3️⃣ Tożsamość to NIE username

- ✅ **Tożsamość = osoba**, nie konto systemowe
- Konta systemowe mogą być: współdzielone, sklonowane, tymczasowe
- Każdy stay jest powiązany z **konkretną osobą**

> 💡 **Dla audytora/CTO:** Konto techniczne ≠ odpowiedzialność użytkownika

### 4️⃣ Dostęp skoncentrowany na Stay

- ⏱ **Granty czasowe** - dostęp tylko w wyznaczonym czasie
- 🔒 **Brak aktywnego grantu → brak wejścia**
- ❌ **Stay kończy się automatycznie gdy grant wygasa**

> 🔑 Kontrola obecności zamiast walki z systemowym IAM

### 5️⃣ Pełna audytowalność

- 🎥 **Nagrywanie każdej sesji**
- 📝 Sesje powiązane z osobą, nie kontem
- 🔍 Możliwość przeglądu działań każdej osoby

> 📜 **ISO 27001:** audytowalność i odpowiedzialność spełnione

### 6️⃣ Projekt nieinwazyjny

- ⚡ Nie wymaga agentów, PAM, ani zmian w firewallu
- 🖥 Działa z natywnymi narzędziami (SSH, vendor CLI)
- ♻️ Idealny dla systemów legacy i appliance'ów

> 🛡 Minimalne ryzyko operacyjne i łatwe wdrożenie

### 7️⃣ Praktyczna rzeczywistość

- 🖥 VM sklonowane → automatycznie podlega zasadom Inside
- 👥 Współdzielone konta → audytowalne obecności
- ⏳ Maszyny "tymczasowe" → nagrane i kontrolowane, nawet po latach

> 🚀 System dopasowany do **realnego IT**, nie teoretycznego ideału

### 8️⃣ Zgodność z ISO 27001

- ✅ Kontrolowany dostęp
- ✅ Least privilege (czasowo)
- ✅ Odpowiedzialność i audytowalność
- ✅ Nieinwazyjne wdrożenie

> 📌 Spełnia **rzeczywiste wymagania audytu** bez rewolucji w IAM

### 9️⃣ Kluczowy wniosek

> **"Nie naprawiamy świata. Naprawiamy odpowiedzialność.**
> **Liczy się kto działa, kiedy i co robi - nie konto."**

---

## 🏗️ Architektura

### Obecna Architektura (v1.8)

```
Osoba (gdziekolwiek)
    ↓
Brama Inside (jeden serwer)
    ├── ssh_proxy (Entry przez SSH :22)
    ├── rdp_proxy (Entry przez RDP :3389)
    └── web_ui (:5000)
    ↓
Serwery Backendowe (10.0.x.x)
```

### Jak Działa Entry

```
1. Osoba łączy się: ssh alice@prod-db-01
2. Entry (ssh_proxy) wyciąga:
   - IP źródłowe (identyfikuje osobę)
   - Hostname docelowy (identyfikuje serwer)
3. Zapytanie do bazy:
   - Osoba ma ważny grant?
   - Grant zezwala na SSH?
   - Grant zezwala na ten serwer?
   - Grant zezwala na tego SSH username?
4. Jeśli tak:
   - Utwórz lub dołącz do stay
   - Utwórz sesję w ramach stay
   - Przekaż do backendu
   - Nagraj wszystko
5. Jeśli nie:
   - Odmów wejścia
   - Zapisz powód odmowy
```

### Przyszła Architektura (v1.9+)

**Rozproszona:** Tower (płaszczyzna kontroli) + Gates (płaszczyzny danych)

```
Tower (Płaszczyzna Kontroli)
├── Web UI
├── REST API (/api/v1/)
└── PostgreSQL (granty, obecności, osoby)

Gates (Płaszczyzna Danych - rozproszone)
├── Gate 1 (DMZ) - ssh/rdp/http entry
├── Gate 2 (Cloud) - ssh/rdp entry
└── Gate 3 (Biuro) - tylko ssh entry

Komunikacja: REST API + lokalny cache
```

Korzyści:
- Skalowanie horyzontalne (dodaj więcej Gates)
- Dystrybucja geograficzna
- Tryb offline (Gates cache'ują granty)
- Redukcja promienia rażenia

---

## 📋 Przypadki Użycia

### 1. Dostęp Kontraktora

**Problem:** Zewnętrzny kontraktor potrzebuje 2 tygodnie dostępu do środowiska stagingowego.

**Rozwiązanie:**
```bash
inside grant kontraktor-bob --group staging-servers --duration 14d
```

Po 14 dniach: automatyczne wygaśnięcie, brak sprzątania.

### 2. Rotacja Dyżurów

**Problem:** Tygodniowy dyżurny inżynier potrzebuje awaryjnego dostępu do produkcji.

**Rozwiązanie:**
```bash
# Każdy poniedziałek, przyznaj obecnemu dyżurnemu
inside grant oncall-engineer --group production \
  --schedule "Mon-Sun 00:00-23:59" \
  --duration 7d
```

Grant automatycznie wygasa, nowy dyżurny dostaje nowy grant.

### 3. Tymczasowa Eskalacja Uprawnień

**Problem:** Junior admin potrzebuje sudo na konkretne 1-godzinne okno maintenance.

**Rozwiązanie:**
```bash
inside grant junior-admin --server app-01 \
  --ssh-login root \
  --duration 1h
```

Po 1 godzinie: dostęp root automatycznie odwołany, stay kończy się.

### 4. Audyt Zgodności

**Problem:** "Pokaż mi wszystkich, którzy byli wewnątrz produkcji w zeszłym miesiącu."

**Rozwiązanie:**
- Web UI → Wyszukiwanie
- Filtr: server_group="Production", date_from="2025-12-01"
- Eksport → CSV
- Gotowe. Pełny ślad audytowy z nagraniami sesji.

---

## 🔐 Bezpieczeństwo

### Autentykacja

- **Identyfikacja osoby** - Po IP źródłowym (mapowane na osobę w bazie)
- **Bez haseł** - Inside nigdy nie obsługuje haseł
- **Autentykacja backendowa** - Klucze SSH, dane RDP przechowywane per osoba

### Autoryzacja

- **Oparta na grantach** - Każde wejście sprawdzane względem aktywnych grantów
- **Czasowa** - Granty wygasają automatycznie
- **Szczegółowa** - Per-osoba, per-serwer, per-protokół, per-username

### Ślad Audytowy

- **Niezmienne zapisy** - Wszystkie wejścia logowane (sukces + odmowa)
- **Nagrania sesji** - Logi terminala (SSH), wideo (RDP)
- **Historia zmian** - Tworzenie/modyfikacja/usuwanie grantów śledzone

### Kontrola Sesji

- **Monitoring na żywo** - Zobacz kto jest wewnątrz teraz
- **Wymuszone przerwanie** - Admin może zabić aktywne stay
- **Auto-przerwanie** - Stay kończy się gdy grant wygasa (z ostrzeżeniami)

---

## 🛠️ Zaawansowane Funkcje

### Kontrola Port Forwardingu

Konfiguracja w Grant Creation Wizard → krok **How**:

- **Dozwolone:** SSH -L, -R, -D działają normalnie
- **Zablokowane:** Połączenie odrzucone jeśli próba port forwarding

Przydatne dla bastion hosts (allow forwarding) vs production servers (block forwarding).

### Dostęp Oparty na Harmonogramie

Konfiguracja w Grant Creation Wizard → krok **How** → Schedule (opcjonalnie):

- **Przykład:** "Mon-Fri 09:00-17:00", timezone "Europe/Warsaw"
- **Zachowanie:** Cyklicznie co tydzień — osoba może wejść w harmonogramie
- **Poza harmonogramem:** Wejście odmówione, aktywne stays auto-terminate

Idealne dla dostępu tylko w godzinach pracy do produkcji.

---

## Roadmap

Szczegółowy roadmap z opisem wszystkich wersji dostępny w głównym [README.md](README.md) w sekcji "Roadmap".

**Aktualne:**
- ✅ **v2.0** (Luty 2026) - Session Multiplexing (Teleport-Style) - **OBECNA WERSJA**

**Planowane:**
- 🎯 **v2.1** (Q2 2026) - MFA Integration z Azure AD
- 💡 **v2.2** - Cross-Gate Session Joining + RDP Multiplexing
- 🔮 **v2.3** - Admin Console Expansion (Audit Logs, Grant Debug, MFA Status)
- 🚀 **v3.0** - HTTP/HTTPS Proxy + Commercial Licensing

---

## 📚 Szybki Start

### Wymagania

- Serwer Linux (zalecany Debian 12)
- PostgreSQL 15+
- Python 3.13+
- Publiczne IP lub dostęp VPN dla klientów

### Instalacja

```bash
# 1. Sklonuj repozytorium
git clone https://github.com/pawelmojski/inside.git
cd inside

# 2. Zainstaluj zależności
pip install -r requirements.txt

# 3. Skonfiguruj bazę danych
sudo -u postgres createdb inside
alembic upgrade head

# 4. Konfiguracja
cp config/inside.conf.example config/inside.conf
vim config/inside.conf

# 5. Uruchom usługi
sudo systemctl start inside-ssh-proxy
sudo systemctl start inside-rdp-proxy
sudo systemctl start inside-flask
```

### Pierwszy Grant

```bash
# 1. Dodaj osobę
inside person add "Jan Kowalski" --ip 100.64.0.50

# 2. Dodaj serwer backendowy
inside server add prod-db-01 --ip 10.0.1.100

# 3. Utwórz grant
inside grant create jan.kowalski --server prod-db-01 --duration 8h

# 4. Osoba może teraz wejść
ssh jan.kowalski@gateway.firma.pl
```

---

## 🎓 Dokumentacja

- **[ROADMAP.md](ROADMAP.md)** - Plan rozwoju i historia wersji
- **[DOCUMENTATION.md](DOCUMENTATION.md)** - Dokumentacja techniczna
- **[README.md](README.md)** - Wersja angielska

---

## 💬 TL;DR

**Inside w jednym zdaniu:**

*Czasowe granty dla prawdziwych ludzi na bycie wewnątrz infrastruktury, z pełnym audytem i nagrywaniem sesji, wdrożone w godzinę.*

**Kluczowe różnice:**

- 👤 **Osoba ≠ username** - Odpowiedzialność dla ludzi, nie kont
- ⏱ **Skoncentrowane na Stay** - Kto jest wewnątrz teraz, jak długo
- 🎫 **Oparte na Grantach** - Konkretne pozwolenie, nie rola/grupa
- 🚀 **Nieinwazyjne** - Bez agentów, bez zmian, wdrożenie w godzinę
- 📜 **Pełny audyt** - Każde wejście, każdy stay, każda sesja nagrana

**Jedna komenda żeby przyznać dostęp:**
```bash
inside grant alice --server prod-db --duration 8h
```

**Jedno miejsce żeby zobaczyć wszystko:**
```
Dashboard → Kto jest wewnątrz teraz
```

---

**Projekt:** Inside
**Repozytorium:** https://github.com/pawelmojski/inside
**Status:** Produkcja (v1.8)
**Licencja:** Komercyjna (opcje monetyzacji otwarte)
