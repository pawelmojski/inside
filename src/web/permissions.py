"""
Permission decorators for web GUI access control.

Permission levels:
- 0: Super Admin (full access)
- 100: Admin (manage users, policies, gates, servers)
- 500: Operator (view-only, manage sessions)
- 1000: User (no GUI access)
"""
from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user


def permission_required(min_level=1000):
    """
    Decorator to check if user has required permission level.
    
    Args:
        min_level: Minimum permission level required (lower number = higher privilege)
                   0 = Super Admin only
                   100 = Admin or higher
                   500 = Operator or higher
                   1000 = Any authenticated user
    
    Usage:
        @permission_required(0)  # Super Admin only
        def delete_system():
            pass
        
        @permission_required(100)  # Admin or Super Admin
        def manage_users():
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))
            
            # Check permission level
            user_level = getattr(current_user, 'permission_level', 1000)
            
            if user_level > min_level:
                flash(
                    f'Access denied. Required permission level: {min_level}, '
                    f'your level: {user_level}',
                    'danger'
                )
                abort(403)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def admin_required(func):
    """
    Decorator for admin-only routes (permission_level <= 100).
    
    Usage:
        @admin_required
        def admin_dashboard():
            pass
    """
    return permission_required(100)(func)


def super_admin_required(func):
    """
    Decorator for super admin-only routes (permission_level == 0).
    
    Usage:
        @super_admin_required
        def system_config():
            pass
    """
    return permission_required(0)(func)


def operator_required(func):
    """
    Decorator for operator or higher routes (permission_level <= 500).
    
    Usage:
        @operator_required
        def view_logs():
            pass
    """
    return permission_required(500)(func)


def check_permission(user, min_level):
    """
    Helper function to check if user has required permission level.
    
    Args:
        user: User object
        min_level: Minimum required permission level
    
    Returns:
        bool: True if user has sufficient permissions
    """
    if not user:
        return False
    
    user_level = getattr(user, 'permission_level', 1000)
    return user_level <= min_level


def get_permission_name(level):
    """
    Get human-readable permission level name.
    
    Args:
        level: Permission level integer
    
    Returns:
        str: Permission level name
    """
    if level == 0:
        return 'Super Admin'
    elif level <= 100:
        return 'Admin'
    elif level <= 500:
        return 'Operator'
    else:
        return 'User'
