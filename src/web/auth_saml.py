"""
SAML Authentication Blueprint
Handles Azure AD SAML SSO for MFA and GUI login
"""

from flask import Blueprint, request, redirect, Response, render_template_string, url_for
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.utils import OneLogin_Saml2_Utils
import sys
import os
import logging
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from config.saml_config import SAML_SETTINGS, INSIDE_ACCESS_GROUP_ID
from src.core.database import SessionLocal, MFAChallenge, User, Stay, AuditLog, UserGroup
from sqlalchemy import text

saml_bp = Blueprint('saml', __name__, url_prefix='/auth/saml')
logger = logging.getLogger(__name__)

AUTO_CREATED_GROUP_NAME = 'Auto-Created Users'

def ensure_auto_created_group(db):
    """Ensure 'Auto-Created Users' group exists, create if missing."""
    group = db.query(UserGroup).filter(UserGroup.name == AUTO_CREATED_GROUP_NAME).first()
    if not group:
        group = UserGroup(
            name=AUTO_CREATED_GROUP_NAME,
            description='Users automatically created via SAML authentication',
            is_active=True
        )
        db.add(group)
        db.flush()
        logger.info(f"Created auto-created user group: {AUTO_CREATED_GROUP_NAME} (ID: {group.id})")
    return group

def add_user_to_group(db, user_id, group_id):
    """Add user to group if not already a member."""
    # Check if already member
    existing = db.execute(
        text("SELECT 1 FROM user_group_members WHERE user_id = :uid AND user_group_id = :gid"),
        {"uid": user_id, "gid": group_id}
    ).first()
    
    if not existing:
        db.execute(
            text("INSERT INTO user_group_members (user_id, user_group_id) VALUES (:uid, :gid)"),
            {"uid": user_id, "gid": group_id}
        )
        logger.info(f"Added user {user_id} to group {group_id}")



def prepare_flask_request():
    """Prepare request data for python3-saml
    
    Force HTTPS scheme since Flask runs behind nginx reverse proxy.
    """
    url_data = request.url.split('?')
    return {
        'https': 'on',  # Force HTTPS - Flask is behind nginx proxy
        'http_host': request.host.split(':')[0],  # Remove port if present
        'script_name': request.path,
        'server_port': 443,  # Force HTTPS port
        'get_data': request.args.copy(),
        'post_data': request.form.copy(),
        'query_string': url_data[1] if len(url_data) > 1 else ''
    }


