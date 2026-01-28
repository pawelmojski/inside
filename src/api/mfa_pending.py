#!/usr/bin/env python3
"""
MFA Pending Challenges API
Endpoint for listing unverified MFA challenges (last 5 minutes)
"""

from flask import Blueprint, jsonify, request, render_template
from datetime import datetime, timedelta
from src.core.database import SessionLocal, MFAChallenge, User, Server, Gate
import logging

logger = logging.getLogger(__name__)

mfa_pending_bp = Blueprint('mfa_pending', __name__)


@mfa_pending_bp.route('/mfa', methods=['GET'])
def mfa_page():
    """Render MFA pending challenges page"""
    return render_template('mfa_pending.html')


@mfa_pending_bp.route('/api/v1/mfa/pending', methods=['GET'])
def get_pending_challenges():
    """Get list of pending (unverified) MFA challenges from last 5 minutes
    
    Returns:
        200 OK: {
            "challenges": [
                {
                    "id": 123,
                    "token": "abc123...",
                    "user_id": 6,
                    "username": "p.mojski",
                    "user_fullname": "Pawel Mojski",
                    "server_id": 8,
                    "server_name": "rancher-2",
                    "server_ip": "10.210.1.190",
                    "gate_id": 3,
                    "gate_name": "tailscale-etop",
                    "source_ip": "100.64.0.20",
                    "destination_ip": "10.210.1.190",
                    "ssh_login": "p.mojski",
                    "created_at": "2026-01-28T10:30:00",
                    "expires_at": "2026-01-28T10:35:00",
                    "mfa_url": "https://inside.ideo.pl/auth/saml/login?token=..."
                }
            ]
        }
    """
    db = SessionLocal()
    
    # Get challenges from last 5 minutes that are not verified
    cutoff_time = datetime.utcnow() - timedelta(minutes=5)
    now = datetime.utcnow()
    
    challenges = db.query(MFAChallenge).filter(
        MFAChallenge.created_at >= cutoff_time,
        MFAChallenge.verified == False,
        MFAChallenge.expires_at > now
    ).order_by(MFAChallenge.created_at.desc()).all()
    
    result = []
    for challenge in challenges:
        # Get user info (may be null in Phase 2)
        user = None
        if challenge.user_id:
            user = db.query(User).get(challenge.user_id)
        
        # Get server info from destination_ip (Phase 2) or grant (Phase 1)
        server = None
        if challenge.destination_ip:
            # Phase 2: Find server by destination IP
            from src.core.access_control_v2 import AccessControlEngineV2
            engine = AccessControlEngineV2()
            backend_info = engine.find_backend_by_proxy_ip(db, challenge.destination_ip, challenge.gate_id)
            if backend_info and backend_info['server']:
                server = backend_info['server']
        elif challenge.grant_id:
            # Phase 1: Get server from grant
            from src.core.database import AccessPolicy
            grant = db.query(AccessPolicy).get(challenge.grant_id)
            if grant and grant.target_server_id:
                server = db.query(Server).get(grant.target_server_id)
        
        # Get gate info
        gate = db.query(Gate).get(challenge.gate_id) if challenge.gate_id else None
        
        # Use expires_at from challenge (already calculated)
        expires_at = challenge.expires_at
        
        # Build MFA URL
        base_url = "https://inside.ideo.pl"
        mfa_url = f"{base_url}/auth/saml/login?token={challenge.token}"
        
        challenge_data = {
            'id': challenge.id,
            'token': challenge.token,
            'user_id': user.id if user else None,
            'username': user.username if user else '(unknown)',
            'user_fullname': user.full_name if user else '(identifying...)',
            'server_id': server.id if server else None,
            'server_name': server.name if server else '(unknown)',
            'server_ip': server.ip_address if server else challenge.destination_ip,
            'gate_id': gate.id if gate else None,
            'gate_name': gate.name if gate else '(unknown)',
            'source_ip': challenge.source_ip,
            'destination_ip': challenge.destination_ip,
            'ssh_login': challenge.ssh_username,
            'created_at': challenge.created_at.isoformat() + 'Z',  # UTC indicator
            'expires_at': expires_at.isoformat() + 'Z',  # UTC indicator
            'mfa_url': mfa_url
        }
        
        result.append(challenge_data)
    
    db.close()
    return jsonify({'challenges': result}), 200
