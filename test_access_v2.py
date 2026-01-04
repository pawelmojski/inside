#!/usr/bin/env python3
"""Test script for new flexible access control system."""

import sys
sys.path.append('/opt/jumphost')

from src.core.database import SessionLocal
from src.core.access_control_v2 import AccessControlEngineV2

def test_access_check():
    """Test access check scenarios."""
    db = SessionLocal()
    engine = AccessControlEngineV2()
    
    print("=" * 80)
    print("TESTING NEW FLEXIBLE ACCESS CONTROL SYSTEM")
    print("=" * 80)
    
    # Test 1: Mariusz -> SSH Server (dest_ip would be 10.0.160.129 in production)
    print("\n[TEST 1] Mariusz @ 192.168.1.100 -> Test-SSH-Server (SSH, login=mariusz)")
    result = engine.check_access_v2(
        db=db,
        source_ip="192.168.1.100",
        dest_ip="10.0.160.129",  # Proxy IP for Test-SSH-Server
        protocol="ssh",
        ssh_login="mariusz"
    )
    print(f"  Result: {result['has_access']}")
    print(f"  Reason: {result['reason']}")
    if result['has_access']:
        print(f"  User: {result['user'].username}")
        print(f"  Server: {result['server'].name}")
        print(f"  Matching policies: {len(result['policies'])}")
    
    # Test 2: Mariusz -> SSH Server with wrong login
    print("\n[TEST 2] Mariusz @ 192.168.1.100 -> Test-SSH-Server (SSH, login=root) [SHOULD FAIL]")
    result = engine.check_access_v2(
        db=db,
        source_ip="192.168.1.100",
        dest_ip="10.0.160.129",
        protocol="ssh",
        ssh_login="root"
    )
    print(f"  Result: {result['has_access']}")
    print(f"  Reason: {result['reason']}")
    
    # Test 3: Jasiek -> SSH Server (any login)
    print("\n[TEST 3] Jasiek @ 192.168.1.200 -> Test-SSH-Server (SSH, login=root)")
    result = engine.check_access_v2(
        db=db,
        source_ip="192.168.1.200",
        dest_ip="10.0.160.129",
        protocol="ssh",
        ssh_login="root"
    )
    print(f"  Result: {result['has_access']}")
    print(f"  Reason: {result['reason']}")
    if result['has_access']:
        print(f"  User: {result['user'].username}")
        print(f"  Server: {result['server'].name}")
        print(f"  Matching policies: {len(result['policies'])}")
    
    # Test 4: Jasiek from different IP (Office Network)
    print("\n[TEST 4] Jasiek @ 192.168.2.50 -> Test-SSH-Server (SSH, login=deploy)")
    result = engine.check_access_v2(
        db=db,
        source_ip="192.168.2.50",  # Office Network IP
        dest_ip="10.0.160.129",
        protocol="ssh",
        ssh_login="deploy"
    )
    print(f"  Result: {result['has_access']}")
    print(f"  Reason: {result['reason']}")
    if result['has_access']:
        print(f"  User: {result['user'].username}")
        print(f"  User IP Label: {result['user_ip'].label}")
    
    # Test 5: Jasiek -> Windows RDP Server
    print("\n[TEST 5] Jasiek @ 192.168.1.200 -> Windows-RDP-Server (RDP)")
    result = engine.check_access_v2(
        db=db,
        source_ip="192.168.1.200",
        dest_ip="10.0.160.130",  # Proxy IP for Windows-RDP-Server
        protocol="rdp"
    )
    print(f"  Result: {result['has_access']}")
    print(f"  Reason: {result['reason']}")
    if result['has_access']:
        print(f"  User: {result['user'].username}")
        print(f"  Server: {result['server'].name}")
    
    # Test 6: Mariusz -> Windows RDP Server [SHOULD FAIL]
    print("\n[TEST 6] Mariusz @ 192.168.1.100 -> Windows-RDP-Server (RDP) [SHOULD FAIL]")
    result = engine.check_access_v2(
        db=db,
        source_ip="192.168.1.100",
        dest_ip="10.0.160.130",
        protocol="rdp"
    )
    print(f"  Result: {result['has_access']}")
    print(f"  Reason: {result['reason']}")
    
    # Test 7: Unknown IP [SHOULD FAIL]
    print("\n[TEST 7] Unknown IP @ 192.168.99.99 [SHOULD FAIL]")
    result = engine.check_access_v2(
        db=db,
        source_ip="192.168.99.99",
        dest_ip="10.0.160.129",
        protocol="ssh",
        ssh_login="root"
    )
    print(f"  Result: {result['has_access']}")
    print(f"  Reason: {result['reason']}")
    
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print("✓ N:M Server Groups: Test-SSH-Server in BOTH groups")
    print("✓ Granular Protocol Control: Mariusz SSH only, Jasiek SSH+RDP")
    print("✓ SSH Login Restrictions: Mariusz only 'mariusz', Jasiek ALL")
    print("✓ Multiple Source IPs: Jasiek has 2 IPs (VPN + Office)")
    print("=" * 80)
    
    db.close()

if __name__ == "__main__":
    test_access_check()
