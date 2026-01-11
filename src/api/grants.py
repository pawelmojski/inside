"""Tower API - Grant (Access Policy) endpoints for Gate clients.

Gates use these endpoints to check authorization and fetch active grants.
"""

from datetime import datetime
from flask import Blueprint, request, jsonify
from sqlalchemy import and_, or_
import pytz
from src.api.auth import require_gate_auth, get_current_gate, get_db_session
from src.core.database import (
    AccessPolicy, User, Server, ServerGroup, UserSourceIP,
    PolicySchedule, UserGroup, UserGroupMember, ServerGroupMember
)

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
    gate = get_current_gate()
    db = get_db_session()
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'missing_body', 'message': 'Request body required'}), 400
    
    source_ip = data.get('source_ip')
    destination_ip = data.get('destination_ip')
    protocol = data.get('protocol')
    ssh_login = data.get('ssh_login')
    
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
    
    # Build success response
    response = {
        'allowed': True,
        'person_id': user.id,
        'person_username': user.username,
        'person_fullname': user.full_name if hasattr(user, 'full_name') else user.username,
        'server_id': server.id,
        'server_name': server.name,
        'server_ip': server.ip_address,
        'grant_id': selected_policy.id if selected_policy else None,
        'grant_scope': selected_policy.scope_type if selected_policy else None,
        'effective_end_time': result['effective_end_time'].isoformat() if result.get('effective_end_time') else None,
        'port_forwarding_allowed': selected_policy.port_forwarding_allowed if selected_policy else False,
        'reason': result.get('reason', 'Access granted'),
        'gate_id': gate.id,
        'gate_name': gate.name
    }
    
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
