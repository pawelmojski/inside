"""Access Control Engine V2 - New flexible policy-based system."""
from datetime import datetime
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import logging

from .database import (
    User, Server, AccessGrant, AuditLog, IPAllocation,
    UserSourceIP, ServerGroup, ServerGroupMember, AccessPolicy, PolicySSHLogin,
    UserGroup, UserGroupMember, PolicySchedule, get_all_user_groups, get_all_server_groups
)
from .schedule_checker import check_policy_schedules

logger = logging.getLogger(__name__)


class AccessControlEngineV2:
    """New flexible policy-based access control system."""
    
    def find_backend_by_proxy_ip(
        self,
        db: Session,
        proxy_ip: str,
        gate_id: int
    ) -> Optional[Dict]:
        """
        Find backend server by proxy IP address (destination IP) on specific gate.
        
        Supports two modes:
        1. NAT mode: proxy_ip is from IP pool → lookup via ip_allocations
        2. TPROXY mode: proxy_ip is real server IP → lookup directly in servers table
        
        Looks up in ip_allocations table to find which backend server
        is assigned to this proxy IP on the given gate. Same IP can exist
        on multiple gates pointing to different servers.
        
        If not found in allocations, tries direct lookup by server IP (TPROXY mode).
        
        Args:
            db: Database session
            proxy_ip: Destination IP that client connected to (pool IP or real server IP)
            gate_id: ID of the gate that received the connection
            
        Returns:
            Dict with server info or None if not found
            {
                'server': Server object,
                'allocation': IPAllocation object or None (None for TPROXY)
            }
        """
        try:
            # First try NAT mode: lookup via IP pool allocations
            allocation = db.query(IPAllocation).filter(
                and_(
                    IPAllocation.allocated_ip == proxy_ip,
                    IPAllocation.gate_id == gate_id,
                    IPAllocation.is_active == True
                )
            ).first()
            
            if allocation:
                # Found in IP pool - NAT mode
                server = db.query(Server).filter(
                    Server.id == allocation.server_id,
                    Server.is_active == True
                ).first()
                
                if not server:
                    logger.error(f"Server ID {allocation.server_id} not found or inactive for pool IP {proxy_ip}")
                    return None
                
                logger.info(f"NAT mode: Pool IP {proxy_ip} on gate {gate_id} maps to server {server.ip_address} (ID: {server.id})")
                return {
                    'server': server,
                    'allocation': allocation
                }
            
            # Not found in pool - try TPROXY mode: direct server IP lookup
            server = db.query(Server).filter(
                Server.ip_address == proxy_ip,
                Server.is_active == True
            ).first()
            
            if server:
                logger.info(f"TPROXY mode: Direct IP {proxy_ip} maps to server {server.name} (ID: {server.id})")
                return {
                    'server': server,
                    'allocation': None  # No allocation in TPROXY mode
                }
            
            # Not found in either mode
            logger.warning(f"No backend found for destination IP {proxy_ip} (tried NAT pool and TPROXY direct lookup)")
            return None
            
        except Exception as e:
            logger.error(f"Error looking up backend for destination IP {proxy_ip} on gate {gate_id}: {e}", exc_info=True)
            return None
    
    def check_schedule_access(
        self,
        db: Session,
        policy: 'AccessPolicy',
        check_time: Optional[datetime] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Check if policy allows access at given time based on schedules.
        
        Args:
            db: Database session
            policy: AccessPolicy object
            check_time: Time to check (default: now)
        
        Returns:
            (has_access: bool, reason: str or None)
            - If use_schedules=False: (True, None) - schedule checking disabled
            - If no schedules defined: (True, None) - allow access
            - If schedule matches: (True, schedule_name)
            - If no schedule matches: (False, "Outside allowed time windows")
        """
        if not policy.use_schedules:
            # Schedule-based access disabled for this policy
            return (True, None)
        
        # Get all schedules for this policy
        schedules = db.query(PolicySchedule).filter(
            PolicySchedule.policy_id == policy.id,
            PolicySchedule.is_active == True
        ).all()
        
        # Convert to dict format for checker
        schedule_dicts = []
        for s in schedules:
            schedule_dicts.append({
                'name': s.name,
                'weekdays': s.weekdays,
                'time_start': s.time_start,
                'time_end': s.time_end,
                'months': s.months,
                'days_of_month': s.days_of_month,
                'timezone': s.timezone,
                'is_active': s.is_active
            })
        
        matches, matched_name = check_policy_schedules(schedule_dicts, check_time)
        
        if not matches:
            return (False, "Outside allowed time windows")
        
        return (True, matched_name)
    
    def check_access_v2(
        self,
        db: Session,
        source_ip: str,
        dest_ip: str,
        protocol: str,
        gate_id: int,
        ssh_login: Optional[str] = None,
        check_time: Optional[datetime] = None
    ) -> dict:
        """
        New flexible policy-based access control.
        
        Args:
            db: Database session
            source_ip: Client's source IP address
            dest_ip: Destination proxy IP (to identify target server)
            protocol: 'ssh' or 'rdp'
            gate_id: ID of the gate that received the connection
            ssh_login: SSH login name (only for SSH protocol)
            check_time: Time to check access (default: now/utcnow)
            
        Returns:
            dict with:
                - has_access: bool
                - user: User object or None
                - user_ip: UserSourceIP object or None
                - server: Server object or None
                - policies: List of matching AccessPolicy objects
                - reason: str explaining decision
        """
        # Default to now if not provided
        if check_time is None:
            check_time = datetime.utcnow()
        
        try:
            # Step 0: Check gate maintenance mode FIRST
            from .database import Gate, MaintenanceAccess
            gate = db.query(Gate).filter(Gate.id == gate_id).first()
            
            if gate and gate.in_maintenance and gate.maintenance_scheduled_at:
                from datetime import timedelta
                now = check_time
                grace_start = gate.maintenance_scheduled_at - timedelta(minutes=gate.maintenance_grace_minutes)
                
                # Check if in grace period or active maintenance
                if now >= grace_start:
                    # Find user first to check maintenance access
                    user_ip = db.query(UserSourceIP).filter(
                        UserSourceIP.source_ip == source_ip,
                        UserSourceIP.is_active == True
                    ).first()
                    
                    user = None
                    if user_ip:
                        user = db.query(User).filter(
                            User.id == user_ip.user_id,
                            User.is_active == True
                        ).first()
                    
                    # Check if user has maintenance access
                    has_maintenance_access = False
                    if user:
                        has_maintenance_access = db.query(MaintenanceAccess).filter(
                            MaintenanceAccess.entity_type == 'gate',
                            MaintenanceAccess.entity_id == gate_id,
                            MaintenanceAccess.person_id == user.id
                        ).first() is not None
                    
                    if not has_maintenance_access:
                        # In grace period or maintenance - deny access
                        if now >= gate.maintenance_scheduled_at:
                            reason = f"Gate in maintenance mode: {gate.maintenance_reason}"
                            denial_reason = 'gate_maintenance'
                        else:
                            minutes_until = int((gate.maintenance_scheduled_at - now).total_seconds() / 60)
                            reason = f"Gate entering maintenance in {minutes_until} minutes"
                            denial_reason = 'maintenance_grace_period'
                        
                        logger.warning(f"Access denied: {reason}")
                        return {
                            'has_access': False,
                            'user': user,
                            'user_ip': user_ip if user else None,
                            'server': None,
                            'policies': [],
                            'selected_policy': None,
                            'denial_reason': denial_reason,
                            'reason': reason
                        }
            
            # Step 1: Find user by source_ip or special markers
            user = None
            user_ip = None
            
            # Check if this is a special authentication marker
            if source_ip.startswith('_fingerprint_') or source_ip.startswith('_identified_user_') or source_ip.startswith('_stay_'):
                # Extract user_id from marker formats:
                # _fingerprint_{user_id} (legacy)
                # _identified_user_{user_id} (MFA/known IP identified)
                # _stay_{stay_id} (active Stay - need to lookup user)
                try:
                    if source_ip.startswith('_stay_'):
                        # Lookup user from Stay: _stay_{stay_id}
                        stay_id = int(source_ip.split('_')[2])
                        from src.core.database import Stay
                        stay = db.query(Stay).filter(Stay.id == stay_id).first()
                        if not stay:
                            logger.error(f"Stay ID {stay_id} not found")
                            return {
                                'has_access': False,
                                'user': None,
                                'user_ip': None,
                                'server': None,
                                'policies': [],
                                'selected_policy': None,
                                'denial_reason': 'stay_not_found',
                                'reason': 'Stay not found'
                            }
                        user_id = stay.user_id
                    elif source_ip.startswith('_identified_user_'):
                        # Extract user_id: _identified_user_{user_id}
                        user_id = int(source_ip.split('_')[3])
                    else:
                        # Legacy: _fingerprint_{user_id}
                        user_id = int(source_ip.split('_')[2])
                    
                    user = db.query(User).filter(
                        User.id == user_id,
                        User.is_active == True
                    ).first()
                    
                    if not user:
                        logger.warning(f"Access denied: User ID {user_id} from marker not found or inactive")
                        return {
                            'has_access': False,
                            'user': None,
                            'user_ip': None,
                            'server': None,
                            'policies': [],
                            'selected_policy': None,
                            'denial_reason': 'user_inactive',
                            'reason': f'User not found or inactive'
                        }
                    
                    logger.info(f"User identified via marker: {user.username} (ID: {user.id}, marker: {source_ip.split('_')[1]})")
                    # user_ip remains None - this is marker-based auth, not IP-based
                    
                except (IndexError, ValueError) as e:
                    logger.error(f"Invalid marker format: {source_ip}")
                    return {
                        'has_access': False,
                        'user': None,
                        'user_ip': None,
                        'server': None,
                        'policies': [],
                        'selected_policy': None,
                        'denial_reason': 'invalid_marker',
                        'reason': 'Invalid authentication marker'
                    }
            else:
                # Normal IP-based authentication
                user_ip = db.query(UserSourceIP).filter(
                    UserSourceIP.source_ip == source_ip,
                    UserSourceIP.is_active == True
                ).first()
                
                if not user_ip:
                    logger.warning(f"Access denied: Unknown source IP {source_ip}")
                    return {
                        'has_access': False,
                        'user': None,
                        'user_ip': None,
                        'server': None,
                        'policies': [],
                        'selected_policy': None,
                        'denial_reason': 'unknown_source_ip',
                        'reason': f'Unknown source IP {source_ip}'
                    }
                
                user = db.query(User).filter(
                    User.id == user_ip.user_id,
                    User.is_active == True
                ).first()
                
                if not user:
                    logger.warning(f"Access denied: User ID {user_ip.user_id} not found or inactive")
                    return {
                        'has_access': False,
                        'user': None,
                        'user_ip': user_ip,
                        'server': None,
                        'policies': [],
                        'selected_policy': None,
                        'denial_reason': 'user_inactive',
                        'reason': f'User not found or inactive'
                    }
            
            # Step 2: Find backend server by dest_ip on this gate
            backend_info = self.find_backend_by_proxy_ip(db, dest_ip, gate_id)
            if not backend_info:
                logger.warning(f"Access denied: No backend found for destination IP {dest_ip} on gate {gate_id}")
                return {
                    'has_access': False,
                    'user': user,
                    'user_ip': user_ip,
                    'server': None,
                    'policies': [],
                    'selected_policy': None,
                    'denial_reason': 'server_not_found',
                    'reason': f'No backend server for destination IP {dest_ip}'
                }
            
            server = backend_info['server']
            
            # Step 2b: Check backend server maintenance mode
            if server.in_maintenance and server.maintenance_scheduled_at:
                from datetime import timedelta
                now = check_time
                grace_start = server.maintenance_scheduled_at - timedelta(minutes=server.maintenance_grace_minutes)
                
                # Check if in grace period or active maintenance
                if now >= grace_start:
                    # Check if user has maintenance access to this server
                    has_maintenance_access = db.query(MaintenanceAccess).filter(
                        MaintenanceAccess.entity_type == 'server',
                        MaintenanceAccess.entity_id == server.id,
                        MaintenanceAccess.person_id == user.id
                    ).first() is not None
                    
                    if not has_maintenance_access:
                        # In grace period or maintenance - deny access
                        if now >= server.maintenance_scheduled_at:
                            reason = f"Server in maintenance mode: {server.maintenance_reason}"
                            denial_reason = 'backend_maintenance'
                        else:
                            minutes_until = int((server.maintenance_scheduled_at - now).total_seconds() / 60)
                            reason = f"Server entering maintenance in {minutes_until} minutes"
                            denial_reason = 'maintenance_grace_period'
                        
                        logger.warning(f"Access denied: {reason}")
                        return {
                            'has_access': False,
                            'user': user,
                            'user_ip': user_ip,
                            'server': server,
                            'policies': [],
                            'selected_policy': None,
                            'denial_reason': denial_reason,
                            'reason': reason
                        }
            
            # Step 3: Find matching policies with PRIORITY: user > group
            now = check_time
            
            # Get all server groups (including parent groups)
            server_group_ids = get_all_server_groups(server.id, db)
            
            # PRIORITY 1: Check for direct user policies first
            user_policies_query = db.query(AccessPolicy).filter(
                AccessPolicy.user_id == user.id,
                AccessPolicy.is_active == True,
                AccessPolicy.start_time <= now,
                or_(AccessPolicy.end_time == None, AccessPolicy.end_time >= now)
            ).filter(
                # Source IP match: NULL (all IPs) or specific user_source_ip_id
                # Note: user_ip can be None when using fingerprint-based authentication
                or_(
                    AccessPolicy.source_ip_id == None,
                    AccessPolicy.source_ip_id == user_ip.id if user_ip else None
                )
            ).filter(
                # Protocol match: NULL (all protocols) or specific
                or_(
                    AccessPolicy.protocol == None,
                    AccessPolicy.protocol == protocol
                )
            )
            
            # Check if user has direct policies for this server
            direct_user_policies = []
            for policy in user_policies_query:
                if policy.scope_type == 'group':
                    if policy.target_group_id in server_group_ids:
                        direct_user_policies.append(policy)
                elif policy.scope_type in ('server', 'service'):
                    if policy.target_server_id == server.id:
                        direct_user_policies.append(policy)
            
            # If user has direct policies, use ONLY those (ignore group inheritance)
            if direct_user_policies:
                matching_policies = direct_user_policies
                logger.debug(f"Using {len(direct_user_policies)} direct user policies (ignoring groups)")
                
                # For SSH, filter by login BEFORE proceeding
                # If direct policy exists but login not allowed - DENY (no fallback to groups)
                if protocol == 'ssh' and ssh_login:
                    valid_policies = []
                    for policy in matching_policies:
                        allowed_logins = db.query(PolicySSHLogin).filter(
                            PolicySSHLogin.policy_id == policy.id
                        ).all()
                        
                        # No restrictions = all logins allowed
                        if not allowed_logins:
                            valid_policies.append(policy)
                        else:
                            # Check if requested login is in allowed list
                            for login in allowed_logins:
                                if login.allowed_login == ssh_login:
                                    valid_policies.append(policy)
                                    break
                    
                    if not valid_policies:
                        logger.warning(
                            f"Access denied: Login '{ssh_login}' not allowed for {user.username} "
                            f"to {server.name} (user has direct policy, group inheritance blocked)"
                        )
                        return {
                            'has_access': False,
                            'user': user,
                            'user_ip': user_ip,
                            'server': server,
                            'policies': matching_policies,
                            'selected_policy': matching_policies[0] if matching_policies else None,
                            'denial_reason': 'ssh_login_not_allowed',
                            'reason': f'SSH login "{ssh_login}" not allowed by direct user policy'
                        }
                    
                    matching_policies = valid_policies
            else:
                # PRIORITY 2: No direct user policies, check group policies
                user_group_ids = get_all_user_groups(user.id, db)
                
                if not user_group_ids:
                    logger.warning(
                        f"Access denied: No direct policies and no groups for {user.username}"
                    )
                    return {
                        'has_access': False,
                        'user': user,
                        'user_ip': user_ip,
                        'server': server,
                        'policies': [],
                        'selected_policy': None,
                        'denial_reason': 'no_matching_policy',
                        'reason': 'No matching policy (user or group)'
                    }
                
                group_policies_query = db.query(AccessPolicy).filter(
                    AccessPolicy.user_group_id.in_(user_group_ids),
                    AccessPolicy.is_active == True,
                    AccessPolicy.start_time <= now,
                    or_(AccessPolicy.end_time == None, AccessPolicy.end_time >= now)
                ).filter(
                    # Protocol match: NULL (all protocols) or specific
                    or_(
                        AccessPolicy.protocol == None,
                        AccessPolicy.protocol == protocol
                    )
                )
                
                matching_policies = []
                for policy in group_policies_query:
                    if policy.scope_type == 'group':
                        if policy.target_group_id in server_group_ids:
                            matching_policies.append(policy)
                    elif policy.scope_type in ('server', 'service'):
                        if policy.target_server_id == server.id:
                            matching_policies.append(policy)
                
                logger.debug(f"Using {len(matching_policies)} group policies (no direct user policies)")
            
            if not matching_policies:
                logger.warning(
                    f"Access denied: No matching policy for {user.username} "
                    f"from {source_ip} to {server.name} ({protocol})"
                )
                return {
                    'has_access': False,
                    'user': user,
                    'user_ip': user_ip,
                    'server': server,
                    'policies': [],
                    'selected_policy': None,
                    'denial_reason': 'no_matching_policy',
                    'reason': f'No matching access policy'
                }
            
            # Step 3.5: Filter policies by schedule (if use_schedules enabled)
            schedule_filtered_policies = []
            for policy in matching_policies:
                schedule_ok, schedule_name = self.check_schedule_access(db, policy, now)
                if schedule_ok:
                    schedule_filtered_policies.append(policy)
                    if schedule_name:
                        logger.debug(f"Policy {policy.id} schedule matched: {schedule_name}")
                else:
                    logger.debug(f"Policy {policy.id} schedule check failed: outside time window")
            
            if not schedule_filtered_policies:
                logger.warning(
                    f"Access denied: No policy active at this time for {user.username} "
                    f"from {source_ip} to {server.name} ({protocol})"
                )
                return {
                    'has_access': False,
                    'user': user,
                    'user_ip': user_ip,
                    'server': server,
                    'policies': matching_policies,  # Show which policies exist but are inactive
                    'selected_policy': matching_policies[0] if matching_policies else None,
                    'denial_reason': 'outside_schedule',
                    'reason': 'Outside allowed time windows'
                }
            
            matching_policies = schedule_filtered_policies
            
            # Step 4: For SSH with group policies, check login restrictions
            # (Direct user policies already filtered ssh_login above)
            if protocol == 'ssh' and ssh_login and not direct_user_policies:
                valid_policies = []
                for policy in matching_policies:
                    allowed_logins = db.query(PolicySSHLogin).filter(
                        PolicySSHLogin.policy_id == policy.id
                    ).all()
                    
                    # No restrictions = all logins allowed
                    if not allowed_logins:
                        valid_policies.append(policy)
                    else:
                        # Check if requested login is in allowed list
                        for login in allowed_logins:
                            if login.allowed_login == ssh_login:
                                valid_policies.append(policy)
                                break
                
                if not valid_policies:
                    logger.warning(
                        f"Access denied: Login '{ssh_login}' not allowed for {user.username} "
                        f"to {server.name} (group policies)"
                    )
                    return {
                        'has_access': False,
                        'user': user,
                        'user_ip': user_ip,
                        'server': server,
                        'policies': matching_policies,
                        'selected_policy': matching_policies[0] if matching_policies else None,
                        'denial_reason': 'ssh_login_not_allowed',
                        'reason': f'SSH login "{ssh_login}" not allowed by group policy'
                    }
                
                matching_policies = valid_policies
            
            # Success!
            logger.info(
                f"Access granted: {user.username} from {source_ip} "
                f"to {server.name} ({protocol}" +
                (f", login={ssh_login}" if ssh_login else "") + 
                f") - {len(matching_policies)} matching policies"
            )
            
            # Calculate effective end time (earliest of: policy end_time or schedule window end)
            effective_end_time = None
            policy_end_times = [p.end_time for p in matching_policies if p.end_time]
            
            if policy_end_times:
                # Get earliest policy end_time
                earliest_policy_end = min(policy_end_times)
                effective_end_time = earliest_policy_end
                
                # Check if any policy has schedules - find earliest schedule window end
                from src.core.schedule_checker import get_earliest_schedule_end
                
                for policy in matching_policies:
                    if policy.use_schedules:
                        # Get schedules for this policy
                        schedule_rules = []
                        for s in policy.schedules:
                            if s.is_active:
                                schedule_rules.append({
                                    'name': s.name,
                                    'weekdays': s.weekdays,
                                    'time_start': s.time_start,
                                    'time_end': s.time_end,
                                    'months': s.months,
                                    'days_of_month': s.days_of_month,
                                    'timezone': s.timezone,
                                    'is_active': s.is_active
                                })
                        
                        if schedule_rules:
                            schedule_end = get_earliest_schedule_end(schedule_rules, now)
                            if schedule_end:
                                # Use earliest of: policy end_time or schedule window end
                                if effective_end_time is None or schedule_end < effective_end_time:
                                    effective_end_time = schedule_end
                                    logger.info(f"Effective end_time adjusted to schedule window end: {schedule_end}")
            
            # Select first matching policy for session tracking (OR logic - any policy grants access)
            selected_policy = matching_policies[0] if matching_policies else None
            
            return {
                'has_access': True,
                'user': user,
                'user_ip': user_ip,
                'server': server,
                'policies': matching_policies,
                'selected_policy': selected_policy,  # NEW v1.7.5: First matching policy for session tracking
                'reason': 'Access granted',
                'effective_end_time': effective_end_time  # NEW: earliest of policy end or schedule window end
            }
            
        except Exception as e:
            logger.error(f"Error checking access: {e}", exc_info=True)
            return {
                'has_access': False,
                'user': None,
                'user_ip': None,
                'server': None,
                'policies': [],
                'selected_policy': None,
                'denial_reason': 'internal_error',
                'reason': f'Internal error: {str(e)}'
            }
    
    def check_port_forwarding_allowed(self, db, source_ip: str, dest_ip: str, gate_id: int) -> bool:
        """Check if user has port forwarding permission for this server
        
        Returns True if ANY matching policy has port_forwarding_allowed=True
        """
        try:
            # Use check_access_v2 to get matching policies
            result = self.check_access_v2(db, source_ip, dest_ip, 'ssh', gate_id, None)
            
            if not result['has_access']:
                logger.warning(f"Port forwarding denied: No access to server")
                return False
            
            # Check if any policy allows port forwarding
            for policy in result['policies']:
                if policy.port_forwarding_allowed:
                    logger.info(f"Port forwarding allowed by policy {policy.id}")
                    return True
            
            logger.warning(f"Port forwarding denied: No policy allows it")
            return False
            
        except Exception as e:
            logger.error(f"Error checking port forwarding: {e}", exc_info=True)
            return False
    
    def check_access_legacy_fallback(
        self,
        db: Session,
        source_ip: str,
        username: Optional[str] = None
    ) -> dict:
        """
        Legacy access check using old access_grants table.
        Fallback for backward compatibility.
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
                    'reason': f"No active access grant",
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
                    'reason': f"Server not found or inactive",
                    'user': user,
                    'server': None
                }
            
            return {
                'has_access': True,
                'user': user,
                'server': server,
                'grant': grant,
                'reason': 'Access granted (legacy)'
            }
            
        except Exception as e:
            logger.error(f"Error in legacy access check: {e}", exc_info=True)
            return {
                'has_access': False,
                'user': None,
                'server': None,
                'reason': f'Internal error: {str(e)}'
            }
    
    def audit_access_attempt(
        self,
        db: Session,
        user_id: Optional[int],
        action: str,
        source_ip: str,
        destination: str,
        protocol: str,
        success: bool,
        details: Optional[str] = None
    ):
        """Log access attempt to audit log."""
        try:
            log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type='access_attempt',
                source_ip=source_ip,
                success=success,
                details=f"Protocol: {protocol}, Destination: {destination}. {details or ''}"
            )
            db.add(log)
            db.commit()
        except Exception as e:
            logger.error(f"Error logging audit: {e}", exc_info=True)
            db.rollback()
