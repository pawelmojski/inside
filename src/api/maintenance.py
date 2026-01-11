"""Tower API - Maintenance mode endpoints.

Allows administrators to schedule disconnections for:
- Individual sessions
- All sessions on a specific gate
- All sessions to a specific backend server
"""

from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from sqlalchemy import and_
from src.api.auth import require_gate_auth, get_current_gate, get_db_session
from src.core.database import Session as DBSession, Gate, Server

maintenance_bp = Blueprint('maintenance', __name__, url_prefix='/api/v1')


@maintenance_bp.route('/sessions/<session_id>/force-disconnect', methods=['POST'])
@require_gate_auth
def force_disconnect_session(session_id):
    """Force disconnect a specific session.
    
    Request JSON:
        {
            "disconnect_at": "2026-01-11T18:30:00Z",  # ISO timestamp (optional)
            "reason": "User deactivated"               # Optional reason
        }
    
    If disconnect_at not provided, disconnects immediately (now + 5 seconds).
    
    Response:
        200 OK: {
            "success": true,
            "session_id": "100.64.0.20_1768151609.790956",
            "disconnect_at": "2026-01-11T18:30:00",
            "reason": "User deactivated"
        }
        
        404: Session not found or not active
    """
    gate = get_current_gate()
    db = get_db_session()
    
    # Find session
    session = db.query(DBSession).filter(
        DBSession.session_id == session_id,
        DBSession.is_active == True
    ).first()
    
    if not session:
        return jsonify({
            'error': 'session_not_found',
            'message': f'Active session {session_id} not found'
        }), 404
    
    data = request.get_json() or {}
    
    # Parse disconnect_at timestamp
    disconnect_at_str = data.get('disconnect_at')
    if disconnect_at_str:
        from dateutil import parser as dateparser
        try:
            disconnect_at = dateparser.isoparse(disconnect_at_str)
            # Convert to naive UTC
            if disconnect_at.tzinfo is not None:
                disconnect_at = disconnect_at.replace(tzinfo=None)
        except Exception as e:
            return jsonify({
                'error': 'invalid_timestamp',
                'message': f'Invalid disconnect_at format: {e}'
            }), 400
    else:
        # Default: disconnect in 5 seconds
        disconnect_at = datetime.utcnow() + timedelta(seconds=5)
    
    reason = data.get('reason', 'Forced disconnect by administrator')
    
    # Mark session for termination
    session.termination_reason = 'forced_disconnect'
    session.termination_details = reason
    db.commit()
    
    return jsonify({
        'success': True,
        'session_id': session_id,
        'disconnect_at': disconnect_at.isoformat(),
        'reason': reason
    }), 200


