#!/usr/bin/env python3
"""
Jumphost Web GUI - Main Flask Application
Flask-based web interface for managing SSH/RDP jumphost access control.
"""

import os
import sys
import logging
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_required, current_user
from werkzeug.middleware.proxy_fix import ProxyFix
import pytz

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.core.database import SessionLocal, User, Server, ServerGroup, AccessPolicy, AuditLog
from src.core.access_control_v2 import AccessControlEngineV2

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://jumphost_user:password@localhost/jumphost')
app.config['PREFERRED_URL_SCHEME'] = 'https'

# Apply ProxyFix middleware - Flask is behind nginx reverse proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access the Jumphost Web GUI.'

# Initialize Access Control Engine
access_control = AccessControlEngineV2()

@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login"""
    db = SessionLocal()
    try:
        user = db.query(User).get(int(user_id))
        if user:
            # Merge user into current session to avoid detached instance
            db.expunge(user)
        return user
    finally:
        db.close()

# Database session management
@app.before_request
def before_request():
    """Create database session before each request"""
    from flask import g
    g.db = SessionLocal()

@app.teardown_request
def teardown_request(exception=None):
    """Close database session after each request"""
    from flask import g
    db = g.pop('db', None)
    if db is not None:
        db.close()

# Template filters
@app.template_filter('datetime')
def format_datetime(value):
    """Format datetime for display"""
    if value is None:
        return ''
    return value.strftime('%Y-%m-%d %H:%M:%S')

@app.template_filter('localtime')
def format_localtime(value):
    """Convert UTC datetime to Europe/Warsaw timezone for display"""
    if value is None:
        return ''
    warsaw_tz = pytz.timezone('Europe/Warsaw')
    # If naive datetime, assume it's UTC
    if value.tzinfo is None:
        value = pytz.utc.localize(value)
    # Convert to Warsaw time
    local_time = value.astimezone(warsaw_tz)
    return local_time.strftime('%Y-%m-%d %H:%M:%S %Z')

@app.template_filter('time_only')
def format_time_only(value):
    """Convert UTC datetime to Europe/Warsaw timezone and return only HH:MM:SS"""
    if value is None:
        return ''
    warsaw_tz = pytz.timezone('Europe/Warsaw')
    # If naive datetime, assume it's UTC
    if value.tzinfo is None:
        value = pytz.utc.localize(value)
    # Convert to Warsaw time
    local_time = value.astimezone(warsaw_tz)
    return local_time.strftime('%H:%M:%S')

@app.template_filter('time_short')
def format_time_short(value):
    """Convert UTC datetime to Europe/Warsaw timezone and return only HH:MM"""
    if value is None:
        return ''
    warsaw_tz = pytz.timezone('Europe/Warsaw')
    # If naive datetime, assume it's UTC
    if value.tzinfo is None:
        value = pytz.utc.localize(value)
    # Convert to Warsaw time
    local_time = value.astimezone(warsaw_tz)
    return local_time.strftime('%H:%M')

@app.template_filter('date')
def format_date(value):
    """Format date for display"""
    if value is None:
        return ''
    return value.strftime('%Y-%m-%d')

@app.template_filter('timeago')
def format_timeago(value):
    """Format datetime as relative time ago"""
    if value is None:
        return ''
    from datetime import datetime, timezone
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    diff = now - value
    
    seconds = diff.total_seconds()
    if seconds < 60:
        return 'just now'
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f'{minutes}m ago'
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f'{hours}h ago'
    else:
        days = int(seconds / 86400)
        return f'{days}d ago'

@app.template_filter('highlight_esc')
def highlight_escape_sequences(value):
    """Highlight escape sequences in HTML"""
    if value is None:
        return ''
    import re
    from markupsafe import Markup
    # Highlight <ESC>, <NUL>, <BEL>, <BS>, <DEL> tags
    value = re.sub(r'&lt;(ESC|NUL|BEL|BS|DEL)&gt;', r'<span class="esc-tag">&lt;\1&gt;</span>', value)
    return Markup(value)

# Context processor for global template variables
@app.context_processor
def inject_globals():
    """Inject global variables into all templates"""
    return {
        'app_name': 'Jumphost Web GUI',
        'app_version': '1.0',
        'now': datetime.now()
    }

# Import and register blueprints
from blueprints.dashboard import dashboard_bp
from blueprints.users import users_bp
from blueprints.servers import servers_bp
from blueprints.groups import groups_bp
from blueprints.user_groups import user_groups_bp
from blueprints.policies import policies_bp
from blueprints.sessions import sessions_bp
from blueprints.monitoring import monitoring_bp
from blueprints.auth import auth_bp
from blueprints.gates import gates_bp as gates_ui_bp  # Web UI for gates management
from blueprints.stays import stays_bp as stays_ui_bp  # Web UI for stays tracking
from search import search_bp
from auth_saml import saml_bp  # SAML authentication for MFA

# Import Tower API blueprints
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from api.grants import grants_bp
from api.stays import stays_bp as stays_api_bp  # API for gate communication
from api.gates import gates_bp as gates_api_bp  # API for gate communication
from api.maintenance import maintenance_bp  # API for maintenance mode
from api.mfa import mfa_bp  # API for MFA challenge/status
from api.mfa_pending import mfa_pending_bp  # API for pending MFA list

app.register_blueprint(dashboard_bp, url_prefix='/')
app.register_blueprint(users_bp, url_prefix='/users')
app.register_blueprint(servers_bp, url_prefix='/servers')
app.register_blueprint(groups_bp, url_prefix='/groups')
app.register_blueprint(user_groups_bp, url_prefix='/user-groups')
app.register_blueprint(policies_bp, url_prefix='/policies')
app.register_blueprint(sessions_bp, url_prefix='/sessions')
app.register_blueprint(stays_ui_bp, url_prefix='/stays')  # Web UI for stays
app.register_blueprint(monitoring_bp, url_prefix='/monitoring')
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(saml_bp)  # SAML endpoints (/auth/saml/*)
app.register_blueprint(gates_ui_bp, url_prefix='/gates')  # Web UI for gates
app.register_blueprint(search_bp, url_prefix='/search')

# Register Tower API blueprints (for Gate communication)
app.register_blueprint(grants_bp)
app.register_blueprint(stays_api_bp, name='stays_api')  # API endpoint, unique name
app.register_blueprint(gates_api_bp, name='gates_api')  # API for gates (/api/v1/gates/*) - unique name
app.register_blueprint(maintenance_bp)  # Maintenance mode endpoints
app.register_blueprint(mfa_bp)  # MFA API (/api/v1/mfa/*)
app.register_blueprint(mfa_pending_bp)  # MFA pending list (/api/v1/mfa/pending)

from src.api.sessions import api_sessions_bp
app.register_blueprint(api_sessions_bp)

from src.api.sessions_grant_status import bp as sessions_grant_status_bp
app.register_blueprint(sessions_grant_status_bp)

from src.api.recordings import recordings_bp
app.register_blueprint(recordings_bp)

from src.api.policies import policies_api_bp
app.register_blueprint(policies_api_bp)

# Favicon route (prevent 404 errors)
@app.route('/favicon.ico')
def favicon():
    """Serve favicon or return 204 No Content"""
    return '', 204

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('errors/500.html'), 500

if __name__ == '__main__':
    # Development server
    app.run(host='0.0.0.0', port=5000, debug=True)
