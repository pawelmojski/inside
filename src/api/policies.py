"""Tower API - Policy endpoints for internal use (UI).

Provides policy information for tooltips and UI elements.
"""

from flask import Blueprint, jsonify
from src.core.database import SessionLocal, AccessPolicy
import logging

logger = logging.getLogger(__name__)

policies_api_bp = Blueprint('policies_api', __name__, url_prefix='/api/v1/policies')


@policies_api_bp.route('/<int:policy_id>')
def get_policy(policy_id):
    """Get policy details for UI tooltips.
    
    Returns policy summary information for display in popovers.
    """
    db = SessionLocal()
    try:
        policy = db.query(AccessPolicy).filter(AccessPolicy.id == policy_id).first()
        
        if not policy:
            return jsonify({'error': 'Policy not found'}), 404
        
        # Build display strings for users/servers
        user_display = 'Any'
        if policy.user_id:
            user_display = policy.user.full_name if policy.user else f'User #{policy.user_id}'
        elif policy.user_group_id:
            user_display = f'Group: {policy.user_group.name}' if policy.user_group else f'Group #{policy.user_group_id}'
        
        server_display = 'Any'
        if policy.server_id:
            server_display = policy.server.name if policy.server else f'Server #{policy.server_id}'
        elif policy.server_group_id:
            server_display = f'Group: {policy.server_group.name}' if policy.server_group else f'Group #{policy.server_group_id}'
        
        return jsonify({
            'id': policy.id,
            'description': policy.description,
            'user_display': user_display,
            'server_display': server_display,
            'ssh_username': policy.ssh_username,
            'protocol': policy.protocol,
            'priority': policy.priority,
            'enabled': policy.enabled
        })
        
    finally:
        db.close()