@maintenance_bp.route('/gates/<int:gate_id>/maintenance', methods=['POST'])
@require_gate_auth
def enter_gate_maintenance(gate_id):
    """Put gate into maintenance mode with scheduled disconnection.
    
    Request JSON:
        {
            "scheduled_at": "2026-01-11T20:00:00Z",  # ISO timestamp when maintenance starts
            "grace_minutes": 15,                      # Minutes before to block new logins (default: 15)
            "reason": "Scheduled maintenance",
            "personnel_ids": [5, 12]                  # User IDs with access during maintenance
        }
    
    Grace period: New logins blocked at (scheduled_at - grace_minutes).
    Existing sessions disconnected at scheduled_at.
    Personnel in personnel_ids list can login during grace period and maintenance.
    
    Response:
        200 OK: {
            "success": true,
            "gate_id": 1,
            "gate_name": "gate-localhost",
            "scheduled_at": "2026-01-11T20:00:00",
            "grace_starts_at": "2026-01-11T19:45:00",
            "grace_minutes": 15,
            "affected_sessions": 5,
            "maintenance_personnel": ["p.mojski", "j.kowalski"],
            "reason": "Scheduled maintenance"
        }
        
        404: Gate not found
        400: Invalid timestamp or personnel
    """
    gate = get_current_gate()
    db = get_db_session()
    
    # Verify gate exists
    target_gate = db.query(Gate).filter(Gate.id == gate_id).first()
    if not target_gate:
        return jsonify({
            'error': 'gate_not_found',
            'message': f'Gate {gate_id} not found'
        }), 404
    
    data = request.get_json() or {}
    
    # Parse scheduled_at timestamp (required)
    scheduled_at_str = data.get('scheduled_at')
    if not scheduled_at_str:
        return jsonify({
            'error': 'missing_scheduled_at',
            'message': 'scheduled_at timestamp is required (ISO format)'
        }), 400
    
    from dateutil import parser as dateparser
    try:
        scheduled_at = dateparser.isoparse(scheduled_at_str)
        # Convert to naive UTC
        if scheduled_at.tzinfo is not None:
            scheduled_at = scheduled_at.replace(tzinfo=None)
    except Exception as e:
        return jsonify({
            'error': 'invalid_timestamp',
            'message': f'Invalid scheduled_at format: {e}'
        }), 400
    
    # If scheduled_at is in the past, treat as "now" (immediate maintenance)
    now = datetime.utcnow()
    if scheduled_at < now:
        scheduled_at = now
    
    grace_minutes = data.get('grace_minutes', 15)
    reason = data.get('reason', 'Scheduled gate maintenance')
    personnel_ids = data.get('personnel_ids', [])
    
    # Set maintenance mode
    target_gate.in_maintenance = True
    target_gate.maintenance_scheduled_at = scheduled_at
    target_gate.maintenance_grace_minutes = grace_minutes
    target_gate.maintenance_reason = reason
    
    # Clear existing maintenance personnel and add new ones
    from src.core.database import MaintenanceAccess, User
    db.query(MaintenanceAccess).filter(
        MaintenanceAccess.entity_type == 'gate',
        MaintenanceAccess.entity_id == gate_id
    ).delete()
    
    personnel_usernames = []
    for person_id in personnel_ids:
        user = db.query(User).filter(User.id == person_id).first()
        if user:
            access = MaintenanceAccess(
                entity_type='gate',
                entity_id=gate_id,
                person_id=person_id
            )
            db.add(access)
            personnel_usernames.append(user.username)
    
    db.commit()
    
    # Calculate grace period start time
    grace_starts_at = scheduled_at - timedelta(minutes=grace_minutes)
    
    # Find all active sessions on this gate
    active_sessions = db.query(DBSession).filter(
        DBSession.gate_id == gate_id,
        DBSession.is_active == True
    ).all()
    
    # Mark all sessions for termination at scheduled_at
    import json
    for session in active_sessions:
        # Only mark for disconnect if user is NOT maintenance personnel
        if session.user_id not in personnel_ids:
            session.termination_reason = 'gate_maintenance'
            session.denial_details = json.dumps({
                'reason': reason,
                'disconnect_at': scheduled_at.isoformat()
            })
    
    db.commit()
    
    return jsonify({
        'success': True,
        'gate_id': gate_id,
        'gate_name': target_gate.name,
        'scheduled_at': scheduled_at.isoformat(),
        'grace_starts_at': grace_starts_at.isoformat(),
        'grace_minutes': grace_minutes,
        'affected_sessions': len([s for s in active_sessions if s.user_id not in personnel_ids]),
        'maintenance_personnel': personnel_usernames,
        'reason': reason
    }), 200


@maintenance_bp.route('/backends/<int:server_id>/maintenance', methods=['POST'])
@require_gate_auth
def enter_backend_maintenance(server_id):
    """Put backend server into maintenance mode with scheduled disconnection.
    
    Request JSON:
        {
            "scheduled_at": "2026-01-11T20:00:00Z",  # ISO timestamp when maintenance starts
            "grace_minutes": 15,                      # Minutes before to block new logins (default: 15)
            "reason": "Server maintenance",
            "personnel_ids": [5, 12]                  # User IDs with access during maintenance
        }
    
    Response:
        200 OK: {
            "success": true,
            "server_id": 1,
            "server_name": "Test-SSH-Server",
            "scheduled_at": "2026-01-11T20:00:00",
            "grace_starts_at": "2026-01-11T19:45:00",
            "grace_minutes": 15,
            "affected_sessions": 3,
            "maintenance_personnel": ["p.mojski"],
            "reason": "Server maintenance"
        }
        
        404: Server not found
        400: Invalid timestamp or personnel
    """
    gate = get_current_gate()
    db = get_db_session()
    
    # Verify server exists
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        return jsonify({
            'error': 'server_not_found',
            'message': f'Server {server_id} not found'
        }), 404
    
    data = request.get_json() or {}
    
    # Parse scheduled_at timestamp (required)
    scheduled_at_str = data.get('scheduled_at')
    if not scheduled_at_str:
        return jsonify({
            'error': 'missing_scheduled_at',
            'message': 'scheduled_at timestamp is required (ISO format)'
        }), 400
    
    from dateutil import parser as dateparser
    try:
        scheduled_at = dateparser.isoparse(scheduled_at_str)
        # Convert to naive UTC
        if scheduled_at.tzinfo is not None:
            scheduled_at = scheduled_at.replace(tzinfo=None)
    except Exception as e:
        return jsonify({
            'error': 'invalid_timestamp',
            'message': f'Invalid scheduled_at format: {e}'
        }), 400
    
    # If scheduled_at is in the past, treat as "now" (immediate maintenance)
    now = datetime.utcnow()
    if scheduled_at < now:
        scheduled_at = now
    
    grace_minutes = data.get('grace_minutes', 15)
    reason = data.get('reason', 'Scheduled server maintenance')
    personnel_ids = data.get('personnel_ids', [])
    
    # Set maintenance mode
    server.in_maintenance = True
    server.maintenance_scheduled_at = scheduled_at
    server.maintenance_grace_minutes = grace_minutes
    server.maintenance_reason = reason
    
    # Clear existing maintenance personnel and add new ones
    from src.core.database import MaintenanceAccess, User
    db.query(MaintenanceAccess).filter(
        MaintenanceAccess.entity_type == 'server',
        MaintenanceAccess.entity_id == server_id
    ).delete()
    
    personnel_usernames = []
    for person_id in personnel_ids:
        user = db.query(User).filter(User.id == person_id).first()
        if user:
            access = MaintenanceAccess(
                entity_type='server',
                entity_id=server_id,
                person_id=person_id
            )
            db.add(access)
            personnel_usernames.append(user.username)
    
    db.commit()
    
    # Calculate grace period start time
    grace_starts_at = scheduled_at - timedelta(minutes=grace_minutes)
    
    # Find all active sessions to this server
    active_sessions = db.query(DBSession).filter(
        DBSession.server_id == server_id,
        DBSession.is_active == True
    ).all()
    
    # Mark all sessions for termination at scheduled_at (except personnel)
    import json
    for session in active_sessions:
        if session.user_id not in personnel_ids:
            session.termination_reason = 'backend_maintenance'
            session.denial_details = json.dumps({
                'reason': reason,
                'disconnect_at': scheduled_at.isoformat()
            })
    
    db.commit()
    
    return jsonify({
        'success': True,
        'server_id': server_id,
        'server_name': server.name,
        'scheduled_at': scheduled_at.isoformat(),
        'grace_starts_at': grace_starts_at.isoformat(),
        'grace_minutes': grace_minutes,
        'affected_sessions': len([s for s in active_sessions if s.user_id not in personnel_ids]),
        'maintenance_personnel': personnel_usernames,
        'reason': reason
    }), 200


