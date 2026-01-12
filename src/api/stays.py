"""Tower API - Stay endpoints for Gate clients.

Gates use these endpoints to report when persons enter/leave servers.
A Stay represents a person being "inside" a server - may have multiple sessions.
"""

from datetime import datetime
from flask import Blueprint, request, jsonify
from src.api.auth import require_gate_auth, get_current_gate, get_db_session
from src.core.database import Stay, User, Server, AccessPolicy

stays_bp = Blueprint('stays', __name__, url_prefix='/api/v1/stays')


@stays_bp.route('/start', methods=['POST'])
@require_gate_auth
def start_stay():
    """Report that a person has entered a server (Stay started).
    
    Gate calls this when person successfully connects.
    Creates a new Stay record with started_at = now, ended_at = NULL.
    
    Request JSON:
        {
            "username": "jan.kowalski",
            "server": "srv-prod-01",       # Hostname or IP
            "grant_id": 123,               # From /api/v1/auth/check response
            "source_ip": "192.168.1.100"   # Optional: client IP
        }
    
    Response:
        201 Created: {
            "stay_id": 789,
            "person_id": 456,
            "person_username": "jan.kowalski",
            "server_id": 12,
            "server_hostname": "srv-prod-01",
            "grant_id": 123,
            "gate_id": 1,
            "gate_name": "gate-localhost",
            "started_at": "2026-01-07T14:30:00",
            "is_active": true
        }
        
        400 Bad Request: Missing parameters
        404 Not Found: Person/server not found
    """
    gate = get_current_gate()
    db = get_db_session()
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'missing_body', 'message': 'Request body required'}), 400
    
    username = data.get('username')
    server_identifier = data.get('server')
    grant_id = data.get('grant_id')
    source_ip = data.get('source_ip')
    
    if not username or not server_identifier or not grant_id:
        return jsonify({
            'error': 'missing_parameters',
            'message': 'Required: username, server, grant_id'
        }), 400
    
    # Find person
    person = db.query(User).filter(User.username == username).first()
    if not person:
        return jsonify({
            'error': 'person_not_found',
            'message': f'User "{username}" not found'
        }), 404
    
    # Find server
    server = db.query(Server).filter(
        (Server.name == server_identifier) | (Server.ip_address == server_identifier)
    ).first()
    if not server:
        return jsonify({
            'error': 'server_not_found',
            'message': f'Server "{server_identifier}" not found'
        }), 404
    
    # Verify grant exists
    grant = db.query(AccessPolicy).get(grant_id)
    if not grant:
        return jsonify({
            'error': 'grant_not_found',
            'message': f'Grant #{grant_id} not found'
        }), 404
    
    # Create Stay
    now = datetime.utcnow()
    stay = Stay(
        user_id=person.id,
        policy_id=grant_id,
        gate_id=gate.id,
        server_id=server.id,
        started_at=now,
        ended_at=None,  # NULL = person still inside
        is_active=True,
        created_at=now,
        updated_at=now
    )
    
    db.add(stay)
    db.commit()
    db.refresh(stay)
    
    return jsonify({
        'stay_id': stay.id,
        'person_id': person.id,
        'person_username': person.username,
        'server_id': server.id,
        'server_name': server.name,
        'grant_id': grant_id,
        'gate_id': gate.id,
        'gate_name': gate.name,
        'started_at': stay.started_at.isoformat(),
        'is_active': True,
        'source_ip': source_ip
    }), 201


