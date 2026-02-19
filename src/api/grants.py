"""Tower API - Grant (Access Policy) endpoints for Gate clients.

Gates use these endpoints to check authorization and fetch active grants.
"""

from datetime import datetime
from flask import Blueprint, request, jsonify
from sqlalchemy import and_, or_
import pytz
import logging
from src.api.auth import require_gate_auth, get_current_gate, get_db_session
from src.core.database import (
    AccessPolicy, User, Server, ServerGroup, UserSourceIP,
    PolicySchedule, UserGroup, UserGroupMember, ServerGroupMember
)

logger = logging.getLogger(__name__)

# Polish characters transliteration map for ASCII-only terminals
POLISH_TRANSLITERATION = {
    'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n', 'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z',
    'Ą': 'A', 'Ć': 'C', 'Ę': 'E', 'Ł': 'L', 'Ń': 'N', 'Ó': 'O', 'Ś': 'S', 'Ź': 'Z', 'Ż': 'Z'
}

def transliterate_polish(text: str) -> str:
    """Convert Polish diacritical characters to ASCII equivalents.
    
    For terminals that don't support UTF-8, converts characters like:
    Paweł Mojski -> Pawel Mojski
    """
    if not text:
        return text
    for pl_char, ascii_char in POLISH_TRANSLITERATION.items():
        text = text.replace(pl_char, ascii_char)
    return text

grants_bp = Blueprint('grants', __name__, url_prefix='/api/v1')


def check_schedule_access(grant: AccessPolicy, db) -> tuple[bool, str]:
    """Check if current time matches any active schedule for the grant.
    
    Returns:
        (allowed: bool, reason: str)
    """
    if not grant.use_schedules:
        return True, "No schedule restrictions"
    
    # Get all active schedules for this grant
    schedules = db.query(PolicySchedule).filter(
        PolicySchedule.policy_id == grant.id,
        PolicySchedule.is_active == True
    ).all()
    
    if not schedules:
        # If use_schedules=True but no schedules defined, deny access
        return False, "No active schedules defined for this grant"
    
    now_utc = datetime.utcnow()
    
    # Check each schedule - if ANY matches, allow access
    for schedule in schedules:
        # Get timezone-aware current time
        tz = pytz.timezone(schedule.timezone)
        now_local = pytz.utc.localize(now_utc).astimezone(tz)
        
        # Check weekday (0=Monday, 6=Sunday)
        if schedule.weekdays is not None:
            if now_local.weekday() not in schedule.weekdays:
                continue  # Wrong day of week
        
        # Check month
        if schedule.months is not None:
            if now_local.month not in schedule.months:
                continue  # Wrong month
        
        # Check day of month
        if schedule.days_of_month is not None:
            if now_local.day not in schedule.days_of_month:
                continue  # Wrong day of month
        
        # Check time range
        if schedule.time_start is not None and schedule.time_end is not None:
            current_time = now_local.time()
            
            # Handle time ranges that cross midnight
            if schedule.time_start <= schedule.time_end:
                # Normal range (e.g., 08:00 - 16:00)
                if not (schedule.time_start <= current_time <= schedule.time_end):
                    continue  # Outside time window
            else:
                # Crosses midnight (e.g., 22:00 - 02:00)
                if not (current_time >= schedule.time_start or current_time <= schedule.time_end):
                    continue  # Outside time window
        
        # All checks passed for this schedule
        return True, f"Matches schedule: {schedule.name or f'#{schedule.id}'}"
    
    # No schedule matched
    return False, f"Current time ({now_local.strftime('%Y-%m-%d %H:%M %Z')}) outside allowed windows"


