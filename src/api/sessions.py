"""Tower API - Session management endpoints for Gate clients.

Gates use these endpoints to report session lifecycle events.
"""

from datetime import datetime
from flask import Blueprint, request, jsonify
from src.api.auth import require_gate_auth, get_current_gate, get_db_session
from src.core.database import Session, User, Server, Stay
import logging

logger = logging.getLogger(__name__)

api_sessions_bp = Blueprint('api_sessions', __name__, url_prefix='/api/v1/sessions')


@api_sessions_bp.route('/create', methods=['POST'])
@require_gate_auth
def create_session():
    """Gate reports that a session has started.
    
    Called after successful authentication and connection establishment.
    
    Request JSON:
        {
            "session_id": "uuid-string",
            "stay_id": 123,                    # From /stays/start response
            "person_id": 6,
            "server_id": 1,
            "protocol": "ssh",
            "source_ip": "100.64.0.39",
            "proxy_ip": "10.0.160.129",
            "backend_ip": "10.0.160.4",
            "backend_port": 22,
            "ssh_username": "p.mojski",        # Optional: SSH login
            "subsystem_name": "sftp",          # Optional: SSH subsystem
            "ssh_agent_used": true,            # Optional: Agent forwarding
            "recording_path": "/path/to/rec",  # Optional: Recording file
            "grant_id": 30,                    # From /auth/check
            "protocol_version": "SSH-2.0-..."  # Optional: Client version
        }
    
    Response:
        201 Created: {
            "session_id": "uuid-string",
            "db_session_id": 789,
            "person_username": "p.mojski",
            "server_name": "Test-SSH-Server",
            "started_at": "2026-01-07T10:00:00",
            "is_active": true,
            "message": "Session created successfully"
        }
        
        400 Bad Request: Missing parameters
        404 Not Found: Person/server not found
    """
    gate = get_current_gate()
    db = get_db_session()
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'missing_body', 'message': 'Request body required'}), 400
    
    session_id = data.get('session_id')
    stay_id = data.get('stay_id')
    person_id = data.get('person_id')
    server_id = data.get('server_id')
    protocol = data.get('protocol')
    source_ip = data.get('source_ip')
    proxy_ip = data.get('proxy_ip')
    
    if not all([session_id, person_id, server_id, protocol, source_ip, proxy_ip]):
        return jsonify({
            'error': 'missing_parameters',
            'message': 'Required: session_id, person_id, server_id, protocol, source_ip, proxy_ip'
        }), 400
    
    # Verify person exists
    person = db.query(User).get(person_id)
    if not person:
        return jsonify({
            'error': 'person_not_found',
            'message': f'Person ID {person_id} not found'
        }), 404
    
    # Verify server exists
    server = db.query(Server).get(server_id)
    if not server:
        return jsonify({
            'error': 'server_not_found',
            'message': f'Server ID {server_id} not found'
        }), 404
    
    # STAY LOGIC: Check if person has any active sessions
    # If this is first session → create Stay
    # If person already has active session(s) → reuse existing Stay
    active_sessions_count = db.query(Session).filter(
        Session.user_id == person_id,
        Session.is_active == True
    ).count()
    
    if active_sessions_count == 0:
        # First session - create new Stay
        logger.info(f"First session for person {person.username} - creating new Stay")
        stay = Stay(
            user_id=person_id,
            policy_id=data.get('grant_id'),  # Policy used for first session
            gate_id=gate.id,
            server_id=server_id,  # First server for metadata
            started_at=datetime.utcnow(),
            is_active=True
        )
        db.add(stay)
        db.flush()  # Get stay.id before creating session
        stay_id = stay.id
        logger.info(f"Created Stay #{stay_id} for person {person.username}")
    else:
        # Person already has active session(s) - reuse existing Stay
        existing_stay = db.query(Stay).filter(
            Stay.user_id == person_id,
            Stay.is_active == True
        ).first()
        
        if existing_stay:
            stay_id = existing_stay.id
            logger.info(f"Reusing existing Stay #{stay_id} for person {person.username} (has {active_sessions_count} active sessions)")
        else:
            # Edge case: has active sessions but no active Stay (data inconsistency)
            # Create new Stay
            logger.warning(f"Person {person.username} has {active_sessions_count} active sessions but no active Stay - creating new Stay")
            stay = Stay(
                user_id=person_id,
                policy_id=data.get('grant_id'),
                gate_id=gate.id,
                server_id=server_id,
                started_at=datetime.utcnow(),
                is_active=True
            )
            db.add(stay)
            db.flush()
            stay_id = stay.id
    
    # Create session
    now = datetime.utcnow()
    db_session = Session(
        session_id=session_id,
        user_id=person_id,
        server_id=server_id,
        protocol=protocol,
        source_ip=source_ip,
        proxy_ip=proxy_ip,
        backend_ip=data.get('backend_ip'),
        backend_port=data.get('backend_port'),
        ssh_username=data.get('ssh_username'),
        subsystem_name=data.get('subsystem_name'),
        ssh_agent_used=data.get('ssh_agent_used', False),
        started_at=now,
        is_active=True,
        recording_path=data.get('recording_path'),
        policy_id=data.get('grant_id'),
        connection_status='active',
        protocol_version=data.get('protocol_version'),
        gate_id=gate.id,
        stay_id=stay_id
    )
    
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    
    return jsonify({
        'session_id': session_id,
        'db_session_id': db_session.id,
        'person_id': person.id,
        'person_username': person.username,
        'server_id': server.id,
        'server_name': server.name,
        'gate_id': gate.id,
        'gate_name': gate.name,
        'stay_id': stay_id,
        'started_at': db_session.started_at.isoformat(),
        'is_active': True,
        'message': 'Session created successfully'
    }), 201