@maintenance_bp.route('/gates/<int:gate_id>/maintenance', methods=['DELETE'])
@require_gate_auth
def exit_gate_maintenance(gate_id):
    """Exit maintenance mode for gate - allow normal operations.
    
    Response:
        200 OK: {
            "success": true,
            "gate_id": 1,
            "gate_name": "gate-localhost"
        }
        
        404: Gate not found
    """
    gate = get_current_gate()
    db = get_db_session()
    
    target_gate = db.query(Gate).filter(Gate.id == gate_id).first()
    if not target_gate:
        return jsonify({
            'error': 'gate_not_found',
            'message': f'Gate {gate_id} not found'
        }), 404
    
    # Clear maintenance mode
    target_gate.in_maintenance = False
    target_gate.maintenance_scheduled_at = None
    target_gate.maintenance_reason = None
    
    # Clear maintenance personnel
    from src.core.database import MaintenanceAccess
    db.query(MaintenanceAccess).filter(
        MaintenanceAccess.entity_type == 'gate',
        MaintenanceAccess.entity_id == gate_id
    ).delete()
    
    # Clear any pending termination reasons for sessions on this gate
    db.query(DBSession).filter(
        DBSession.gate_id == gate_id,
        DBSession.termination_reason == 'gate_maintenance'
    ).update({
        'termination_reason': None,
        'denial_details': None
    })
    
    db.commit()
    
    return jsonify({
        'success': True,
        'gate_id': gate_id,
        'gate_name': target_gate.name
    }), 200


@maintenance_bp.route('/backends/<int:server_id>/maintenance', methods=['DELETE'])
@require_gate_auth
def exit_backend_maintenance(server_id):
    """Exit maintenance mode for backend server - allow normal operations.
    
    Response:
        200 OK: {
            "success": true,
            "server_id": 1,
            "server_name": "Test-SSH-Server"
        }
        
        404: Server not found
    """
    gate = get_current_gate()
    db = get_db_session()
    
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        return jsonify({
            'error': 'server_not_found',
            'message': f'Server {server_id} not found'
        }), 404
    
    # Clear maintenance mode
    server.in_maintenance = False
    server.maintenance_scheduled_at = None
    server.maintenance_reason = None
    
    # Clear maintenance personnel
    from src.core.database import MaintenanceAccess
    db.query(MaintenanceAccess).filter(
        MaintenanceAccess.entity_type == 'server',
        MaintenanceAccess.entity_id == server_id
    ).delete()
    
    # Clear any pending termination reasons for sessions to this server
    db.query(DBSession).filter(
        DBSession.server_id == server_id,
        DBSession.termination_reason == 'backend_maintenance'
    ).update({
        'termination_reason': None,
        'denial_details': None
    })
    
    db.commit()
    
    return jsonify({
        'success': True,
        'server_id': server_id,
        'server_name': server.name
    }), 200