@grants_bp.route('/auth/check', methods=['POST'])
@require_gate_auth
def check_grant():
    """Check if a person can access a server - FULL AccessControlV2 logic.
    
    Gate calls this when client connects. Tower does ALL the magic:
    - Maps destination_ip (from pool) to backend server
    - Finds person by source_ip
    - Checks grants (user policies > group policies)
    - Checks schedules (time windows)
    - Checks SSH login restrictions
    - Calculates effective end_time
    
    Request JSON:
        {
            "source_ip": "192.168.1.100",    # Client IP
            "destination_ip": "10.0.160.5",  # IP from pool (dest of SSH connection)
            "protocol": "ssh",               # "ssh" or "rdp"
            "ssh_login": "root"              # Optional: SSH username
        }
    
    Response:
        200 OK (ALLOWED): {
            "allowed": true,
            "person_id": 6,
            "person_username": "p.mojski",
            "person_fullname": "Pawel Mojski",
            "server_id": 1,
            "server_name": "Test-SSH-Server",
            "server_ip": "10.0.160.4",
            "grant_id": 30,
            "grant_scope": "service",
            "effective_end_time": "2026-01-07T18:00:00",
            "port_forwarding_allowed": true,
            "ssh_logins": ["p.mojski"],
            "reason": "Access granted"
        }
        
        403 Forbidden (DENIED): {
            "allowed": false,
            "denial_reason": "outside_schedule",
            "reason": "Outside allowed time windows",
            "details": "Grant exists but schedule requires Tuesday 00:00-18:00"
        }
        
        400 Bad Request: Missing parameters
    """
    from sqlalchemy import and_, or_
    
    gate = get_current_gate()
    db = get_db_session()
    
    data = request.get_json()
    logger.info(f"=== check_grant START === gate={gate.name if gate else 'None'}, data keys={list(data.keys()) if data else 'None'}")
    
    if not data:
        return jsonify({'error': 'missing_body', 'message': 'Request body required'}), 400
    
    source_ip = data.get('source_ip')
    destination_ip = data.get('destination_ip')
    protocol = data.get('protocol')
    ssh_login = data.get('ssh_login')
    ssh_key_fingerprint = data.get('ssh_key_fingerprint')  # Optional: for MFA session persistence
    mfa_token = data.get('mfa_token')  # Optional: verified MFA challenge token
    
    logger.info(f"check_grant params: source_ip={source_ip}, dest_ip={destination_ip}, protocol={protocol}, ssh_login={ssh_login}, fingerprint={ssh_key_fingerprint[:20] if ssh_key_fingerprint else None}, mfa_token={mfa_token[:20] if mfa_token else None}")
    
    if not source_ip or not destination_ip or not protocol:
        return jsonify({
            'error': 'missing_parameters',
            'message': 'Required: source_ip, destination_ip, protocol'
        }), 400
    
    if protocol not in ['ssh', 'rdp']:
        return jsonify({
            'error': 'invalid_protocol',
            'message': 'Protocol must be "ssh" or "rdp"'
        }), 400
    
    # MFA PHASE 2: User identification and Stay management
    # STEP 1: Identify user_id (required before Stay matching)
    user_id = None
    active_stay = None
    identification_method = None
    
    if gate.mfa_enabled:
        from src.core.database import UserSourceIP, Stay, MFAChallenge
        
        # Method A: Fingerprint match (if fingerprint provided)
        if ssh_key_fingerprint and not user_id:
            stay_by_fingerprint = db.query(Stay).filter(
                Stay.ssh_key_fingerprint == ssh_key_fingerprint,
                Stay.gate_id == gate.id,
                Stay.is_active == True
            ).first()
            
            if stay_by_fingerprint:
                user_id = stay_by_fingerprint.user_id
                active_stay = stay_by_fingerprint
                identification_method = 'fingerprint'
                logger.info(f"User identified by fingerprint: user_id={user_id}, stay_id={active_stay.id}")
        
        # Method B: Known source IP
        if not user_id:
            known_ip = db.query(UserSourceIP).filter(
                UserSourceIP.source_ip == source_ip,
                UserSourceIP.is_active == True
            ).first()
            
            if known_ip:
                user_id = known_ip.person_id
                identification_method = 'known_ip'
                logger.info(f"User identified by known IP: user_id={user_id}")
        
        # Method C: MFA token (verified challenge)
        if not user_id and mfa_token:
            challenge = db.query(MFAChallenge).filter(
                MFAChallenge.token == mfa_token,
                MFAChallenge.gate_id == gate.id,
                MFAChallenge.verified == True
            ).first()
            
            if challenge and challenge.user_id:
                user_id = challenge.user_id
                identification_method = 'mfa'
                logger.info(f"User identified by MFA token: user_id={user_id}")
                request.mfa_verified_user_id = user_id
                request.mfa_verified_fingerprint = ssh_key_fingerprint
            else:
                logger.warning(f"Invalid or unverified MFA token: {mfa_token[:20] if mfa_token else None}")
                return jsonify({
                    'allowed': False,
                    'mfa_required': True,
                    'error': 'invalid_mfa_token',
                    'message': 'MFA token invalid or not verified'
                }), 403
        
        # STEP 2: Check if user needs MFA (not identified yet)
        if not user_id:
            logger.info(f"User not identified (fingerprint={ssh_key_fingerprint[:20] if ssh_key_fingerprint else None}, known_ip=False) - MFA required")
            
            # Find backend server to include in response
            from src.core.access_control_v2 import AccessControlEngineV2
            engine = AccessControlEngineV2()
            backend_info = engine.find_backend_by_proxy_ip(db, destination_ip, gate.id)
            
            server_info = {}
            if backend_info and backend_info['server']:
                server = backend_info['server']
                server_info = {
                    'server_id': server.id,
                    'server_name': server.name,
                    'server_ip': server.ip_address
                }
            
            return jsonify({
                'allowed': False,
                'mfa_required': True,
                'reason': 'MFA authentication required - user not identified',
                'gate_id': gate.id,
                'gate_name': gate.name,
                'destination_ip': destination_ip,
                'ssh_login': ssh_login,
                **server_info
            }), 403
        
        # STEP 3: User identified - check/update Stay
        if not active_stay:
            # Check if user has active Stay on this Gate
            active_stay = db.query(Stay).filter(
                Stay.user_id == user_id,
                Stay.gate_id == gate.id,
                Stay.is_active == True
            ).first()
            
            if active_stay:
                logger.info(f"Found existing Stay for user_id={user_id}: stay_id={active_stay.id}")
        
        # STEP 4: Update Stay fingerprint if needed
        if active_stay:
            if not active_stay.ssh_key_fingerprint and ssh_key_fingerprint:
                # Stay has NULL fingerprint, but now user connected with key
                # Update Stay to enable future fingerprint-based persistence
                active_stay.ssh_key_fingerprint = ssh_key_fingerprint
                db.commit()
                logger.info(f"Updated Stay {active_stay.id} with fingerprint (upgrade from NULL)")
            
            # Use Stay for access check
            source_ip = f"_stay_{active_stay.id}"
            request.identified_stay = active_stay
        else:
            # No Stay yet - will be created after grant check passes
            # Use special marker for access engine
            source_ip = f"_identified_user_{user_id}"
            request.identified_user_id = user_id
            request.identified_fingerprint = ssh_key_fingerprint
    
    # Use AccessControlV2 engine - ALL the magic happens here!
    from src.core.access_control_v2 import AccessControlEngineV2
    engine = AccessControlEngineV2()
    
    result = engine.check_access_v2(
        db=db,
        source_ip=source_ip,
        dest_ip=destination_ip,
        protocol=protocol,
        gate_id=gate.id,
        ssh_login=ssh_login
    )
    
    if not result['has_access']:
        # Access DENIED
        denial_response = {
            'allowed': False,
            'denial_reason': result.get('denial_reason', 'access_denied'),
            'reason': result.get('reason', 'Access denied'),
            'details': result.get('reason', 'No additional details'),
            'gate_id': gate.id,
            'gate_name': gate.name
        }
        
        # Include person info if user was found (for custom denial messages)
        user = result.get('user')
        if user:
            denial_response['person_id'] = user.id
            denial_response['person_username'] = user.username
            # Transliterate Polish characters for ASCII-only terminals
            denial_response['person_fullname'] = transliterate_polish(user.full_name)
        
        # Include server info if server was found
        server = result.get('server')
        if server:
            denial_response['server_id'] = server.id
            denial_response['server_name'] = server.name
            denial_response['server_ip'] = server.ip_address
        
        # Check if there's an active session that should be force-disconnected
        # (used by heartbeat to terminate sessions when grant revoked/user deactivated)
        from src.core.database import Session as DBSession
        active_session = db.query(DBSession).filter(
            and_(
                DBSession.source_ip == source_ip,
                DBSession.proxy_ip == destination_ip,
                DBSession.protocol == protocol,
                DBSession.is_active == True
            )
        ).first()
        
        if active_session and active_session.termination_reason:
            # Session marked for termination - calculate disconnect_at
            # Default: disconnect in 5 seconds (grace period)
            from datetime import timedelta
            disconnect_at = datetime.utcnow() + timedelta(seconds=5)
            denial_response['disconnect_at'] = disconnect_at.isoformat()
        
        return jsonify(denial_response), 403
    
    # Access GRANTED
    user = result['user']
    server = result['server']
    selected_policy = result['selected_policy']
    
    # MFA Phase 2: Create Stay with fingerprint if user was just verified via MFA
    logger.info(f"DEBUG Stay creation: gate.mfa_enabled={gate.mfa_enabled}, ssh_key_fingerprint={ssh_key_fingerprint[:20] if ssh_key_fingerprint else None}")
    if gate.mfa_enabled and ssh_key_fingerprint:
        from src.core.database import Stay, MFAChallenge
        from datetime import datetime, timedelta
        
        logger.info(f"DEBUG: Querying for recent verified MFA challenge for user {user.id}, gate {gate.id}")
        # Check if user just completed MFA verification (within last 60 seconds)
        recent_verified_challenge = db.query(MFAChallenge).filter(
            MFAChallenge.gate_id == gate.id,
            MFAChallenge.user_id == user.id,
            MFAChallenge.verified == True,
            MFAChallenge.verified_at > datetime.utcnow() - timedelta(seconds=60)
        ).order_by(MFAChallenge.verified_at.desc()).first()
        
        logger.info(f"DEBUG: Found challenge: {recent_verified_challenge.id if recent_verified_challenge else None}")
        
        has_fingerprint_stay = hasattr(request, 'fingerprint_stay') and request.fingerprint_stay
        logger.info(f"DEBUG: has_fingerprint_stay={has_fingerprint_stay}")
        
        # Mark that this user was verified via MFA and should get Stay with fingerprint when session is created
        if recent_verified_challenge and not has_fingerprint_stay and ssh_key_fingerprint:
            request.mfa_verified_fingerprint = ssh_key_fingerprint
            logger.info(f"DEBUG: Marked fingerprint {ssh_key_fingerprint[:20]} for Stay creation on session start")
    
    # MFA Phase 2: Check if MFA required based on gate config and grant
    if gate.mfa_enabled and selected_policy and selected_policy.mfa_required:
        # Check if we have fingerprint-based Stay (from earlier lookup)
        has_fingerprint_stay = hasattr(request, 'fingerprint_stay') and request.fingerprint_stay
        
        if has_fingerprint_stay:
            # Have Stay from fingerprint, but grant REQUIRES MFA for this server
            # Force MFA even with existing Stay
            pass  # Fall through to MFA required logic below
        
        # Check if user has verified MFA challenge (not expired)
        # Challenge must be recent (last 60 seconds) to prevent reuse
        from src.core.database import MFAChallenge
        from datetime import datetime, timedelta
        
        # Phase 2: challenge.grant_id may be NULL, so check by user_id and gate_id only
        recent_verified_challenge = db.query(MFAChallenge).filter(
            MFAChallenge.gate_id == gate.id,
            MFAChallenge.user_id == user.id,
            MFAChallenge.verified == True,
            MFAChallenge.verified_at > datetime.utcnow() - timedelta(seconds=60)  # 60 second window after verification
        ).order_by(MFAChallenge.verified_at.desc()).first()
        
        if not recent_verified_challenge:
            # MFA required - no recent verified challenge
            # Return special response telling Gate to trigger MFA flow
            return jsonify({
                'allowed': False,
                'mfa_required': True,
                'user_id': user.id,
                'person_username': user.username,
                'person_fullname': transliterate_polish(user.full_name) if hasattr(user, 'full_name') else user.username,
                'grant_id': selected_policy.id,
                'server_id': server.id,
                'server_name': server.name,
                'reason': 'MFA authentication required',
                'message': 'Please complete MFA authentication to proceed'
            }), 200  # Return 200 (not 403) - this is expected flow, not denial
    
    # Build success response
    response = {
        'allowed': True,
        'person_id': user.id,
        'person_username': user.username,
        'person_fullname': user.full_name if hasattr(user, 'full_name') else user.username,
        'person_permission_level': user.permission_level if hasattr(user, 'permission_level') else 1000,
        'server_id': server.id,
        'server_name': server.name,
        'server_ip': server.ip_address,
        'grant_id': selected_policy.id if selected_policy else None,
        'grant_scope': selected_policy.scope_type if selected_policy else None,
        'effective_end_time': result['effective_end_time'].isoformat() + 'Z' if result.get('effective_end_time') else None,
        'port_forwarding_allowed': selected_policy.port_forwarding_allowed if selected_policy else False,
        'inactivity_timeout_minutes': selected_policy.inactivity_timeout_minutes if selected_policy else 60,
        'reason': result.get('reason', 'Access granted'),
        'gate_id': gate.id,
        'gate_name': gate.name
    }
    
    # MFA Phase 2: If this was MFA verification, tell Gate to save fingerprint in Stay
    if hasattr(request, 'mfa_verified_fingerprint') and request.mfa_verified_fingerprint:
        response['ssh_key_fingerprint'] = request.mfa_verified_fingerprint
        logger.info(f"Sending fingerprint to Gate for Stay creation: {request.mfa_verified_fingerprint[:20]}")
    
    # Add SSH logins if protocol is SSH
    if protocol == 'ssh' and selected_policy:
        from src.core.database import PolicySSHLogin
        ssh_logins = db.query(PolicySSHLogin).filter(
            PolicySSHLogin.policy_id == selected_policy.id
        ).all()
        response['ssh_logins'] = [login.allowed_login for login in ssh_logins] if ssh_logins else []
    
    return jsonify(response), 200