@api_sessions_bp.route('/<session_id>', methods=['PATCH'])
@require_gate_auth
def update_session(session_id):
    """Gate updates session status (e.g., ended, recording path updated).
    
    Request JSON:
        {
            "ended_at": "2026-01-07T11:00:00",    # Optional: Session end time
            "duration_seconds": 3600,              # Optional: Session duration
            "is_active": false,                    # Optional: Set to false when ended
            "termination_reason": "user_logout",   # Optional: Why session ended
            "recording_path": "/updated/path",     # Optional: Update recording path
            "recording_size": 1234567              # Optional: Recording file size
        }
    
    Response:
        200 OK: {
            "session_id": "uuid-string",
            "db_session_id": 789,
            "updated_fields": ["ended_at", "duration_seconds", "is_active"],
            "message": "Session updated successfully"
        }
        
        404 Not Found: Session not found
    """
    gate = get_current_gate()
    db = get_db_session()
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'missing_body', 'message': 'Request body required'}), 400
    
    # Find session
    db_session = db.query(Session).filter(Session.session_id == session_id).first()
    if not db_session:
        return jsonify({
            'error': 'session_not_found',
            'message': f'Session {session_id} not found'
        }), 404
    
    # Update fields
    updated_fields = []
    
    if 'ended_at' in data:
        db_session.ended_at = datetime.fromisoformat(data['ended_at']) if isinstance(data['ended_at'], str) else data['ended_at']
        updated_fields.append('ended_at')
    
    if 'duration_seconds' in data:
        db_session.duration_seconds = data['duration_seconds']
        updated_fields.append('duration_seconds')
    
    if 'is_active' in data:
        db_session.is_active = data['is_active']
        updated_fields.append('is_active')
    
    if 'termination_reason' in data:
        db_session.termination_reason = data['termination_reason']
        updated_fields.append('termination_reason')
    
    if 'recording_path' in data:
        db_session.recording_path = data['recording_path']
        updated_fields.append('recording_path')
    
    if 'recording_size' in data:
        db_session.recording_size = data['recording_size']
        updated_fields.append('recording_size')
    
    # STAY LOGIC: If session ended, check if we should close Stay
    if data.get('is_active') == False or 'ended_at' in data:
        # Session is ending - check if this is last active session for this person
        person_id = db_session.user_id
        
        # Count remaining active sessions for this person (excluding current one)
        remaining_sessions = db.query(Session).filter(
            Session.user_id == person_id,
            Session.is_active == True,
            Session.id != db_session.id
        ).count()
        
        logger.info(f"Session {session_id} ending for person ID {person_id} - {remaining_sessions} other active sessions remain")
        
        if remaining_sessions == 0:
            # This is the last session - close Stay
            active_stay = db.query(Stay).filter(
                Stay.user_id == person_id,
                Stay.is_active == True
            ).first()
            
            if active_stay:
                active_stay.is_active = False
                active_stay.ended_at = db_session.ended_at or datetime.utcnow()
                if active_stay.started_at:
                    active_stay.duration_seconds = int((active_stay.ended_at - active_stay.started_at).total_seconds())
                active_stay.termination_reason = data.get('termination_reason', 'last_session_ended')
                
                logger.info(f"Closed Stay #{active_stay.id} for person ID {person_id} (last session ended, duration: {active_stay.duration_seconds}s)")
                updated_fields.append('stay_closed')
            else:
                logger.warning(f"Person ID {person_id} has no active Stay despite session ending")
    
    db.commit()
    db.refresh(db_session)
    
    return jsonify({
        'session_id': session_id,
        'db_session_id': db_session.id,
        'updated_fields': updated_fields,
        'is_active': db_session.is_active,
        'message': 'Session updated successfully'
    }), 200


