"""Tower API - Bearer token authentication for Gate clients.

This module provides authentication middleware for Tower API endpoints.
Gates authenticate using Bearer tokens stored in gates.api_token.
"""

from functools import wraps
from flask import request, jsonify, g
from sqlalchemy.orm import Session
from src.core.database import SessionLocal, Gate


def require_gate_auth(f):
    """Decorator to require valid Gate Bearer token authentication.
    
    Usage:
        @app.route('/api/v1/resource')
        @require_gate_auth
        def protected_endpoint():
            gate = g.current_gate  # Access authenticated gate
            return jsonify(...)
    
    Request headers:
        Authorization: Bearer {GATE_TOKEN}
    
    Returns:
        401 if token missing or invalid
        403 if gate is inactive (is_active=False means gate is compromised/disabled)
        Calls wrapped function if authentication succeeds
    
    Note: Maintenance mode uses gate.in_maintenance, not is_active.
          is_active=False permanently blocks ALL gate operations.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({
                'error': 'missing_token',
                'message': 'Authorization header required'
            }), 401
        
        if not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'invalid_token_format',
                'message': 'Authorization header must be "Bearer {token}"'
            }), 401
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        
        if not token:
            return jsonify({
                'error': 'empty_token',
                'message': 'Bearer token cannot be empty'
            }), 401
        
        # Validate token against database
        db: Session = SessionLocal()
        try:
            gate = db.query(Gate).filter(Gate.api_token == token).first()
            
            if not gate:
                return jsonify({
                    'error': 'invalid_token',
                    'message': 'Token not recognized'
                }), 401
            
            if not gate.is_active:
                return jsonify({
                    'error': 'gate_inactive',
                    'message': f'Gate "{gate.name}" is deactivated'
                }), 403
            
            # Store authenticated gate in Flask g for use in endpoint
            g.current_gate = gate
            g.db_session = db
            
            return f(*args, **kwargs)
        
        finally:
            db.close()
    
    return decorated_function


def get_current_gate() -> Gate:
    """Get the currently authenticated Gate from request context.
    
    Must be called within a request context protected by @require_gate_auth.
    
    Returns:
        Gate object for authenticated gate
    
    Raises:
        RuntimeError if called outside authenticated context
    """
    if not hasattr(g, 'current_gate'):
        raise RuntimeError('get_current_gate() called outside @require_gate_auth context')
    
    return g.current_gate


def get_db_session() -> Session:
    """Get the database session from request context.
    
    Must be called within a request context protected by @require_gate_auth.
    
    Returns:
        SQLAlchemy Session object
    
    Raises:
        RuntimeError if called outside authenticated context
    """
    if not hasattr(g, 'db_session'):
        raise RuntimeError('get_db_session() called outside @require_gate_auth context')
    
    return g.db_session
