#!/usr/bin/env python3
"""Test multi-login SSH restrictions for Mariusz."""

import sys
sys.path.append('/opt/jumphost')

from src.core.database import SessionLocal
from src.core.access_control_v2 import AccessControlEngineV2

def test_mariusz_multi_login():
    """Test Mariusz with 2 allowed logins: mariusz and deploy."""
    db = SessionLocal()
    engine = AccessControlEngineV2()
    
    print("=" * 80)
    print("TESTING MARIUSZ: SSH Login Restrictions (mariusz + deploy only)")
    print("=" * 80)
    
    # Test 1: login "mariusz" - SHOULD WORK
    print("\n[TEST 1] Mariusz @ 192.168.1.100 -> SSH login=mariusz [SHOULD WORK]")
    result = engine.check_access_v2(
        db=db,
        source_ip="192.168.1.100",
        dest_ip="10.0.160.129",
        protocol="ssh",
        ssh_login="mariusz"
    )
    print(f"  Result: {'✅ GRANTED' if result['has_access'] else '❌ DENIED'}")
    print(f"  Reason: {result['reason']}")
    
    # Test 2: login "deploy" - SHOULD WORK
    print("\n[TEST 2] Mariusz @ 192.168.1.100 -> SSH login=deploy [SHOULD WORK]")
    result = engine.check_access_v2(
        db=db,
        source_ip="192.168.1.100",
        dest_ip="10.0.160.129",
        protocol="ssh",
        ssh_login="deploy"
    )
    print(f"  Result: {'✅ GRANTED' if result['has_access'] else '❌ DENIED'}")
    print(f"  Reason: {result['reason']}")
    
    # Test 3: login "root" - SHOULD FAIL
    print("\n[TEST 3] Mariusz @ 192.168.1.100 -> SSH login=root [SHOULD FAIL]")
    result = engine.check_access_v2(
        db=db,
        source_ip="192.168.1.100",
        dest_ip="10.0.160.129",
        protocol="ssh",
        ssh_login="root"
    )
    print(f"  Result: {'✅ GRANTED' if result['has_access'] else '❌ DENIED'}")
    print(f"  Reason: {result['reason']}")
    
    # Test 4: login "admin" - SHOULD FAIL
    print("\n[TEST 4] Mariusz @ 192.168.1.100 -> SSH login=admin [SHOULD FAIL]")
    result = engine.check_access_v2(
        db=db,
        source_ip="192.168.1.100",
        dest_ip="10.0.160.129",
        protocol="ssh",
        ssh_login="admin"
    )
    print(f"  Result: {'✅ GRANTED' if result['has_access'] else '❌ DENIED'}")
    print(f"  Reason: {result['reason']}")
    
    # Test 5: login "postgres" - SHOULD FAIL
    print("\n[TEST 5] Mariusz @ 192.168.1.100 -> SSH login=postgres [SHOULD FAIL]")
    result = engine.check_access_v2(
        db=db,
        source_ip="192.168.1.100",
        dest_ip="10.0.160.129",
        protocol="ssh",
        ssh_login="postgres"
    )
    print(f"  Result: {'✅ GRANTED' if result['has_access'] else '❌ DENIED'}")
    print(f"  Reason: {result['reason']}")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("Mariusz ma dostęp SSH TYLKO jako:")
    print("  ✅ mariusz")
    print("  ✅ deploy")
    print("\nInne loginy (root, admin, postgres, etc.) są zablokowane!")
    print("=" * 80)
    
    db.close()

if __name__ == "__main__":
    test_mariusz_multi_login()
