"""
Whoami endpoint - check current authenticated user
"""
from flask import Blueprint, jsonify
from flask_login import current_user, login_required

whoami_bp = Blueprint('whoami', __name__)


@whoami_bp.route('/api/whoami')
@login_required
def whoami():
    """
    Return information about currently authenticated user.
    
    Useful for debugging session issues.
    """
    return jsonify({
        'authenticated': current_user.is_authenticated,
        'id': current_user.id,
        'username': current_user.username,
        'email': current_user.email,
        'full_name': current_user.full_name,
        'permission_level': current_user.permission_level,
        'is_active': current_user.is_active,
        'permission_name': _get_permission_name(current_user.permission_level)
    })


def _get_permission_name(level):
    """Get human-readable permission name"""
    if level == 0:
        return 'Super Admin'
    elif level <= 100:
        return 'Admin'
    elif level <= 500:
        return 'Operator'
    else:
        return 'User (no GUI access)'
