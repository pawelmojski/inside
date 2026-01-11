"""Tower API - Session recording streaming endpoints.

Gates stream session recordings in real-time to Tower.
Tower stores recordings persistently.
"""

import os
import base64
from datetime import datetime
from flask import Blueprint, request, jsonify
from src.api.auth import require_gate_auth, get_current_gate, get_db_session
from src.core.database import Session

recordings_bp = Blueprint('recordings', __name__, url_prefix='/api/v1/recordings')

# Base directory for recordings
RECORDINGS_DIR = '/opt/jumphost/logs/recordings'


@recordings_bp.route('/start', methods=['POST'])
@require_gate_auth
def start_recording():
    """Gate notifies Tower that recording has started.
    
    Request JSON:
        {
            "session_id": "uuid-string",
            "person_username": "p.mojski",
            "server_name": "Test-SSH-Server",
            "server_ip": "10.0.160.4"
        }
    
    Response:
        201 Created: {
            "session_id": "uuid-string",
            "recording_path": "/opt/jumphost/logs/recordings/20260107/p.mojski_Test-SSH-Server_20260107_105500_abc123.rec",
            "message": "Recording started"
        }
    """
    gate = get_current_gate()
    db = get_db_session()
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'missing_body'}), 400
    
    session_id = data.get('session_id')
    person_username = data.get('person_username')
    server_name = data.get('server_name')
    server_ip = data.get('server_ip')
    
    if not all([session_id, person_username, server_name]):
        return jsonify({
            'error': 'missing_parameters',
            'message': 'Required: session_id, person_username, server_name'
        }), 400
    
    # Generate recording path
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    date_dir = datetime.now().strftime("%Y%m%d")
    
    # Create directory structure
    recording_dir = os.path.join(RECORDINGS_DIR, date_dir)
    os.makedirs(recording_dir, exist_ok=True)
    
    # Filename: username_server_timestamp_sessionid.rec
    session_short = session_id.split('-')[0]  # First part of UUID
    filename = f"{person_username}_{server_name}_{timestamp}_{session_short}.rec"
    recording_path = os.path.join(recording_dir, filename)
    
    # Create empty file
    with open(recording_path, 'wb') as f:
        # Write header
        header = f"Session Recording\nUser: {person_username}\nServer: {server_name} ({server_ip})\nStarted: {datetime.now().isoformat()}\n\n"
        f.write(header.encode('utf-8'))
    
    return jsonify({
        'session_id': session_id,
        'recording_path': recording_path,
        'message': 'Recording started'
    }), 201


@recordings_bp.route('/chunk', methods=['POST'])
@require_gate_auth
def upload_chunk():
    """Gate uploads a chunk of recording data.
    
    Request JSON:
        {
            "session_id": "uuid-string",
            "recording_path": "/path/from/start/response",
            "chunk_data": "base64-encoded-data",
            "chunk_index": 0,
            "timestamp": "2026-01-07T10:00:00"
        }
    
    Response:
        200 OK: {
            "session_id": "uuid-string",
            "chunk_index": 0,
            "bytes_written": 1024,
            "message": "Chunk received"
        }
        
        404 Not Found: Recording file not found
    """
    gate = get_current_gate()
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'missing_body'}), 400
    
    session_id = data.get('session_id')
    recording_path = data.get('recording_path')
    chunk_data_b64 = data.get('chunk_data')
    chunk_index = data.get('chunk_index', 0)
    
    if not all([session_id, recording_path, chunk_data_b64]):
        return jsonify({
            'error': 'missing_parameters',
            'message': 'Required: session_id, recording_path, chunk_data'
        }), 400
    
    # Decode base64 data
    try:
        chunk_data = base64.b64decode(chunk_data_b64)
    except Exception as e:
        return jsonify({
            'error': 'invalid_base64',
            'message': f'Failed to decode base64: {e}'
        }), 400
    
    # Validate recording path (security: must be under RECORDINGS_DIR)
    if not recording_path.startswith(RECORDINGS_DIR):
        return jsonify({
            'error': 'invalid_path',
            'message': 'Recording path must be under recordings directory'
        }), 400
    
    if not os.path.exists(recording_path):
        return jsonify({
            'error': 'recording_not_found',
            'message': f'Recording file not found: {recording_path}'
        }), 404
    
    # Append chunk to file
    try:
        with open(recording_path, 'ab') as f:
            f.write(chunk_data)
        
        bytes_written = len(chunk_data)
        
        return jsonify({
            'session_id': session_id,
            'chunk_index': chunk_index,
            'bytes_written': bytes_written,
            'message': 'Chunk received'
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'write_failed',
            'message': f'Failed to write chunk: {e}'
        }), 500


@recordings_bp.route('/finalize', methods=['POST'])
@require_gate_auth
def finalize_recording():
    """Gate notifies that recording is complete.
    
    Request JSON:
        {
            "session_id": "uuid-string",
            "recording_path": "/path/to/recording.rec",
            "total_bytes": 12345,
            "duration_seconds": 600
        }
    
    Response:
        200 OK: {
            "session_id": "uuid-string",
            "recording_path": "/path/to/recording.rec",
            "file_size": 12345,
            "message": "Recording finalized"
        }
    """
    gate = get_current_gate()
    db = get_db_session()
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'missing_body'}), 400
    
    session_id = data.get('session_id')
    recording_path = data.get('recording_path')
    total_bytes = data.get('total_bytes')
    
    if not all([session_id, recording_path]):
        return jsonify({
            'error': 'missing_parameters',
            'message': 'Required: session_id, recording_path'
        }), 400
    
    # Verify file exists and get actual size
    if not os.path.exists(recording_path):
        return jsonify({
            'error': 'recording_not_found',
            'message': f'Recording file not found: {recording_path}'
        }), 404
    
    actual_size = os.path.getsize(recording_path)
    
    # Update session in database
    try:
        db_session = db.query(Session).filter(Session.session_id == session_id).first()
        if db_session:
            db_session.recording_path = recording_path
            db_session.recording_size = actual_size
            db.commit()
    except Exception as e:
        db.rollback()
        # Non-critical error - recording is saved
        pass
    
    return jsonify({
        'session_id': session_id,
        'recording_path': recording_path,
        'file_size': actual_size,
        'reported_size': total_bytes,
        'message': 'Recording finalized'
    }), 200
