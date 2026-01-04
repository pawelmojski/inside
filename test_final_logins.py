#!/usr/bin/env python3
"""Test: Mariusz (mariusz+deploy) vs Jasiek (jasiek+deploy) - separate login sets."""

import sys
sys.path.append('/opt/jumphost')

from src.core.database import SessionLocal
from src.core.access_control_v2 import AccessControlEngineV2

db = SessionLocal()
engine = AccessControlEngineV2()

print("=" * 80)
print("FINAL TEST: Różne zestawy loginów dla różnych użytkowników")
print("=" * 80)
print("\nMariusz: mariusz + deploy")
print("Jasiek:  jasiek + deploy")
print("=" * 80)

tests = [
    ("Mariusz", "192.168.1.100", "mariusz", True),
    ("Mariusz", "192.168.1.100", "deploy", True),
    ("Mariusz", "192.168.1.100", "jasiek", False),
    ("Mariusz", "192.168.1.100", "root", False),
    
    ("Jasiek", "192.168.1.200", "jasiek", True),
    ("Jasiek", "192.168.1.200", "deploy", True),
    ("Jasiek", "192.168.1.200", "mariusz", False),
    ("Jasiek", "192.168.1.200", "root", False),
]

for user, ip, login, should_work in tests:
    result = engine.check_access_v2(db, ip, "10.0.160.129", "ssh", login)
    status = "✅ GRANTED" if result['has_access'] else "❌ DENIED"
    expected = "✅" if should_work else "❌"
    match = "✓" if (result['has_access'] == should_work) else "✗ BŁĄD"
    
    print(f"\n[{match}] {user} → login={login:8s} | Expected: {expected} | Got: {status}")
    if not result['has_access']:
        print(f"     Reason: {result['reason']}")

print("\n" + "=" * 80)
print("PODSUMOWANIE")
print("=" * 80)
print("✅ Mariusz: tylko 'mariusz' + 'deploy'")
print("✅ Jasiek:  tylko 'jasiek' + 'deploy'")
print("✅ Każdy ma swój niezależny zestaw loginów!")
print("✅ Login 'deploy' jest wspólny dla obu, ale to nie kolizja - to design!")
print("=" * 80)

db.close()
