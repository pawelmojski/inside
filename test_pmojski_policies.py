#!/usr/bin/env python3
"""Test p.mojski access policies from different source IPs."""

import sys
sys.path.append('/opt/jumphost')

from src.core.database import SessionLocal
from src.core.access_control_v2 import AccessControlEngineV2

db = SessionLocal()
engine = AccessControlEngineV2()

print("=" * 80)
print("TEST: Polisy p.mojski z różnych źródeł")
print("=" * 80)

tests = [
    # Tailscale Linux (100.64.0.20) → SSH Test-SSH-Server
    ("Tailscale Linux", "100.64.0.20", "10.0.160.129", "ssh", "p.mojski", True, "policy #6"),
    ("Tailscale Linux", "100.64.0.20", "10.0.160.129", "ssh", "ideo", True, "policy #6"),
    ("Tailscale Linux", "100.64.0.20", "10.0.160.129", "ssh", "root", False, "policy #6 blocked"),
    ("Tailscale Linux", "100.64.0.20", "10.0.160.129", "ssh", "admin", False, "policy #6 blocked"),
    
    # Biuro Linux (10.30.14.3) → SSH Test-SSH-Server (wszystkie loginy!)
    ("Biuro Linux", "10.30.14.3", "10.0.160.129", "ssh", "p.mojski", True, "policy #7 ALL"),
    ("Biuro Linux", "10.30.14.3", "10.0.160.129", "ssh", "ideo", True, "policy #7 ALL"),
    ("Biuro Linux", "10.30.14.3", "10.0.160.129", "ssh", "root", True, "policy #7 ALL"),
    ("Biuro Linux", "10.30.14.3", "10.0.160.129", "ssh", "admin", True, "policy #7 ALL"),
    ("Biuro Linux", "10.30.14.3", "10.0.160.129", "ssh", "postgres", True, "policy #7 ALL"),
    
    # Tailscale Windows (100.64.0.39) → RDP Windows-RDP-Server
    ("Tailscale Windows", "100.64.0.39", "10.0.160.130", "rdp", None, True, "policy #8 RDP"),
    
    # Negative tests
    ("Tailscale Windows", "100.64.0.39", "10.0.160.129", "ssh", "p.mojski", False, "no SSH policy for Windows"),
    ("Tailscale Linux", "100.64.0.20", "10.0.160.130", "rdp", None, False, "no RDP policy for Linux"),
    ("Biuro Linux", "10.30.14.3", "10.0.160.130", "rdp", None, False, "no RDP policy for Biuro"),
]

passed = 0
failed = 0

for label, src_ip, dst_ip, proto, login, should_work, note in tests:
    result = engine.check_access_v2(db, src_ip, dst_ip, proto, login)
    status = "✅" if result['has_access'] else "❌"
    expected = "✅" if should_work else "❌"
    
    if result['has_access'] == should_work:
        passed += 1
        match = "✓"
    else:
        failed += 1
        match = "✗ BŁĄD"
    
    login_str = login if login else "N/A"
    print(f"\n[{match}] {label:18s} → {proto.upper()} login={login_str:10s} | {note}")
    print(f"     Expected: {expected} | Got: {status}")
    if not result['has_access'] and should_work:
        print(f"     Reason: {result['reason']}")

print("\n" + "=" * 80)
print(f"WYNIKI: {passed} PASSED, {failed} FAILED")
print("=" * 80)

if failed == 0:
    print("✅ Wszystkie testy przeszły pomyślnie!")
    print("\nKonfiguracja p.mojski:")
    print("  • Tailscale Linux (100.64.0.20)   → SSH jako p.mojski lub ideo")
    print("  • Biuro Linux (10.30.14.3)        → SSH jako ktokolwiek")
    print("  • Tailscale Windows (100.64.0.39) → RDP (Windows-RDP-Server)")
else:
    print(f"❌ {failed} testów nie przeszło!")

print("=" * 80)

db.close()
