"""Tower API - Gate management endpoints.

Gates use these endpoints for heartbeat and configuration sync.
"""

from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from src.api.auth import require_gate_auth, get_current_gate, get_db_session
from src.core.database import Gate

gates_bp = Blueprint('gates', __name__, url_prefix='/api/v1/gates')


@gates_bp.route('/heartbeat', methods=['POST'])
@require_gate_auth
def heartbeat():
    """Gate sends heartbeat to report it's alive.
    
    Gate should call this every 5 seconds.
    Tower marks gate as offline if no heartbeat for 30 seconds.
    
    Note: Gates in maintenance mode (in_maintenance=True) can still send heartbeats.
          Only is_active=False (compromised/disabled) gates are blocked.
    
    Request JSON:
        {
            "version": "1.9.0",              # Gate software version
            "hostname": "jumphost-01",       # Optional: update hostname
            "active_stays": 5,               # Optional: number of active stays
            "active_sessions": 8,            # Optional: number of active sessions
            "active_session_ids": ["abc123", "def456"]  # NEW: List of active session IDs
        }
    
    Response:
        200 OK: {
            "gate_id": 1,
            "gate_name": "gate-localhost",
            "status": "online",
            "last_heartbeat": "2026-01-07T14:30:00",
            "message": "Heartbeat received",
            "relay_sessions": [              # NEW: Sessions to relay to Tower
                {
                    "session_id": "abc123",
                    "action": "start",       # or "stop"
                    "watchers_count": 2
                }
            ]
        }
    """
    gate = get_current_gate()
    db = get_db_session()
    
    data = request.get_json() or {}
    
    version = data.get('version')
    hostname = data.get('hostname')
    active_stays = data.get('active_stays')
    active_sessions = data.get('active_sessions')
    active_session_ids = data.get('active_session_ids', [])
    
    # Update gate
    now = datetime.utcnow()
    gate.last_heartbeat = now
    gate.status = 'online'
    gate.updated_at = now
    
    if version:
        gate.version = version
    if hostname:
        gate.hostname = hostname
    
    db.commit()
    db.refresh(gate)
    
    # NEW: Check which sessions from this gate need relay (browser watchers)
    relay_sessions = []
    try:
        # Import here to avoid circular dependency
        from src.web.relay_tracking import get_relay_requests_for_gate
        relay_sessions = get_relay_requests_for_gate(gate.name, active_session_ids)
    except Exception as e:
        # If relay tracking not available (e.g., Flask not running), just skip
        pass
    
    return jsonify({
        'gate_id': gate.id,
        'gate_name': gate.name,
        'status': gate.status,
        'last_heartbeat': gate.last_heartbeat.isoformat(),
        'version': gate.version,
        'message': 'Heartbeat received',
        'active_stays': active_stays,
        'active_sessions': active_sessions,
        'relay_sessions': relay_sessions  # NEW
    }), 200


@gates_bp.route('/config', methods=['GET'])
@require_gate_auth
def get_config():
    """Gate fetches configuration from Tower.
    
    Returns settings that Gate should use for operation.
    
    Response:
        200 OK: {
            "gate_id": 1,
            "gate_name": "gate-localhost",
            "config": {
                "heartbeat_interval": 30,      # Seconds between heartbeats
                "cache_ttl": 30,               # Seconds for local cache
                "max_sessions_per_stay": 100,  # Max simultaneous sessions
                "log_level": "INFO",           # Logging level
                "enable_recording": true       # Enable session recording
            },
            "timestamp": "2026-01-07T14:30:00"
        }
    """
    gate = get_current_gate()
    db = get_db_session()
    
    # Build configuration
    config = {
        'heartbeat_interval': 30,  # seconds
        'cache_ttl': 30,  # seconds
        'max_sessions_per_stay': 100,
        'log_level': 'INFO',
        'enable_recording': True,
        'grant_check_cache_enabled': True,
        'offline_mode_enabled': True,
        'offline_cache_duration': 300  # 5 minutes
    }
    
    return jsonify({
        'gate_id': gate.id,
        'gate_name': gate.name,
        'location': gate.location,
        'description': gate.description,
        'config': config,
        'timestamp': datetime.utcnow().isoformat()
    }), 200


@gates_bp.route('/status', methods=['GET'])
@require_gate_auth
def get_status():
    """Get current gate status and statistics.
    
    Response:
        200 OK: {
            "gate_id": 1,
            "gate_name": "gate-localhost",
            "status": "online",
            "last_heartbeat": "2026-01-07T14:30:00",
            "version": "1.9.0",
            "statistics": {
                "active_stays": 5,
                "total_stays_today": 42,
                "active_sessions": 8,
                "total_sessions_today": 156
            }
        }
    """
    gate = get_current_gate()
    db = get_db_session()
    
    from src.core.database import Stay, Session
    
    # Calculate statistics
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    active_stays = db.query(Stay).filter(
        Stay.gate_id == gate.id,
        Stay.is_active == True
    ).count()
    
    total_stays_today = db.query(Stay).filter(
        Stay.gate_id == gate.id,
        Stay.started_at >= today_start
    ).count()
    
    active_sessions = db.query(Session).filter(
        Session.gate_id == gate.id,
        Session.is_active == True
    ).count()
    
    total_sessions_today = db.query(Session).filter(
        Session.gate_id == gate.id,
        Session.started_at >= today_start
    ).count()
    
    return jsonify({
        'gate_id': gate.id,
        'gate_name': gate.name,
        'hostname': gate.hostname,
        'location': gate.location,
        'status': gate.status,
        'last_heartbeat': gate.last_heartbeat.isoformat() if gate.last_heartbeat else None,
        'version': gate.version,
        'is_active': gate.is_active,
        'statistics': {
            'active_stays': active_stays,
            'total_stays_today': total_stays_today,
            'active_sessions': active_sessions,
            'total_sessions_today': total_sessions_today
        },
        'timestamp': now.isoformat()
    }), 200