@stays_bp.route('/end', methods=['POST'])
@require_gate_auth
def end_stay():
    """Report that a person has left a server (Stay ended).
    
    Gate calls this when person disconnects.
    Updates Stay: ended_at = now, duration_seconds = calculated, is_active = false.
    
    Request JSON:
        {
            "stay_id": 789,
            "termination_reason": "client_disconnect"  # Optional
        }
    
    Response:
        200 OK: {
            "stay_id": 789,
            "person_username": "jan.kowalski",
            "server_hostname": "srv-prod-01",
            "started_at": "2026-01-07T14:30:00",
            "ended_at": "2026-01-07T15:45:00",
            "duration_seconds": 4500,
            "is_active": false,
            "termination_reason": "client_disconnect"
        }
        
        400 Bad Request: Missing stay_id
        404 Not Found: Stay not found
        409 Conflict: Stay already ended
    """
    gate = get_current_gate()
    db = get_db_session()
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'missing_body', 'message': 'Request body required'}), 400
    
    stay_id = data.get('stay_id')
    termination_reason = data.get('termination_reason', 'normal_disconnect')
    
    if not stay_id:
        return jsonify({
            'error': 'missing_parameters',
            'message': 'Required: stay_id'
        }), 400
    
    # Find stay
    stay = db.query(Stay).get(stay_id)
    if not stay:
        return jsonify({
            'error': 'stay_not_found',
            'message': f'Stay #{stay_id} not found'
        }), 404
    
    # Check if already ended
    if stay.ended_at is not None:
        return jsonify({
            'error': 'stay_already_ended',
            'message': f'Stay #{stay_id} already ended at {stay.ended_at.isoformat()}',
            'ended_at': stay.ended_at.isoformat(),
            'duration_seconds': stay.duration_seconds
        }), 409
    
    # End stay
    now = datetime.utcnow()
    duration = int((now - stay.started_at).total_seconds())
    
    stay.ended_at = now
    stay.duration_seconds = duration
    stay.is_active = False
    stay.termination_reason = termination_reason
    stay.updated_at = now
    
    db.commit()
    db.refresh(stay)
    
    # Get person and server info for response
    person = db.query(User).get(stay.user_id)
    server = db.query(Server).get(stay.server_id)
    
    return jsonify({
        'stay_id': stay.id,
        'person_id': person.id if person else None,
        'person_username': person.username if person else None,
        'server_id': server.id if server else None,
        'server_name': server.name if server else None,
        'gate_id': stay.gate_id,
        'started_at': stay.started_at.isoformat(),
        'ended_at': stay.ended_at.isoformat(),
        'duration_seconds': stay.duration_seconds,
        'is_active': False,
        'termination_reason': termination_reason
    }), 200


@stays_bp.route('/active', methods=['GET'])
@require_gate_auth
def get_active_stays():
    """Get all currently active stays (persons inside servers).
    
    Optional query parameters:
        gate_id: Filter by specific gate
        person_id: Filter by specific person
        server_id: Filter by specific server
        limit: Max results, default 1000
    
    Response:
        200 OK: {
            "stays": [
                {
                    "stay_id": 789,
                    "person_username": "jan.kowalski",
                    "server_hostname": "srv-prod-01",
                    "gate_name": "gate-localhost",
                    "started_at": "2026-01-07T14:30:00",
                    "duration_seconds": 900
                },
                ...
            ],
            "count": 5,
            "timestamp": "2026-01-07T14:45:00"
        }
    """
    gate = get_current_gate()
    db = get_db_session()
    
    gate_id_filter = request.args.get('gate_id', type=int)
    person_id_filter = request.args.get('person_id', type=int)
    server_id_filter = request.args.get('server_id', type=int)
    limit = int(request.args.get('limit', 1000))
    
    # Query active stays
    query = db.query(Stay).filter(Stay.is_active == True, Stay.ended_at == None)
    
    if gate_id_filter:
        query = query.filter(Stay.gate_id == gate_id_filter)
    if person_id_filter:
        query = query.filter(Stay.user_id == person_id_filter)
    if server_id_filter:
        query = query.filter(Stay.server_id == server_id_filter)
    
    stays = query.order_by(Stay.started_at.desc()).limit(limit).all()
    
    # Build response
    now = datetime.utcnow()
    stays_data = []
    
    for stay in stays:
        person = db.query(User).get(stay.user_id)
        server = db.query(Server).get(stay.server_id)
        gate_obj = db.query(Gate).get(stay.gate_id) if stay.gate_id else None
        
        duration = int((now - stay.started_at).total_seconds())
        
        stays_data.append({
            'stay_id': stay.id,
            'person_id': person.id if person else None,
            'person_username': person.username if person else None,
            'server_id': server.id if server else None,
            'server_name': server.name if server else None,
            'gate_id': stay.gate_id,
            'gate_name': gate_obj.name if gate_obj else None,
            'grant_id': stay.policy_id,
            'started_at': stay.started_at.isoformat(),
            'duration_seconds': duration
        })
    
    return jsonify({
        'stays': stays_data,
        'count': len(stays_data),
        'timestamp': now.isoformat(),
        'requesting_gate': gate.name
    }), 200


# Import Gate here to avoid circular import
from src.core.database import Gate
