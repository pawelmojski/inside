"""
WebSocket Events Handler for Live Session Viewing
Handles real-time terminal streaming via xterm.js
"""
import logging
import sys
import os
from flask import request
from flask_login import current_user
from flask_socketio import emit, join_room, leave_room, disconnect

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.core.database import SessionLocal, Session as DBSession
from src.proxy.session_multiplexer import SessionMultiplexerRegistry
from src.web.websocket_adapter import WebSocketChannelAdapter
from src.web.socketio_instance import socketio

logger = logging.getLogger(__name__)

# Get multiplexer registry (singleton)
multiplexer_registry = SessionMultiplexerRegistry()

# Track active WebSocket channels
active_channels = {}  # request.sid -> WebSocketChannelAdapter


def check_session_access(session: DBSession, db) -> bool:
    """Check if current user has permission to view this session
    
    Args:
        session: Database session object
        db: Database connection
        
    Returns:
        True if user has access, False otherwise
    """
    if not current_user or not current_user.is_authenticated:
        return False
    
    # Allow if user is admin
    if current_user.is_admin:
        return True
    
    # Allow if user is the session owner
    if session.username == current_user.username:
        return True
    
    # Allow if user has admin console permissions (for watch/join)
    # TODO: Check AccessPolicy for admin_console permissions
    
    return False


@socketio.on('watch_session')
def handle_watch_session(data):
    """Handle WebSocket request to watch a live session
    
    Client sends:
    {
        'session_id': 'abc123',
        'mode': 'watch'  # 'watch' (read-only) or 'join' (read-write, future)
    }
    
    Server responds with:
    - 'session_history' event with buffered output
    - 'session_output' events with real-time output
    - 'session_ended' event when session terminates
    """
    if not current_user or not current_user.is_authenticated:
        emit('error', {'message': 'Authentication required'})
        disconnect()
        return
    
    session_id = data.get('session_id')
    mode = data.get('mode', 'watch')  # 'watch' or 'join' (future)
    
    if not session_id:
        emit('error', {'message': 'session_id required'})
        return
    
    # Validate mode
    if mode not in ['watch', 'join']:
        emit('error', {'message': 'Invalid mode. Use "watch" or "join"'})
        return
    
    # Check if join mode is requested (not implemented yet)
    if mode == 'join':
        emit('error', {'message': 'Join mode not yet implemented. Use mode="watch" for read-only viewing.'})
        return
    
    # Get session from database
    db = SessionLocal()
    try:
        session = db.query(DBSession).filter(DBSession.session_id == session_id).first()
        
        if not session:
            emit('error', {'message': 'Session not found'})
            return
        
        # Check access permission
        if not check_session_access(session, db):
            emit('error', {'message': 'Access denied'})
            logger.warning(f"User {current_user.username} denied access to session {session_id}")
            return
        
        # Check if session is active
        if not session.is_active:
            emit('error', {'message': 'Session is not active', 'is_active': False})
            return
        
        # Check if session has multiplexer (v2.0+ feature)
        multiplexer = multiplexer_registry.get_session(session_id)
        
        if not multiplexer:
            # Fallback: session doesn't have multiplexer (legacy sessions)
            # In this case, we can't provide real-time streaming
            # Client should fall back to JSON polling
            emit('error', {
                'message': 'Session does not support live streaming (legacy session)',
                'fallback': 'json_polling'
            })
            logger.info(f"Session {session_id} has no multiplexer - fallback to JSON polling")
            return
        
        # Create WebSocket channel adapter
        watcher_id = f"web_{request.sid}"
        room = request.sid  # SocketIO room = client's session ID
        
        channel = WebSocketChannelAdapter(
            socketio=socketio,
            room=room,
            session_id=session_id,
            username=current_user.username
        )
        
        # Register channel globally
        active_channels[request.sid] = channel
        
        # Add watcher to multiplexer
        # This will automatically:
        # 1. Send session history (50KB buffer)
        # 2. Send announcements ("*** alice is now watching this session ***")
        # 3. Start broadcasting real-time output
        success = multiplexer.add_watcher(watcher_id, channel, current_user.username, mode=mode)
        
        if not success:
            emit('error', {'message': 'Failed to attach to session'})
            del active_channels[request.sid]
            return
        
        # Join SocketIO room for this client
        join_room(room)
        
        # Send success confirmation
        emit('watch_started', {
            'session_id': session_id,
            'mode': mode,
            'owner': session.username,
            'server': session.server_name,
            'message': f'Watching session {session_id} (owner: {session.username})'
        })
        
        logger.info(f"User {current_user.username} started watching session {session_id} (mode: {mode})")
    
    finally:
        db.close()


@socketio.on('send_input')
def handle_send_input(data):
    """Handle input from web client (for join mode, future)
    
    Client sends:
    {
        'data': [72, 101, 108, 108, 111]  # "Hello" as byte array
    }
    """
    # This will be used for join mode implementation
    # For now, we reject all input (watch-only)
    
    if request.sid not in active_channels:
        emit('error', {'message': 'Not watching any session'})
        return
    
    channel = active_channels[request.sid]
    
    # TODO: Implement join mode
    # channel.queue_input(bytes(data['data']))
    
    emit('error', {'message': 'Input not allowed in watch mode. Join mode coming in v2.1!'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnect - cleanup watcher"""
    if request.sid in active_channels:
        channel = active_channels[request.sid]
        session_id = channel.session_id
        username = channel.username
        
        # Remove from multiplexer
        multiplexer = multiplexer_registry.get_session(session_id)
        if multiplexer:
            watcher_id = f"web_{request.sid}"
            multiplexer.remove_watcher(watcher_id)
            logger.info(f"User {username} stopped watching session {session_id}")
        
        # Close channel and cleanup
        channel.close()
        del active_channels[request.sid]
        leave_room(request.sid)


@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    if not current_user or not current_user.is_authenticated:
        logger.warning(f"Unauthenticated WebSocket connection attempt from {request.remote_addr}")
        disconnect()
        return
    
    logger.info(f"WebSocket connected: user={current_user.username}, sid={request.sid}")
    emit('connected', {'message': 'WebSocket connected', 'user': current_user.username})


# Export socketio instance for use in app.py
__all__ = ['socketio']
