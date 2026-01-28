"""
Session grant status endpoint for simplified v1.11 architecture.

Returns current effective grant end time for a session.
This is THE SINGLE SOURCE OF TRUTH for grant expiry monitoring.
"""

from flask import Blueprint, jsonify
from src.core.database import get_db, Session as DBSession, AccessPolicy
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)
bp = Blueprint('sessions_grant_status', __name__)


@bp.route('/api/v1/sessions/<int:session_id>/grant_status', methods=['GET'])
def get_session_grant_status(session_id):
    """
    Get current grant status for a session.
    
    This endpoint is called periodically by Gate monitor threads to check
    if grant is still valid and when it expires.
    
    Returns:
        {
            'valid': bool,  # Is grant still valid?
            'end_time': str or null,  # ISO format with 'Z' suffix (UTC), null = permanent
            'reason': str  # If invalid: reason for denial
        }
    """
    db = next(get_db())
    
    try:
        # Get session from database
        db_session = db.query(DBSession).filter_by(id=session_id).first()
        if not db_session:
            return jsonify({'error': 'Session not found'}), 404
        
        # Get grant (policy) for this session
        if not db_session.policy_id:
            # No policy = permanent access (legacy session)
            return jsonify({
                'valid': True,
                'end_time': None,
                'reason': None
            })
        
        policy = db.query(AccessPolicy).get(db_session.policy_id)
        if not policy:
            return jsonify({
                'valid': False,
                'end_time': None,
                'reason': 'Grant not found'
            })
        
        # Check if policy is still active
        now = datetime.utcnow()
        if policy.start_time and now < policy.start_time:
            return jsonify({
                'valid': False,
                'end_time': None,
                'reason': 'Grant not yet active'
            })
        
        if policy.end_time and now >= policy.end_time:
            return jsonify({
                'valid': False,
                'end_time': None,
                'reason': 'Grant expired'
            })
        
        # Grant still valid - return end time
        # NOTE: This doesn't check schedules - monitor will detect forced disconnect via heartbeat
        if policy.end_time:
            # Database stores naive UTC datetime - add 'Z' suffix
            end_time_str = policy.end_time.isoformat() + 'Z'
        else:
            end_time_str = None  # Permanent grant
        
        return jsonify({
            'valid': True,
            'end_time': end_time_str,
            'reason': None
        })
    finally:
        db.close()