@saml_bp.route('/login')
def saml_login():
    """Initiate SAML login flow
    
    Query params:
        token: MFA challenge token (becomes RelayState)
    """
    mfa_token = request.args.get('token')
    
    if not mfa_token:
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head><title>MFA Error</title></head>
        <body style="font-family: Arial, sans-serif; padding: 50px; text-align: center;">
            <h1>❌ MFA Error</h1>
            <p>Missing MFA token. Please try connecting to the server again.</p>
        </body>
        </html>
        """), 400
    
    # Validate token exists
    db = SessionLocal()
    try:
        challenge = db.query(MFAChallenge).filter(MFAChallenge.token == mfa_token).first()
        if not challenge:
            return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head><title>Invalid MFA Token</title></head>
            <body style="font-family: Arial, sans-serif; padding: 50px; text-align: center;">
                <h1>❌ Invalid MFA Token</h1>
                <p>This MFA token is not recognized. Please try connecting again.</p>
            </body>
            </html>
            """), 400
        
        if challenge.expires_at < datetime.utcnow():
            return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head><title>MFA Token Expired</title></head>
            <body style="font-family: Arial, sans-serif; padding: 50px; text-align: center;">
                <h1>⏰ MFA Token Expired</h1>
                <p>This MFA token has expired (5 minute timeout).</p>
                <p>Please try connecting to the server again to get a new token.</p>
            </body>
            </html>
            """), 410
    finally:
        db.close()
    
    # Initiate SAML SSO
    req = prepare_flask_request()
    auth = OneLogin_Saml2_Auth(req, SAML_SETTINGS)
    
    # RelayState = MFA token (preserved through SAML flow)
    return redirect(auth.login(return_to=mfa_token))


@saml_bp.route('/acs', methods=['POST'])
def saml_acs():
    """Assertion Consumer Service - receives SAML response from Azure AD"""
    req = prepare_flask_request()
    auth = OneLogin_Saml2_Auth(req, SAML_SETTINGS)
    
    # Process SAML response
    auth.process_response()
    errors = auth.get_errors()
    
    if len(errors) > 0:
        error_reason = auth.get_last_error_reason()
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head><title>SAML Authentication Failed</title></head>
        <body style="font-family: Arial, sans-serif; padding: 50px; text-align: center;">
            <h1>❌ SAML Authentication Failed</h1>
            <p>Errors: {{ errors }}</p>
            <p>Reason: {{ reason }}</p>
            <p>Please contact your administrator if this problem persists.</p>
        </body>
        </html>
        """, errors=', '.join(errors), reason=error_reason), 400
    
    if not auth.is_authenticated():
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head><title>Authentication Failed</title></head>
        <body style="font-family: Arial, sans-serif; padding: 50px; text-align: center;">
            <h1>❌ Authentication Failed</h1>
            <p>SAML authentication did not succeed.</p>
        </body>
        </html>
        """), 401
    
    # Extract SAML attributes
    attributes = auth.get_attributes()
    nameid = auth.get_nameid()  # Email address
    
    if not nameid:
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head><title>SAML Error</title></head>
        <body style="font-family: Arial, sans-serif; padding: 50px; text-align: center;">
            <h1>❌ SAML Error</h1>
            <p>Missing email (NameID) in SAML response.</p>
        </body>
        </html>
        """), 400
    
    # Get RelayState (either 'gui' or MFA token)
    relay_state = request.form.get('RelayState', '')
    
    if not relay_state:
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head><title>SAML Error</title></head>
        <body style="font-family: Arial, sans-serif; padding: 50px; text-align: center;">
            <h1>❌ SAML Error</h1>
            <p>Missing RelayState in SAML response.</p>
        </body>
        </html>
        """), 400
    
    # ============ ROUTE TO APPROPRIATE FLOW ============
    if relay_state == 'gui':
        # GUI LOGIN FLOW
        return _handle_gui_saml_login(nameid, attributes)
    else:
        # MFA SESSION FLOW (relay_state is MFA token)
        return _handle_mfa_saml_auth(nameid, attributes, relay_state)


def _handle_gui_saml_login(nameid, attributes):
    """Handle GUI login after SAML authentication"""
    from flask_login import login_user
    
    saml_email = nameid.lower()
    saml_full_name = attributes.get('http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name', [saml_email])[0] if attributes else None
    
    db = SessionLocal()
    try:
        # Find or create user
        user = db.query(User).filter(User.email == saml_email).first()
        
        # Check if disabled
        if user and not user.is_active:
            logger.warning(f"Disabled user attempted GUI login: {saml_email}")
            return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head><title>Account Disabled</title></head>
            <body style="font-family: Arial, sans-serif; padding: 50px; text-align: center;">
                <h1>❌ Account Disabled</h1>
                <p>Your account has been disabled. Contact administrator.</p>
            </body>
            </html>
            """), 403
        
        if not user:
            # Auto-create user
            try:
                username = saml_email.split('@')[0]
                existing = db.query(User).filter(User.username == username).first()
                if existing:
                    username = saml_email.replace('@', '_').replace('.', '_')
                
                user = User(
                    username=username,
                    email=saml_email,
                    full_name=saml_full_name or saml_email,
                    is_active=True,
                    port_forwarding_allowed=False,
                    permission_level=900  # Regular user (GUI access)
                )
                db.add(user)
                db.flush()
                
                # Add to Auto-Created Users group
                auto_group = ensure_auto_created_group(db)
                add_user_to_group(db, user.id, auto_group.id)
                
                audit = AuditLog(
                    user_id=user.id,
                    action='auto_user_create_gui',
                    details=f'Auto-created from GUI SAML: {saml_email}',
                    source_ip=request.remote_addr,
                    success=True
                )
                db.add(audit)
                db.commit()
                
                logger.info(f"Auto-created user for GUI: {username} ({saml_email})")
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to auto-create user: {e}", exc_info=True)
                return render_template_string("""
                <!DOCTYPE html>
                <html>
                <head><title>Error</title></head>
                <body style="font-family: Arial, sans-serif; padding: 50px; text-align: center;">
                    <h1>❌ Failed to Create Account</h1>
                    <p>{{ error }}</p>
                </body>
                </html>
                """, error=str(e)), 500
        
        # Check permission (must be < 1000 for GUI)
        if user.permission_level >= 1000:
            logger.warning(f"User {user.username} (level={user.permission_level}) denied GUI access")
            return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head><title>Access Denied</title></head>
            <body style="font-family: Arial, sans-serif; padding: 50px; text-align: center;">
                <h1>❌ GUI Access Denied</h1>
                <p>Your permission level does not allow GUI access.</p>
            </body>
            </html>
            """), 403
        
        # Login to Flask session
        login_user(user, remember=True)
        
        # Audit log
        audit = AuditLog(
            user_id=user.id,
            action='gui_login_saml',
            details=f'GUI login via SAML: {user.username}',
            source_ip=request.remote_addr,
            success=True
        )
        db.add(audit)
        db.commit()
        
        logger.info(f"User logged into GUI via SAML: {user.username} (level={user.permission_level})")
        
        # Redirect to dashboard
        return redirect(url_for('dashboard.index'))
        
    except Exception as e:
        db.rollback()
        logger.error(f"GUI SAML login error: {e}", exc_info=True)
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head><title>Login Error</title></head>
        <body style="font-family: Arial, sans-serif; padding: 50px; text-align: center;">
            <h1>❌ Login Error</h1>
            <p>{{ error }}</p>
        </body>
        </html>
        """, error=str(e)), 500
    finally:
        db.close()