@gates_bp.route('/', methods=['GET'])
@require_gate_auth
def list_gates():
    """List all gates (for Gate to see other gates in network).
    
    Query parameters:
        status: Filter by status (online/offline/error)
        active_only: Boolean, show only active gates
    
    Response:
        200 OK: {
            "gates": [
                {
                    "gate_id": 1,
                    "gate_name": "gate-localhost",
                    "hostname": "localhost",
                    "location": "Main datacenter",
                    "status": "online",
                    "last_heartbeat": "2026-01-07T14:30:00",
                    "version": "1.9.0"
                },
                ...
            ],
            "count": 3
        }
    """
    gate = get_current_gate()
    db = get_db_session()
    
    status_filter = request.args.get('status')
    active_only = request.args.get('active_only', 'false').lower() == 'true'
    
    query = db.query(Gate)
    
    if status_filter:
        query = query.filter(Gate.status == status_filter)
    if active_only:
        query = query.filter(Gate.is_active == True)
    
    gates = query.order_by(Gate.name).all()
    
    gates_data = []
    for g in gates:
        gates_data.append({
            'gate_id': g.id,
            'gate_name': g.name,
            'hostname': g.hostname,
            'location': g.location,
            'description': g.description,
            'status': g.status,
            'last_heartbeat': g.last_heartbeat.isoformat() if g.last_heartbeat else None,
            'version': g.version,
            'is_active': g.is_active,
            'created_at': g.created_at.isoformat() if g.created_at else None
        })
    
    return jsonify({
        'gates': gates_data,
        'count': len(gates_data),
        'requesting_gate': gate.name,
        'timestamp': datetime.utcnow().isoformat()
    }), 200


@gates_bp.route('/cleanup', methods=['POST'])
@require_gate_auth
def cleanup_gate_sessions():
    """Close all active sessions and stays for calling gate (service restart).
    
    Called by gate on startup to cleanup stale sessions from previous run.
    
    Response:
        200 OK: {
            "closed_sessions": 3,
            "closed_stays": 2,
            "message": "Cleanup complete"
        }
    """
    gate = get_current_gate()
    db = get_db_session()
    
    from src.core.database import Session, Stay
    
    now = datetime.utcnow()
    
    # Close all active sessions for this gate
    active_sessions = db.query(Session).filter(
        Session.gate_id == gate.id,
        Session.is_active == True
    ).all()
    
    for session in active_sessions:
        session.is_active = False
        session.ended_at = now
        session.termination_reason = 'gate_restart'
        if session.started_at:
            session.duration_seconds = int((now - session.started_at).total_seconds())
    
    # Close all active stays for this gate  
    active_stays = db.query(Stay).filter(
        Stay.gate_id == gate.id,
        Stay.is_active == True
    ).all()
    
    for stay in active_stays:
        stay.is_active = False
        stay.ended_at = now
        stay.termination_reason = 'gate_restart'
        if stay.started_at:
            stay.duration_seconds = int((now - stay.started_at).total_seconds())
    
    db.commit()
    
    return jsonify({
        'closed_sessions': len(active_sessions),
        'closed_stays': len(active_stays),
        'gate_name': gate.name,
        'message': 'Cleanup complete',
        'timestamp': now.isoformat()
    }), 200


@gates_bp.route('/messages', methods=['GET'])
@require_gate_auth
def get_messages():
    """Get custom messages for SSH banners and error messages.
    
    Gate fetches these messages on startup and caches them.
    Messages support placeholders: {person}, {backend}, {gate_name}, {reason}
    
    Response:
        200 OK: {
            "gate_id": 1,
            "gate_name": "gate-localhost",
            "messages": {
                "welcome_banner": "...",     # Optional: Welcome after successful auth
                "no_backend": "...",         # When backend not in registry
                "no_person": "...",          # When person not recognized
                "no_grant": "...",           # When no active grant
                "maintenance": "...",        # When system in maintenance
                "time_window": "..."         # When outside time window
            },
            "timestamp": "2026-01-12T10:00:00"
        }
    """
    gate = get_current_gate()
    
    messages = {
        'welcome_banner': gate.msg_welcome_banner,
        'no_backend': gate.msg_no_backend or f"Hello, I'm Gate ({gate.name}), an entry point of Inside.\nThe IP address is not registered as a backend server in Inside registry.\nPlease contact your system administrator for assistance.",
        'no_person': gate.msg_no_person or f"Hello, I'm Gate ({gate.name}), an entry point of Inside.\nI can't recognize you and I don't know who you are.\nPlease contact your system administrator for assistance.",
        'no_grant': gate.msg_no_grant or f"Hello, I'm Gate ({gate.name}), an entry point of Inside.\nDear {{person}}, you don't have access to {{backend}}.\nPlease contact your system administrator to request access.",
        'maintenance': gate.msg_maintenance or f"Hello, I'm Gate ({gate.name}), an entry point of Inside.\nThe system is currently in maintenance mode.\nPlease try again later or contact your system administrator.",
        'time_window': gate.msg_time_window or f"Hello, I'm Gate ({gate.name}), an entry point of Inside.\nDear {{person}}, your access to {{backend}} is outside the allowed time window.\nPlease contact your system administrator for assistance."
    }
    
    return jsonify({
        'gate_id': gate.id,
        'gate_name': gate.name,
        'messages': messages,
        'timestamp': datetime.utcnow().isoformat()
    }), 200

