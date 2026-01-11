"""IP Pool Manager - manages dynamic IP allocation from 10.0.160.128/25."""
import ipaddress
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_
import os
from dotenv import load_dotenv

from .database import IPAllocation, get_db

load_dotenv()


class IPPoolManager:
    """Manages IP pool allocation and deallocation."""
    
    def __init__(self, gate=None):
        """Initialize IP pool manager.
        
        Args:
            gate: Gate object with IP pool configuration. If None, uses env vars (legacy).
        """
        if gate and gate.ip_pool_network:
            # Use gate-specific configuration
            self.network = ipaddress.IPv4Network(gate.ip_pool_network)
            self.pool_start = ipaddress.IPv4Address(gate.ip_pool_start)
            self.pool_end = ipaddress.IPv4Address(gate.ip_pool_end)
        else:
            # Fallback to environment variables (legacy/default)
            self.network = ipaddress.IPv4Network(os.getenv("IP_POOL_NETWORK", "10.0.160.128/25"))
            self.pool_start = ipaddress.IPv4Address(os.getenv("IP_POOL_START", "10.0.160.129"))
            self.pool_end = ipaddress.IPv4Address(os.getenv("IP_POOL_END", "10.0.160.254"))
        
    def get_available_ips(self, db: Session, gate_id: Optional[int] = None) -> List[str]:
        """Get list of available IPs from the pool for a specific gate.
        
        Args:
            db: Database session
            gate_id: Optional gate ID to filter by (if None, checks all gates)
        
        Returns:
            List of available IP addresses
        """
        from sqlalchemy import or_
        
        # Get all currently allocated IPs for this gate (or all gates if gate_id=None)
        query = db.query(IPAllocation.allocated_ip).filter(
            IPAllocation.is_active == True,
            or_(
                IPAllocation.expires_at.is_(None),  # Permanent allocations
                IPAllocation.expires_at > datetime.utcnow()  # Active temporary allocations
            )
        )
        
        if gate_id is not None:
            query = query.filter(IPAllocation.gate_id == gate_id)
        
        allocated = query.all()
        allocated_ips = {ip[0] for ip in allocated}
        
        # Generate list of available IPs
        available = []
        current_ip = self.pool_start
        while current_ip <= self.pool_end:
            ip_str = str(current_ip)
            if ip_str not in allocated_ips:
                available.append(ip_str)
            current_ip += 1
        
        return available
    
    def allocate_permanent_ip(
        self,
        db: Session,
        server_id: int,
        gate_id: int = 1,  # Default to gate-1 for backward compatibility
        specific_ip: Optional[str] = None
    ) -> Optional[str]:
        """
        Allocate a permanent IP for a server on a specific gate (no expiration).
        
        IP pools are per-gate and can overlap between gates.
        The same IP (e.g., 10.0.160.129) can be used on multiple gates simultaneously.
        
        Used for static server assignments via CLI assign-proxy-ip command.
        
        Args:
            db: Database session
            server_id: Target server ID
            gate_id: Gate ID (IP pools are per-gate)
            specific_ip: Optional specific IP to allocate (must be in pool)
            
        Returns:
            Allocated IP address or None if pool is exhausted
        """
        if specific_ip:
            # Validate specific IP is in pool range
            from ipaddress import ip_address
            ip_obj = ip_address(specific_ip)
            if ip_obj < self.pool_start or ip_obj > self.pool_end:
                return None
            
            # Check if already allocated ON THIS GATE
            existing = db.query(IPAllocation).filter(
                IPAllocation.allocated_ip == specific_ip,
                IPAllocation.gate_id == gate_id,
                IPAllocation.is_active == True
            ).first()
            if existing:
                return None
            
            allocated_ip = specific_ip
        else:
            # Auto-allocate from available pool (for this gate)
            available_ips = self.get_available_ips(db, gate_id=gate_id)
            
            if not available_ips:
                return None
            
            allocated_ip = available_ips[0]
        
        # Create permanent allocation record (no user_id, source_ip, expires_at, session_id)
        allocation = IPAllocation(
            allocated_ip=allocated_ip,
            server_id=server_id,
            gate_id=gate_id,  # NEW: Assign to specific gate
            user_id=None,
            source_ip=None,
            allocated_at=datetime.utcnow(),
            expires_at=None,  # Permanent
            is_active=True,
            session_id=None
        )
        
        db.add(allocation)
        db.commit()
        db.refresh(allocation)
        
        return allocated_ip
    
    def allocate_ip(
        self,
        db: Session,
        server_id: int,
        user_id: int,
        source_ip: str,
        duration_minutes: int = 60,
        session_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Allocate an IP from the pool.
        
        Args:
            db: Database session
            server_id: Target server ID
            user_id: User ID requesting access
            source_ip: Client source IP address
            duration_minutes: How long to allocate the IP (default 60 minutes)
            session_id: Optional session identifier
            
        Returns:
            Allocated IP address or None if pool is exhausted
        """
        available_ips = self.get_available_ips(db)
        
        if not available_ips:
            return None
        
        # Take the first available IP
        allocated_ip = available_ips[0]
        expires_at = datetime.utcnow() + timedelta(minutes=duration_minutes)
        
        # Create allocation record
        allocation = IPAllocation(
            allocated_ip=allocated_ip,
            server_id=server_id,
            user_id=user_id,
            source_ip=source_ip,
            allocated_at=datetime.utcnow(),
            expires_at=expires_at,
            is_active=True,
            session_id=session_id
        )
        
        db.add(allocation)
        db.commit()
        db.refresh(allocation)
        
        return allocated_ip
    
    def release_ip(self, db: Session, allocated_ip: str) -> bool:
        """
        Release an allocated IP back to the pool.
        
        Args:
            db: Database session
            allocated_ip: IP address to release
            
        Returns:
            True if released successfully, False otherwise
        """
        allocation = db.query(IPAllocation).filter(
            IPAllocation.allocated_ip == allocated_ip,
            IPAllocation.is_active == True
        ).first()
        
        if allocation:
            allocation.is_active = False
            db.commit()
            return True
        
        return False
    
    def get_allocation_by_ip(self, db: Session, allocated_ip: str) -> Optional[IPAllocation]:
        """Get allocation information by allocated IP."""
        return db.query(IPAllocation).filter(
            IPAllocation.allocated_ip == allocated_ip,
            IPAllocation.is_active == True
        ).first()
    
    def get_allocation_by_source_ip(self, db: Session, source_ip: str) -> Optional[IPAllocation]:
        """Get active allocation by source IP."""
        return db.query(IPAllocation).filter(
            IPAllocation.source_ip == source_ip,
            IPAllocation.is_active == True,
            IPAllocation.expires_at > datetime.utcnow()
        ).first()
    
    def cleanup_expired(self, db: Session) -> int:
        """
        Cleanup expired IP allocations.
        
        Returns:
            Number of allocations cleaned up
        """
        expired = db.query(IPAllocation).filter(
            IPAllocation.is_active == True,
            IPAllocation.expires_at <= datetime.utcnow()
        ).all()
        
        count = 0
        for allocation in expired:
            allocation.is_active = False
            count += 1
        
        if count > 0:
            db.commit()
        
        return count
    
    def get_pool_status(self, db: Session) -> dict:
        """
        Get current pool status.
        
        Returns:
            Dictionary with pool statistics
        """
        total_ips = int(self.pool_end) - int(self.pool_start) + 1
        available_ips = len(self.get_available_ips(db))
        allocated_ips = total_ips - available_ips
        
        active_allocations = db.query(IPAllocation).filter(
            IPAllocation.is_active == True,
            IPAllocation.expires_at > datetime.utcnow()
        ).count()
        
        return {
            "total_ips": total_ips,
            "available_ips": available_ips,
            "allocated_ips": allocated_ips,
            "active_allocations": active_allocations,
            "utilization_percent": round((allocated_ips / total_ips) * 100, 2),
            "pool_network": str(self.network),
            "pool_range": f"{self.pool_start} - {self.pool_end}"
        }
    
    def extend_allocation(
        self,
        db: Session,
        allocated_ip: str,
        additional_minutes: int
    ) -> bool:
        """
        Extend the expiration time of an allocation.
        
        Args:
            db: Database session
            allocated_ip: IP address to extend
            additional_minutes: Additional time in minutes
            
        Returns:
            True if extended successfully, False otherwise
        """
        allocation = self.get_allocation_by_ip(db, allocated_ip)
        
        if allocation:
            allocation.expires_at += timedelta(minutes=additional_minutes)
            db.commit()
            return True
        
        return False


# Singleton instance
ip_pool_manager = IPPoolManager()


if __name__ == "__main__":
    """Test IP pool manager."""
    from database import SessionLocal
    
    db = SessionLocal()
    manager = IPPoolManager()
    
    print("IP Pool Status:")
    status = manager.get_pool_status(db)
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    print(f"\nAvailable IPs (first 10): {manager.get_available_ips(db)[:10]}")
    
    # Test allocation
    print("\nTesting IP allocation...")
    allocated = manager.allocate_ip(
        db=db,
        server_id=1,
        user_id=1,
        source_ip="192.168.1.100",
        duration_minutes=30
    )
    print(f"Allocated IP: {allocated}")
    
    # Check status again
    print("\nIP Pool Status after allocation:")
    status = manager.get_pool_status(db)
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    db.close()
