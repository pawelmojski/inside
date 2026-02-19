"""
Admin API Blueprint - Admin console operations
Endpoints for gate-based admin console (uses gate authentication)
"""
from flask import Blueprint, jsonify, g, request, abort
from datetime import datetime
from src.core.database import Session, Stay, User, Server
from src.api.auth import require_gate_auth, get_current_gate, get_db_session
from sqlalchemy import and_

admin_api_bp = Blueprint('admin_api', __name__, url_prefix='/api/v1/admin')


@admin_api_bp.route('/active-stays', methods=['GET'])
@require_gate_auth
def get_active_stays():
    """Get all active stays for admin console (gate auth)"""
    db = get_db_session()
    
    try:
        stays = db.query(Stay).filter(Stay.is_active == True).order_by(Stay.started_at.desc()).all()
        
        stays_list = []
        now = datetime.utcnow()
        
        for stay in stays:
            duration = int((now - stay.started_at).total_seconds())
            
            stays_list.append({
                'id': stay.id,
                'user_id': stay.user.id if stay.user else None,
                'user_name': stay.user.full_name or stay.user.username if stay.user else 'Unknown',
                'started_at': stay.started_at.isoformat(),
                'duration': duration,
                'sessions': [{
                    'session_id': s.session_id,
                    'protocol': s.protocol,
                    'backend_ip': s.backend_ip,
                    'is_active': s.is_active
                } for s in stay.sessions]
            })
        
        return jsonify({'stays': stays_list}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_api_bp.route('/active-sessions', methods=['GET'])
@require_gate_auth
def get_active_sessions():
    """Get all active sessions for admin console (gate auth)"""
    db = get_db_session()
    
    try:
        sessions = db.query(Session).filter(Session.is_active == True).order_by(Session.started_at.desc()).all()
        
        sessions_list = []
        now = datetime.utcnow()
        
        for sess in sessions:
            duration = int((now - sess.started_at).total_seconds())
            
            sessions_list.append({
                'session_id': sess.session_id,
                'user_id': sess.user.id if sess.user else None,
                'user_name': sess.user.full_name or sess.user.username if sess.user else 'Unknown',
                'protocol': sess.protocol,
                'ssh_username': sess.ssh_username,
                'server_id': sess.server.id if sess.server else None,
                'server_name': sess.server.name if sess.server else None,
                'backend_ip': sess.backend_ip,
                'source_ip': sess.source_ip,
                'started_at': sess.started_at.isoformat(),
                'duration': duration,
                'subsystem_name': sess.subsystem_name if hasattr(sess, 'subsystem_name') else None
            })
        
        return jsonify({'sessions': sessions_list}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_api_bp.route('/kill-session/<session_id>', methods=['POST'])
@require_gate_auth
def kill_session(session_id):
    """Terminate a session (admin console)"""
    db = get_db_session()
    
    try:
        # Find session
        session = db.query(Session).filter(Session.session_id == session_id).first()
        
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        if not session.is_active:
            return jsonify({'error': 'Session already terminated'}), 400
        
        # Mark for termination - gate will pick this up via heartbeat
        gate = get_current_gate()
        gate_name = gate.get('name', 'unknown') if isinstance(gate, dict) else getattr(gate, 'name', 'unknown')
        session.termination_reason = f"Killed by admin via gate: {gate_name}"
        session.is_active = False
        session.ended_at = datetime.utcnow()
        session.duration_seconds = int((session.ended_at - session.started_at).total_seconds())
        
        db.commit()
        
        # TODO: Notify gate to immediately disconnect (via Redis/WebSocket if available)
        # For now, gate will pick this up on next heartbeat check
        
        return jsonify({
            'success': True,
            'message': f'Session {session_id} marked for termination',
            'session_id': session_id
        }), 200
    
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500
