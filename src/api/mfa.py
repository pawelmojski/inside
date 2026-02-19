"""
MFA API Blueprint
Gate communication endpoints for MFA challenges
"""

from flask import Blueprint, request, jsonify, g
import secrets
import logging
from datetime import datetime, timedelta
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.api.auth import require_gate_auth
from src.core.database import SessionLocal, MFAChallenge, User, Stay, AccessPolicy
from config.saml_config import MFA_CHALLENGE_TIMEOUT_MINUTES, MFA_TOKEN_LENGTH, TOWER_BASE_URL

mfa_bp = Blueprint('mfa', __name__, url_prefix='/api/v1/mfa')
logger = logging.getLogger(__name__)


@mfa_bp.route('/challenge', methods=['POST'])
@require_gate_auth
def create_mfa_challenge():
    """Create MFA challenge for Gate
    
    Request JSON (Phase 1 - with known user):
        {
            "user_id": int,
            "grant_id": int,
            "ssh_username": str
        }
    
    Request JSON (Phase 2 - unknown user, will be identified via SAML):
        {
            "destination_ip": str,
            "ssh_username": str
        }
    
    Response:
        {
            "mfa_required": true,
            "mfa_token": str,
            "mfa_url": str,
            "mfa_qr": str (ASCII art QR code),
            "timeout_minutes": int
        }
    """
    gate = g.current_gate
    db = g.db_session
    
    data = request.get_json()
    user_id = data.get('user_id')  # Optional in Phase 2
    grant_id = data.get('grant_id')  # Optional in Phase 2
    destination_ip = data.get('destination_ip')  # Required in Phase 2
    source_ip = data.get('source_ip')  # Client source IP
    ssh_username = data.get('ssh_username')
    
    if not ssh_username:
        return jsonify({
            'error': 'missing_parameters',
            'message': 'ssh_username is required'
        }), 400
    
    # Phase 1: Known user (user_id provided)
    # Phase 2: Unknown user (destination_ip provided, user identified via SAML)
    if user_id:
        # Phase 1 - verify user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return jsonify({
                'error': 'user_not_found',
                'message': f'User ID {user_id} not found'
            }), 404
        
        # Verify grant exists
        if grant_id:
            grant = db.query(AccessPolicy).filter(AccessPolicy.id == grant_id).first()
            if not grant:
                return jsonify({
                    'error': 'grant_not_found',
                    'message': f'Grant ID {grant_id} not found'
                }), 404
    elif not destination_ip:
        return jsonify({
            'error': 'missing_parameters',
            'message': 'Either user_id or destination_ip must be provided'
        }), 400
    
    # Generate MFA token
    mfa_token = secrets.token_urlsafe(MFA_TOKEN_LENGTH)
    
    # Create MFA challenge
    expires_at = datetime.utcnow() + timedelta(minutes=MFA_CHALLENGE_TIMEOUT_MINUTES)
    
    challenge = MFAChallenge(
        token=mfa_token,
        gate_id=gate.id,
        user_id=user_id,  # Can be None in Phase 2
        grant_id=grant_id,  # Can be None in Phase 2
        ssh_username=ssh_username,
        source_ip=source_ip,  # Client source IP
        destination_ip=destination_ip,  # Phase 2: for grant lookup after SAML
        created_at=datetime.utcnow(),
        expires_at=expires_at,
        verified=False
    )
    
    db.add(challenge)
    db.commit()
    
    # Build MFA URL
    mfa_url = f"{TOWER_BASE_URL}/auth/saml/login?token={mfa_token}"
    
    # Generate ASCII QR code
    try:
        import qrcode
        qr = qrcode.QRCode()
        qr.add_data(mfa_url)
        qr.make()
        
        # Get ASCII representation
        from io import StringIO
        qr_ascii = StringIO()
        qr.print_ascii(out=qr_ascii, invert=True)
        mfa_qr = qr_ascii.getvalue()
    except Exception as e:
        # Fallback if QR code generation fails
        mfa_qr = f"[QR code generation failed: {str(e)}]"
    
    return jsonify({
        'mfa_required': True,
        'mfa_token': mfa_token,
        'mfa_url': mfa_url,
        'mfa_qr': mfa_qr,
        'timeout_minutes': MFA_CHALLENGE_TIMEOUT_MINUTES
    })


@mfa_bp.route('/status/<token>', methods=['GET'])
@require_gate_auth
def check_mfa_status(token):
    """Check MFA challenge verification status (Gate polling)
    
    Response:
        {
            "verified": bool,
            "error": str (if error),
            "stay_id": int (if verified)
        }
    """
    db = g.db_session
    
    challenge = db.query(MFAChallenge).filter(MFAChallenge.token == token).first()
    
    if not challenge:
        return jsonify({
            'verified': False,
            'error': 'invalid_token',
            'message': 'MFA token not found'
        }), 404
    
    # Check expiry
    if challenge.expires_at < datetime.utcnow():
        return jsonify({
            'verified': False,
            'error': 'expired',
            'message': 'MFA challenge expired'
        }), 410
    
    # Check verification status
    if challenge.verified:
        return jsonify({
            'verified': True,
            'user_id': challenge.user_id,
            'verified_at': challenge.verified_at.isoformat() if challenge.verified_at else None,
            'saml_email': challenge.saml_email
        })
    else:
        # Still waiting for user to complete SAML auth
        return jsonify({
            'verified': False,
            'message': 'Waiting for user authentication'
        })


@mfa_bp.route('/challenge/<token>', methods=['DELETE'])
@require_gate_auth
def cancel_mfa_challenge(token):
    """Cancel pending MFA challenge (user disconnected before completing MFA)
    
    Response:
        {
            "success": bool,
            "message": str
        }
    """
    db = g.db_session
    
    challenge = db.query(MFAChallenge).filter(MFAChallenge.token == token).first()
    
    if not challenge:
        return jsonify({
            'success': False,
            'message': 'Challenge not found'
        }), 404
    
    if challenge.verified:
        return jsonify({
            'success': False,
            'message': 'Challenge already verified, cannot cancel'
        }), 400
    
    # Delete the challenge
    db.delete(challenge)
    db.commit()
    
    logger.info(f"MFA challenge cancelled: {token[:20]}... (user disconnected)")
    
    return jsonify({
        'success': True,
        'message': 'Challenge cancelled'
    })
