"""
WebSocket Events Handler for Live Session Viewing
Handles real-time terminal streaming via xterm.js
"""
import logging
import sys
import os
from datetime import datetime
from flask import request
from flask_login import current_user
from flask_socketio import emit, join_room, leave_room, disconnect

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.core.database import SessionLocal, Session as DBSession
from src.proxy.session_multiplexer import SessionMultiplexerRegistry
from src.web.websocket_adapter import WebSocketChannelAdapter
from src.web.proxy_multiplexer import get_proxy_registry
from src.web import relay_tracking

logger = logging.getLogger(__name__)

# Get multiplexer registry (singleton)
multiplexer_registry = SessionMultiplexerRegistry()
proxy_registry = get_proxy_registry()

# SocketIO instance will be injected by register_handlers()
socketio = None

def register_handlers(socketio_instance):
    """Register Socket.IO event handlers
    
    Must be called AFTER socketio.init_app() in app.py
    """
    global socketio
    socketio = socketio_instance
    logger.info("[SOCKETIO] Registering event handlers...")
    
    # Now register all handlers using the initialized socketio instance
    _register_connect_handler()
    _register_watch_session_handler()
    _register_session_input_handler()
    _register_terminal_resize_handler()
    _register_disconnect_handler()
    
    # Register gate relay handlers (for receiving output from gates)
    _register_gate_relay_handlers()
    
    logger.info("[SOCKETIO] Event handlers registered successfully")


def _register_connect_handler():
    """Register connect event handler"""
    @socketio.on('connect')
    def handle_connect(auth=None):
        """Handle WebSocket connection (browser or gate relay)"""
        # Check if this is a gate relay connection (has gate_api_key in auth)
        if auth and isinstance(auth, dict) and 'gate_api_key' in auth:
            gate_name = auth.get('gate_name', 'unknown')
            logger.info(f"[SOCKETIO] Gate relay connected: {gate_name}, sid={request.sid}")
            emit('connected', {'message': 'Gate relay connected', 'gate_name': gate_name})
            return
        
        # Browser connection - requires authentication
        logger.info(f"[SOCKETIO] WebSocket connected: sid={request.sid}, user={current_user if current_user.is_authenticated else 'anonymous'}")
        
        if not current_user or not current_user.is_authenticated:
            logger.warning(f"[SOCKETIO] Unauthenticated WebSocket connection attempt from {request.remote_addr}")
            disconnect()
            return
        
        logger.info(f"[SOCKETIO] Connection authenticated: user={current_user.username}, sid={request.sid}")
        emit('connected', {'message': 'WebSocket connected', 'user': current_user.username})


def _register_watch_session_handler():
    """Register watch_session event handler"""
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
        logger.info(f"[watch_session] Event received, current_user={current_user}, data={data}")
        
        if not current_user or not current_user.is_authenticated:
            logger.warning("[watch_session] User not authenticated")
            emit('error', {'message': 'Authentication required'})
            disconnect()
            return
        
        session_id = data.get('session_id')
        mode = data.get('mode', 'watch')  # 'watch' or 'join' (future)
        
        logger.info(f"[watch_session] session_id={session_id}, mode={mode}, username={current_user.username}")
        
        if not session_id:
            emit('error', {'message': 'session_id required'})
            return
        
        # Validate mode
        if mode not in ['watch', 'join']:
            emit('error', {'message': 'Invalid mode. Use "watch" or "join"'})
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
                # Session not on Tower - check if it's proxied from gate
                proxy_multiplexer = proxy_registry.get_session(session_id)
                
                if proxy_multiplexer:
                    # Session is already being relayed from gate - use proxy multiplexer
                    multiplexer = proxy_multiplexer
                    logger.info(f"Using proxy multiplexer for {session_id} from gate {proxy_multiplexer.gate_name}")
                else:
                    # Session on gate but not yet relayed - register watch request
                    gate_name = session.gate.name if session.gate else None
                    
                    if not gate_name:
                        emit('error', {'message': 'Cannot determine session location'})
                        return
                    
                    # Register watch request (gate will pick it up on next heartbeat ~5s)
                    relay_tracking.register_watch_request(
                        session_id=session_id,
                        gate_name=gate_name,
                        watcher_sid=request.sid,
                        session_obj=session
                    )
                    
                    # Send "waiting for relay" message
                    emit('relay_pending', {
                        'message': f'Requesting relay from {gate_name}... (this may take up to 5 seconds)',
                        'session_id': session_id,
                        'gate_name': gate_name
                    })
                    
                    logger.info(f"Relay request registered for {session_id} on {gate_name} (watcher: {request.sid})")
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