@api_sessions_bp.route('/active', methods=['GET'])
@require_gate_auth
def get_active_sessions():
    """Get all currently active sessions.
    
    Query parameters:
        gate_id: Filter by specific gate
        person_id: Filter by specific person
        server_id: Filter by specific server
        protocol: Filter by protocol (ssh/rdp)
        limit: Max results, default 1000
    
    Response:
        200 OK: {
            "sessions": [
                {
                    "session_id": "uuid",
                    "db_session_id": 789,
                    "person_username": "p.mojski",
                    "server_name": "Test-SSH-Server",
                    "protocol": "ssh",
                    "started_at": "2026-01-07T10:00:00",
                    "duration_seconds": 900
                },
                ...
            ],
            "count": 5,
            "timestamp": "2026-01-07T10:15:00"
        }
    """
    gate = get_current_gate()
    db = get_db_session()
    
    gate_id_filter = request.args.get('gate_id', type=int)
    person_id_filter = request.args.get('person_id', type=int)
    server_id_filter = request.args.get('server_id', type=int)
    protocol_filter = request.args.get('protocol')
    limit = int(request.args.get('limit', 1000))
    
    # Query active sessions
    query = db.query(Session).filter(Session.is_active == True)
    
    if gate_id_filter:
        query = query.filter(Session.gate_id == gate_id_filter)
    if person_id_filter:
        query = query.filter(Session.user_id == person_id_filter)
    if server_id_filter:
        query = query.filter(Session.server_id == server_id_filter)
    if protocol_filter:
        query = query.filter(Session.protocol == protocol_filter)
    
    sessions = query.order_by(Session.started_at.desc()).limit(limit).all()
    
    # Build response
    now = datetime.utcnow()
    sessions_data = []
    
    for sess in sessions:
        person = db.query(User).get(sess.user_id)
        server = db.query(Server).get(sess.server_id)
        
        duration = int((now - sess.started_at).total_seconds()) if sess.started_at else 0
        
        sessions_data.append({
            'session_id': sess.session_id,
            'db_session_id': sess.id,
            'person_id': sess.user_id,
            'person_username': person.username if person else None,
            'server_id': sess.server_id,
            'server_name': server.name if server else None,
            'protocol': sess.protocol,
            'ssh_username': sess.ssh_username,
            'source_ip': sess.source_ip,
            'gate_id': sess.gate_id,
            'stay_id': sess.stay_id,
            'started_at': sess.started_at.isoformat() if sess.started_at else None,
            'duration_seconds': duration,
            'connection_status': sess.connection_status
        })
    
    return jsonify({
        'sessions': sessions_data,
        'count': len(sessions_data),
        'timestamp': now.isoformat(),
        'requesting_gate': gate.name
    }), 200