def _handle_mfa_saml_auth(nameid, attributes, mfa_token):
    """Handle MFA session authentication (original flow for SSH/RDP)"""
    
    # Database operations
    db = SessionLocal()
    try:
        # Get MFA challenge
        challenge = db.query(MFAChallenge).filter(
            MFAChallenge.token == mfa_token,
            MFAChallenge.verified == False
        ).first()
        
        if not challenge:
            return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head><title>Invalid MFA Challenge</title></head>
            <body style="font-family: Arial, sans-serif; padding: 50px; text-align: center;">
                <h1>❌ Invalid MFA Challenge</h1>
                <p>MFA token not found or already used.</p>
            </body>
            </html>
            """), 400
        
        if challenge.expires_at < datetime.utcnow():
            return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head><title>MFA Expired</title></head>
            <body style="font-family: Arial, sans-serif; padding: 50px; text-align: center;">
                <h1>⏰ MFA Expired</h1>
                <p>This MFA challenge has expired.</p>
            </body>
            </html>
            """), 410
        
        # Extract email from SAML response
        saml_email = nameid.lower()
        
        # Extract additional SAML attributes (optional)
        saml_attributes = attributes
        saml_full_name = saml_attributes.get('http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name', [saml_email])[0] if saml_attributes else None
        
        # Find user by email (Phase 2 - user identified via SAML)
        if not challenge.user_id:
            # Phase 2: User not known yet, identify by SAML email
            user = db.query(User).filter(User.email == saml_email).first()
            
            if not user:
                # AUTO-CREATE USER from SAML
                # Extract username from email (before @ symbol)
                try:
                    username = saml_email.split('@')[0]
                    
                    # Check if username already exists (collision from different domain)
                    existing_user = db.query(User).filter(User.username == username).first()
                    if existing_user:
                        # Use full email as username if collision
                        username = saml_email.replace('@', '_').replace('.', '_')
                    
                    # Create new user
                    user = User(
                        username=username,
                        email=saml_email,
                        full_name=saml_full_name or saml_email,
                        is_active=True,
                        port_forwarding_allowed=False,
                        permission_level=900  # Regular user (can access GUI to view own data)
                    )
                    db.add(user)
                    db.flush()  # Get user ID
                    
                    # Log auto-creation
                    audit = AuditLog(
                        user_id=user.id,
                        action='auto_user_create',
                        details=f'Auto-created user from SAML: {saml_email}',
                        source_ip=request.remote_addr
                    )
                    db.add(audit)
                    db.commit()
                    
                    logger.info(
                        f"Auto-created user: username={user.username}, "
                        f"email={saml_email}, id={user.id}"
                    )
                    
                except Exception as e:
                    db.rollback()
                    logger.error(f"Failed to auto-create user from SAML: {e}", exc_info=True)
                    return render_template_string("""
                    <!DOCTYPE html>
                    <html>
                    <head><title>User Creation Failed</title></head>
                    <body style="font-family: Arial, sans-serif; padding: 50px; text-align: center;">
                        <h1>❌ Failed to Create User</h1>
                        <p>Email: {{ email }}</p>
                        <p>Error: {{ error }}</p>
                        <p>Please contact your administrator.</p>
                    </body>
                    </html>
                    """, email=saml_email, error=str(e)), 500
            
            # Update challenge with identified user
            challenge.user_id = user.id
            challenge.saml_email = saml_email
        else:
            # Phase 1: User already known, verify email match
            user = db.query(User).filter(User.id == challenge.user_id).first()
            
            if not user:
                return render_template_string("""
                <!DOCTYPE html>
                <html>
                <head><title>User Not Found</title></head>
                <body style="font-family: Arial, sans-serif; padding: 50px; text-align: center;">
                    <h1>❌ User Not Found</h1>
                    <p>User ID {{ user_id }} not found in Inside database.</p>
                    <p>Please contact your administrator.</p>
                </body>
                </html>
                """, user_id=challenge.user_id), 403
            
            # Verify email match
            user_email = (user.email or '').lower()
            
            if user_email != saml_email:
                return render_template_string("""
                <!DOCTYPE html>
            <html>
            <head><title>Email Mismatch</title></head>
            <body style="font-family: Arial, sans-serif; padding: 50px; text-align: center;">
                <h1>❌ Email Mismatch</h1>
                <p>SAML email: <strong>{{ saml_email }}</strong></p>
                <p>Inside user email: <strong>{{ user_email }}</strong></p>
                <p>Emails must match for security. Please contact your administrator.</p>
            </body>
            </html>
            """, saml_email=saml_email, user_email=user_email), 403
        
        # Mark MFA challenge as verified (Stay will be created by Gate when SSH actually connects)
        challenge.verified = True
        challenge.verified_at = datetime.utcnow()
        challenge.saml_email = saml_email
        
        db.commit()
        
        # Success page
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>MFA Successful</title>
            <meta http-equiv="refresh" content="3;url={{ dashboard_url }}">
        </head>
        <body style="font-family: Arial, sans-serif; padding: 50px; text-align: center;">
            <h1>✅ MFA Authentication Successful!</h1>
            <p>Authenticated as: <strong>{{ email }}</strong></p>
            <p>Username: <strong>{{ username }}</strong></p>
            <hr>
            <p style="font-size: 18px; color: green;">
                You can now <strong>return to your terminal</strong>.<br>
                Your SSH session will continue automatically.
            </p>
            <p style="color: #666; margin-top: 30px;">
                You can close this browser window or you will be redirected to the dashboard in 3 seconds...
            </p>
        </body>
        </html>
        """, email=saml_email, username=user.username, dashboard_url=url_for('dashboard.index'))
        
    except Exception as e:
        db.rollback()
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head><title>MFA Error</title></head>
        <body style="font-family: Arial, sans-serif; padding: 50px; text-align: center;">
            <h1>❌ MFA Error</h1>
            <p>An error occurred: {{ error }}</p>
            <p>Please try again or contact your administrator.</p>
        </body>
        </html>
        """, error=str(e)), 500
    finally:
        db.close()


@saml_bp.route('/login-gui')
def saml_login_gui():
    """Initiate SAML login flow for GUI access (not MFA session)
    
    This is used when user clicks "Login with Microsoft 365" on login page.
    RelayState is set to 'gui' to distinguish from MFA session flow.
    """
    # Check if already logged in
    from flask_login import current_user
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    # Initiate SAML SSO with RelayState='gui'
    req = prepare_flask_request()
    auth = OneLogin_Saml2_Auth(req, SAML_SETTINGS)
    
    return redirect(auth.login(return_to='gui'))


@saml_bp.route('/metadata')
def saml_metadata():
    """Service Provider metadata for Azure AD configuration"""
    req = prepare_flask_request()
    auth = OneLogin_Saml2_Auth(req, SAML_SETTINGS)
    settings = auth.get_settings()
    metadata = settings.get_sp_metadata()
    errors = settings.validate_metadata(metadata)
    
    if len(errors) > 0:
        return Response(f"Metadata errors: {', '.join(errors)}", status=500, mimetype='text/plain')
    
    return Response(metadata, mimetype='text/xml')


@saml_bp.route('/sls')
def saml_sls():
    """Single Logout Service (optional)"""
    return "Logout not implemented yet", 501