def _register_session_input_handler():
    """Register session_input event handler (for join mode)"""
    @socketio.on('session_input')
    def handle_session_input(data):
        """Handle keyboard input from web client in join mode
        
        Client sends:
        {
            'session_id': 'abc123',
            'data': 'ls\n'  # User keystrokes as string
        }
        """
        if request.sid not in active_channels:
            emit('error', {'message': 'Not watching any session'})
            return
        
        channel = active_channels[request.sid]
        session_id = channel.session_id
        
        # Convert input string to bytes
        input_data = data.get('data', '')
        if isinstance(input_data, str):
            input_bytes = input_data.encode('utf-8')
        else:
            input_bytes = bytes(input_data)
        
        # Queue input in channel adapter
        channel.queue_input(input_bytes)
        
        # Forward to multiplexer
        multiplexer = multiplexer_registry.get_session(session_id)
        if multiplexer:
            # Local session on Tower - forward to local multiplexer
            watcher_id = f"web_{request.sid}"
            multiplexer.handle_participant_input(watcher_id, input_bytes)
            logger.debug(f"Input forwarded to local session {session_id}: {len(input_bytes)} bytes")
        else:
            # Session is on gate (proxy) - send input via WebSocket to gate
            proxy_multiplexer = proxy_registry.get_session(session_id)
            if proxy_multiplexer:
                gate_name = proxy_multiplexer.gate_name
                # Emit to gate relay connection
                socketio.emit('gate_session_input', {
                    'session_id': session_id,
                    'data': list(input_bytes)  # Convert bytes to list for JSON
                }, room=f"gate_{gate_name}")
                logger.debug(f"Input sent to gate {gate_name} for session {session_id}: {len(input_bytes)} bytes")
            else:
                logger.warning(f"Input from {channel.username} for session {session_id} - multiplexer not found")


def _register_terminal_resize_handler():
    """Register terminal_resize event handler"""
    @socketio.on('terminal_resize')
    def handle_terminal_resize(data):
        """Handle terminal resize from web client
        
        Client sends:
        {
            'session_id': 'abc123',
            'rows': 40,
            'cols': 120
        }
        """
        if request.sid not in active_channels:
            return
        
        channel = active_channels[request.sid]
        session_id = data.get('session_id')
        rows = data.get('rows', 24)
        cols = data.get('cols', 80)
        
        logger.info(f"Terminal resize from {channel.username} for {session_id}: {rows}x{cols}")
        
        # For local sessions - resize the Paramiko channel
        # For gate sessions - would need to send resize command to gate (TODO)


