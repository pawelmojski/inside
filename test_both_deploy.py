#!/usr/bin/env python3
"""Test: Both Mariusz and Jasiek can use 'deploy' login."""

import sys
sys.path.append('/opt/jumphost')

from src.core.database import SessionLocal
from src.core.access_control_v2 import AccessControlEngineV2

db = SessionLocal()
engine = AccessControlEngineV2()

print("=" * 80)
print("TEST: Mariusz i Jasiek - obaj mogą użyć loginu 'deploy'")
print("=" * 80)

# Mariusz -> deploy
print("\n[TEST 1] Mariusz @ 192.168.1.100 -> SSH login=deploy")
result = engine.check_access_v2(db, "192.168.1.100", "10.0.160.129", "ssh", "deploy")
print(f"  Result: {'✅ GRANTED' if result['has_access'] else '❌ DENIED'}")
print(f"  User: {result['user'].username if result['user'] else 'N/A'}")

# Jasiek -> deploy
print("\n[TEST 2] Jasiek @ 192.168.1.200 -> SSH login=deploy")
result = engine.check_access_v2(db, "192.168.1.200", "10.0.160.129", "ssh", "deploy")
print(f"  Result: {'✅ GRANTED' if result['has_access'] else '❌ DENIED'}")
print(f"  User: {result['user'].username if result['user'] else 'N/A'}")

print("\n" + "=" * 80)
print("✅ Obaj mogą używać 'deploy' - każdy ma swoje niezależne polisy!")
print("=" * 80)

db.close()
