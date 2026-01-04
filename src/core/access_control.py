"""Access Control Engine - verifies user permissions and manages access."""
from datetime import datetime
from typing import Optional, Tuple, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging

from .database import User, Server, AccessGrant, AuditLog, IPAllocation

logger = logging.getLogger(__name__)


class AccessControlEngine:
    """Manages access control and authorization."""
    
    def find_backend_by_proxy_ip(
        self,
        db: Session,
        proxy_ip: str
    ) -> Optional[Dict]:
        """
        Find backend server by proxy IP address (destination IP).
        
        Looks up in ip_allocations table to find which backend server
        is assigned to this proxy IP.
        
        Args:
            db: Database session
            proxy_ip: Destination IP that client connected to
            
        Returns:
            Dict with server info or None if not found
            {
                'server': Server object,
                'allocation': IPAllocation object
            }
        """
        try:
            allocation = db.query(IPAllocation).filter(
                and_(
                    IPAllocation.allocated_ip == proxy_ip,
                    IPAllocation.is_active == True
                )
            ).first()
            
            if not allocation:
                logger.warning(f"No active IP allocation found for proxy IP {proxy_ip}")
                return None
            
            server = db.query(Server).filter(
                Server.id == allocation.server_id,
                Server.is_active == True
            ).first()
            
            if not server:
                logger.error(f"Server ID {allocation.server_id} not found or inactive for IP {proxy_ip}")
                return None
            
            logger.info(f"Proxy IP {proxy_ip} maps to backend server {server.ip_address} (ID: {server.id})")
            return {
                'server': server,
                'allocation': allocation
            }
            
        except Exception as e:
            logger.error(f"Error looking up backend for proxy IP {proxy_ip}: {e}", exc_info=True)
            return None
    
    def check_access(
        self,
        db: Session,
        source_ip: str,
        username: Optional[str] = None
    ) -> dict:
        """
        Check if source IP (+ optional username) has access to any server.
        
        For SSH: username is required and checked
        For RDP: username is None, we identify user only by source_ip
        
        Returns dict with has_access, user, server, grant, and reason.
        """
        try:
            # Find user by source_ip or username+source_ip
            if username is None:
                # RDP mode: identify user by source_ip only
                user = db.query(User).filter(
                    User.source_ip == source_ip,
                    User.is_active == True
                ).first()
                
                if not user:
                    return {
                        'has_access': False,
                        'reason': f"No user found for source IP {source_ip}",
                        'user': None,
                        'server': None
                    }
            else:
                # SSH mode: find by username and verify source_ip
                user = db.query(User).filter(
                    User.username == username,
                    User.is_active == True
                ).first()
                
                if not user:
                    return {
                        'has_access': False,
                        'reason': f"User {username} not found or inactive",
                        'user': None,
                        'server': None
                    }
                
                # If user has source_ip set, verify it matches
                if user.source_ip and user.source_ip != source_ip:
                    logger.warning(f"Source IP mismatch for {username}: expected {user.source_ip}, got {source_ip}")
                    return {
                        'has_access': False,
                        'reason': f"Source IP {source_ip} not authorized for user {username}",
                        'user': None,
                        'server': None
                    }
            
            # Find active access grant for this user
            now = datetime.utcnow()
            grant = db.query(AccessGrant).filter(
                and_(
                    AccessGrant.user_id == user.id,
                    AccessGrant.is_active == True,
                    AccessGrant.start_time <= now,
                    AccessGrant.end_time >= now
                )
            ).first()
            
            if not grant:
                return {
                    'has_access': False,
                    'reason': f"No active access grant for {username}",
                    'user': user,
                    'server': None
                }
            
            # Get server from grant
            server = db.query(Server).filter(
                Server.id == grant.server_id,
                Server.is_active == True
            ).first()
            
            if not server:
                return {
                    'has_access': False,
                    'reason': "Target server not found or inactive",
                    'user': user,
                    'server': None
                }
            
            # Access granted!
            logger.info(f"Access granted: {username} ({source_ip}) → {server.ip_address}")
            return {
                'has_access': True,
                'reason': 'Access granted',
                'user': user,
                'server': server,
                'grant': grant
            }
            
        except Exception as e:
            logger.error(f"Error checking access: {e}")
            return {
                'has_access': False,
                'reason': f"Internal error: {str(e)}",
                'user': None,
                'server': None
            }
    
    def verify_access(
        self,
        db: Session,
        username: str,
        server_ip: str,
        protocol: str,
        source_ip: str
    ) -> Tuple[bool, Optional[str], Optional[dict]]:
        """
        Verify if user has access to server.
        
        Args:
            db: Database session
            username: Username attempting access
            server_ip: Target server IP
            protocol: 'ssh' or 'rdp'
            source_ip: Client source IP
            
        Returns:
            Tuple of (has_access: bool, reason: str, grant_info: dict)
        """
        try:
            # Check if user exists and is active
            user = db.query(User).filter(
                User.username == username,
                User.is_active == True
            ).first()
            
            if not user:
                self._log_access_attempt(
                    db, None, None, source_ip, protocol, False, 
                    f"User {username} not found or inactive"
                )
                return False, "User not found or inactive", None
            
            # Check if server exists and is active
            server = db.query(Server).filter(
                Server.ip_address == server_ip,
                Server.is_active == True
            ).first()
            
            if not server:
                self._log_access_attempt(
                    db, user.id, None, source_ip, protocol, False,
                    f"Server {server_ip} not found or inactive"
                )
                return False, "Server not found or inactive", None
            
            # Check for active access grant
            now = datetime.utcnow()
            grant = db.query(AccessGrant).filter(
                and_(
                    AccessGrant.user_id == user.id,
                    AccessGrant.server_id == server.id,
                    AccessGrant.protocol == protocol,
                    AccessGrant.is_active == True,
                    AccessGrant.start_time <= now,
                    AccessGrant.end_time >= now
                )
            ).first()
            
            if not grant:
                self._log_access_attempt(
                    db, user.id, server.id, source_ip, protocol, False,
                    f"No active access grant for {username} to {server_ip}"
                )
                return False, "No active access grant", None
            
            # Access granted!
            grant_info = {
                "user_id": user.id,
                "username": username,
                "server_id": server.id,
                "server_ip": server_ip,
                "server_name": server.name,
                "protocol": protocol,
                "grant_id": grant.id,
                "expires_at": grant.end_time.isoformat()
            }
            
            self._log_access_attempt(
                db, user.id, server.id, source_ip, protocol, True,
                f"Access granted to {username} for {server_ip}"
            )
            
            return True, "Access granted", grant_info
            
        except Exception as e:
            logger.error(f"Error verifying access: {str(e)}")
            return False, f"Internal error: {str(e)}", None
    
    def grant_access(
        self,
        db: Session,
        username: str,
        server_ip: str,
        protocol: str,
        duration_minutes: int,
        granted_by: str,
        reason: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Grant access to a user for a server.
        
        Args:
            db: Database session
            username: User to grant access to
            server_ip: Target server IP
            protocol: 'ssh' or 'rdp'
            duration_minutes: How long access should last
            granted_by: Who is granting the access
            reason: Optional reason for granting access
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Get user
            user = db.query(User).filter(User.username == username).first()
            if not user:
                return False, f"User {username} not found"
            
            # Get server
            server = db.query(Server).filter(Server.ip_address == server_ip).first()
            if not server:
                return False, f"Server {server_ip} not found"
            
            # Create access grant
            from datetime import timedelta
            start_time = datetime.utcnow()
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            grant = AccessGrant(
                user_id=user.id,
                server_id=server.id,
                protocol=protocol,
                start_time=start_time,
                end_time=end_time,
                is_active=True,
                granted_by=granted_by,
                reason=reason
            )
            
            db.add(grant)
            db.commit()
            
            # Log the action
            self._log_action(
                db, user.id, "grant_access", "access_grant", grant.id,
                None, True, f"Access granted by {granted_by} for {duration_minutes} minutes"
            )
            
            return True, f"Access granted until {end_time.isoformat()}"
            
        except Exception as e:
            logger.error(f"Error granting access: {str(e)}")
            db.rollback()
            return False, f"Failed to grant access: {str(e)}"
    
    def revoke_access(
        self,
        db: Session,
        username: str,
        server_ip: str,
        protocol: str,
        revoked_by: str
    ) -> Tuple[bool, str]:
        """
        Revoke access for a user to a server.
        
        Args:
            db: Database session
            username: User to revoke access from
            server_ip: Target server IP
            protocol: 'ssh' or 'rdp'
            revoked_by: Who is revoking the access
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Get user and server
            user = db.query(User).filter(User.username == username).first()
            if not user:
                return False, f"User {username} not found"
            
            server = db.query(Server).filter(Server.ip_address == server_ip).first()
            if not server:
                return False, f"Server {server_ip} not found"
            
            # Find and deactivate active grants
            grants = db.query(AccessGrant).filter(
                and_(
                    AccessGrant.user_id == user.id,
                    AccessGrant.server_id == server.id,
                    AccessGrant.protocol == protocol,
                    AccessGrant.is_active == True
                )
            ).all()
            
            if not grants:
                return False, "No active access grant found"
            
            for grant in grants:
                grant.is_active = False
            
            db.commit()
            
            # Log the action
            self._log_action(
                db, user.id, "revoke_access", "access_grant", None,
                None, True, f"Access revoked by {revoked_by}"
            )
            
            return True, f"Access revoked for {len(grants)} grant(s)"
            
        except Exception as e:
            logger.error(f"Error revoking access: {str(e)}")
            db.rollback()
            return False, f"Failed to revoke access: {str(e)}"
    
    def _log_access_attempt(
        self,
        db: Session,
        user_id: Optional[int],
        server_id: Optional[int],
        source_ip: str,
        protocol: str,
        success: bool,
        details: str
    ):
        """Log access attempt to audit log."""
        try:
            log = AuditLog(
                user_id=user_id,
                action="access_attempt",
                resource_type="server",
                resource_id=server_id,
                source_ip=source_ip,
                success=success,
                details=f"[{protocol}] {details}"
            )
            db.add(log)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to log access attempt: {str(e)}")
    
    def _log_action(
        self,
        db: Session,
        user_id: int,
        action: str,
        resource_type: str,
        resource_id: Optional[int],
        source_ip: Optional[str],
        success: bool,
        details: str
    ):
        """Log administrative action to audit log."""
        try:
            log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                source_ip=source_ip,
                success=success,
                details=details
            )
            db.add(log)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to log action: {str(e)}")


# Singleton instance
access_control = AccessControlEngine()