def _register_disconnect_handler():
    """Register disconnect event handler"""
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle WebSocket disconnect - cleanup watcher"""
        # Remove from relay tracking (if watching gate session)
        relay_tracking.unregister_watch_request(request.sid)
        
        if request.sid in active_channels:
            channel = active_channels[request.sid]
            session_id = channel.session_id
            username = channel.username
            
            # Remove from multiplexer (local or proxy)
            multiplexer = multiplexer_registry.get_session(session_id)
            if not multiplexer:
                multiplexer = proxy_registry.get_session(session_id)
            
            if multiplexer:
                watcher_id = f"web_{request.sid}"
                multiplexer.remove_watcher(watcher_id)
                logger.info(f"User {username} stopped watching session {session_id}")
            
            # Close channel and cleanup
            channel.close()
            del active_channels[request.sid]
            leave_room(request.sid)


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
    
    # Allow if user is admin or higher (permission_level <= 100)
    if current_user.permission_level <= 100:
        return True
    
    # Allow if user is the session owner
    if session.username == current_user.username:
        return True
    
    # Allow if user has admin console permissions (for watch/join)
    # TODO: Check AccessPolicy for admin_console permissions
    
    return False


def _register_gate_relay_handlers():
    """Register handlers for gate relay (gate → tower stream)"""
    
    @socketio.on('gate_relay_register')
    def handle_gate_relay_register(data):
        """Gate registers a relay for a session
        
        Data: {
            'session_id': 'abc123',
            'gate_name': 'tailscale-etop',
            'owner_username': 'p.mojski',
            'server_name': 'auto-185-186-155-15'
        }
        """
        session_id = data.get('session_id')
        gate_name = data.get('gate_name')
        owner_username = data.get('owner_username')
        server_name = data.get('server_name')
        
        if not all([session_id, gate_name, owner_username, server_name]):
            logger.error(f"[GateRelay] Missing required fields in gate_relay_register")
            emit('error', {'message': 'Missing required fields'})
            return
        
        logger.info(
            f"[GateRelay:{session_id}] Gate {gate_name} registering relay "
            f"(owner: {owner_username}, server: {server_name})"
        )
        
        # Create or get proxy multiplexer
        proxy_multiplexer = proxy_registry.get_session(session_id)
        if not proxy_multiplexer:
            proxy_multiplexer = proxy_registry.register_session(
                session_id=session_id,
                gate_name=gate_name,
                owner_username=owner_username,
                server_name=server_name
            )
            logger.info(f"[GateRelay:{session_id}] Created proxy multiplexer")
        
        # Join gate to room for bidirectional communication
        gate_room = f"gate_{gate_name}"
        join_room(gate_room)
        logger.info(f"[GateRelay:{session_id}] Gate {gate_name} joined room {gate_room}")
        
        # Send acknowledgment
        emit('relay_ack', {
            'session_id': session_id,
            'status': 'registered',
            'watchers_count': proxy_multiplexer.get_watcher_count()
        })
        
        # Notify pending browser watchers that relay is now active
        watchers = relay_tracking.get_watchers_for_session(session_id)
        for watcher_sid in watchers:
            socketio.emit('relay_activated', {
                'session_id': session_id,
                'gate_name': gate_name,
                'message': f'Relay from {gate_name} activated - connecting...'
            }, room=watcher_sid)
            
            # Now add browser watchers to proxy multiplexer
            try:
                channel = WebSocketChannelAdapter(
                    socketio=socketio,
                    room=watcher_sid,
                    session_id=session_id,
                    username=f"[Browser:{watcher_sid[:8]}]"
                )
                
                success = proxy_multiplexer.add_watcher(
                    watcher_id=f"web_{watcher_sid}",
                    channel=channel,
                    username=f"[Browser]",
                    mode="watch"
                )
                
                if success:
                    active_channels[watcher_sid] = channel
                    
                    # Send watch_started to browser
                    socketio.emit('watch_started', {
                        'session_id': session_id,
                        'mode': 'watch',
                        'owner': owner_username,
                        'server': server_name,
                        'gate': gate_name,
                        'message': f'Watching session {session_id} (owner: {owner_username}, via {gate_name})'
                    }, room=watcher_sid)
                    
                    logger.info(f"[GateRelay:{session_id}] Browser watcher {watcher_sid[:8]} connected")
            except Exception as e:
                logger.error(f"[GateRelay:{session_id}] Failed to add browser watcher {watcher_sid[:8]}: {e}")
    
    @socketio.on('gate_session_output')
    def handle_gate_session_output(data):
        """Gate sends session output
        
        Data: {
            'session_id': 'abc123',
            'gate_name': 'tailscale-etop',
            'output': [72, 101, 108, 108, 111]  # bytes as array
        }
        """
        session_id = data.get('session_id')
        output_array = data.get('output', [])
        
        if not session_id or not output_array:
            return
        
        # Get proxy multiplexer
        proxy_multiplexer = proxy_registry.get_session(session_id)
        if not proxy_multiplexer:
            logger.warning(f"[GateRelay:{session_id}] Received output but no proxy multiplexer")
            return
        
        # Convert array back to bytes
        output_bytes = bytes(output_array)
        
        # Broadcast to browser watchers
        proxy_multiplexer.receive_output_from_gate(output_bytes)
    
    @socketio.on('gate_relay_unregister')
    def handle_gate_relay_unregister(data):
        """Gate unregisters a relay
        
        Data: {
            'session_id': 'abc123',
            'gate_name': 'tailscale-etop'
        }
        """
        session_id = data.get('session_id')
        gate_name = data.get('gate_name')
        
        logger.info(f"[GateRelay:{session_id}] Gate {gate_name} unregistering relay")
        
        # Unregister proxy multiplexer
        proxy_registry.unregister_session(session_id)
        
        # Notify browser watchers
        watchers = relay_tracking.get_watchers_for_session(session_id)
        for watcher_sid in watchers:
            socketio.emit('session_ended', {
                'session_id': session_id,
                'reason': 'Relay disconnected'
            }, room=watcher_sid)


# Export for use in app.py
__all__ = ['register_handlers', 'socketio']