@grants_bp.route('/grants/active', methods=['GET'])
@require_gate_auth
def get_active_grants():
    """Get all currently active grants for Gate cache refresh.
    
    Gate calls this periodically (every 30s) to update local cache.
    
    Query parameters:
        protocol: Filter by protocol (ssh/rdp), optional
        limit: Max number of grants to return, default 1000
    
    Response:
        200 OK: {
            "grants": [
                {
                    "id": 123,
                    "person_id": 456,
                    "person_username": "jan.kowalski",
                    "scope_type": "server",
                    "server_id": 789,
                    "server_hostname": "srv-prod-01",
                    "protocol": "ssh",
                    "start_time": "2026-01-07T10:00:00",
                    "end_time": null,
                    "ssh_logins": ["root", "admin"]
                },
                ...
            ],
            "count": 42,
            "timestamp": "2026-01-07T14:30:00"
        }
    """
    gate = get_current_gate()
    db = get_db_session()
    
    protocol_filter = request.args.get('protocol')
    limit = int(request.args.get('limit', 1000))
    
    now = datetime.utcnow()
    
    # Query active grants
    query = db.query(AccessPolicy).filter(
        AccessPolicy.is_active == True,
        or_(
            AccessPolicy.end_time == None,
            AccessPolicy.end_time > now
        ),
        AccessPolicy.start_time <= now
    )
    
    if protocol_filter:
        if protocol_filter not in ['ssh', 'rdp']:
            return jsonify({'error': 'invalid_protocol', 'message': 'Protocol must be ssh or rdp'}), 400
        
        query = query.filter(
            or_(
                AccessPolicy.protocol == None,
                AccessPolicy.protocol == protocol_filter
            )
        )
    
    grants = query.limit(limit).all()
    
    # Build response
    grants_data = []
    for grant in grants:
        grant_data = {
            'id': grant.id,
            'scope_type': grant.scope_type,
            'protocol': grant.protocol,
            'start_time': grant.start_time.isoformat() if grant.start_time else None,
            'end_time': grant.end_time.isoformat() if grant.end_time else None,
            'port_forwarding_allowed': grant.port_forwarding_allowed,
            'use_schedules': grant.use_schedules
        }
        
        # Add person info
        if grant.user_id:
            person = db.query(User).get(grant.user_id)
            if person:
                grant_data['person_id'] = person.id
                grant_data['person_username'] = person.username
        
        # Add group info
        if grant.user_group_id:
            group = db.query(UserGroup).get(grant.user_group_id)
            if group:
                grant_data['group_id'] = group.id
                grant_data['group_name'] = group.name
        
        # Add server info
        if grant.target_server_id:
            server = db.query(Server).get(grant.target_server_id)
            if server:
                grant_data['server_id'] = server.id
                grant_data['server_name'] = server.name
                grant_data['server_ip'] = server.ip_address
        
        # Add group scope info
        if grant.target_group_id:
            server_group = db.query(ServerGroup).get(grant.target_group_id)
            if server_group:
                grant_data['server_group_id'] = server_group.id
                grant_data['server_group_name'] = server_group.name
        
        # Add SSH logins if protocol is SSH
        if grant.protocol == 'ssh' or grant.protocol is None:
            from src.core.database import PolicySSHLogin
            ssh_logins = db.query(PolicySSHLogin).filter(
                PolicySSHLogin.policy_id == grant.id
            ).all()
            grant_data['ssh_logins'] = [login.allowed_login for login in ssh_logins]
        
        grants_data.append(grant_data)
    
    return jsonify({
        'grants': grants_data,
        'count': len(grants_data),
        'timestamp': now.isoformat(),
        'gate_id': gate.id,
        'gate_name': gate.name
    }), 200
