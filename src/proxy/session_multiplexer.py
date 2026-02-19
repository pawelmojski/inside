"""
Session Multiplexer - Allows multiple clients to share a single SSH session
Enables admin console join/watch functionality (Teleport-like session sharing)
"""
import logging
import threading
import time
from collections import deque
from typing import Dict, List, Optional, Set
from datetime import datetime

logger = logging.getLogger(__name__)


class SessionMultiplexer:
    """Multiplexes a single SSH session to multiple watchers/participants
    
    Architecture:
    - One original client channel (owner)
    - Zero or more admin watcher channels (read-only)
    - Zero or more admin participant channels (read-write)
    - Ring buffer for session history (last N bytes)
    - Real-time broadcasting of all I/O
    """
    
    def __init__(self, session_id: str, owner_username: str, server_name: str, buffer_size: int = 50000):
        """Initialize multiplexer for a session
        
        Args:
            session_id: Unique session identifier
            owner_username: Original user who started the session
            server_name: Target server name
            buffer_size: Size of history buffer in bytes (default 50KB)
        """
        self.session_id = session_id
        self.owner_username = owner_username
        self.server_name = server_name
        self.buffer_size = buffer_size
        
        # Output buffer (ring buffer) - stores recent output for new watchers
        self.output_buffer = deque(maxlen=buffer_size)
        
        # Input queue for participant commands (join mode)
        # Store tuples: (watcher_id, data)
        self.input_queue = deque()
        
        # Connected watchers/participants
        self.watchers: Dict[str, dict] = {}  # watcher_id -> {channel, username, joined_at, mode}
        self.lock = threading.RLock()
        
        # Statistics
        self.created_at = datetime.utcnow()
        self.bytes_proxied = 0
        self.active = True
        
        logger.info(f"SessionMultiplexer created for session {session_id} (owner: {owner_username}, server: {server_name})")
    
    def add_watcher(self, watcher_id: str, channel, username: str, mode: str = 'watch') -> bool:
        """Add a new watcher/participant to this session
        
        Args:
            watcher_id: Unique identifier for this watcher
            channel: Paramiko channel for this watcher
            username: Username of admin watching
            mode: 'watch' (read-only) or 'join' (read-write)
            
        Returns:
            True if added successfully, False otherwise
        """
        if not self.active:
            logger.warning(f"Cannot add watcher {watcher_id} - session {self.session_id} is no longer active")
            return False
        
        with self.lock:
            if watcher_id in self.watchers:
                logger.warning(f"Watcher {watcher_id} already exists in session {self.session_id}")
                return False
            
            self.watchers[watcher_id] = {
                'channel': channel,
                'username': username,
                'joined_at': datetime.utcnow(),
                'mode': mode,
                'bytes_sent': 0
            }
            
            logger.info(f"Added {mode} watcher {watcher_id} ({username}) to session {self.session_id} ({len(self.watchers)} total)")
            
            # Send session history to new watcher
            self._send_history_to_watcher(watcher_id)
            
            # Announce join (if not in stealth mode)
            self._announce_join(username, mode)
            
            return True
    
    def remove_watcher(self, watcher_id: str):
        """Remove a watcher/participant from this session"""
        with self.lock:
            if watcher_id in self.watchers:
                watcher = self.watchers[watcher_id]
                username = watcher['username']
                mode = watcher['mode']
                
                del self.watchers[watcher_id]
                logger.info(f"Removed {mode} watcher {watcher_id} ({username}) from session {self.session_id} ({len(self.watchers)} remaining)")
                
                # Announce leave
                self._announce_leave(username, mode)
    
    def broadcast_output(self, data: bytes, from_watcher_id: Optional[str] = None):
        """Broadcast output from backend to all watchers (and buffer it)
        
        Args:
            data: Output data from backend server
            from_watcher_id: Optional - if this output came from a participant's input
        """
        if not data:
            return
        
        with self.lock:
            # Add to buffer
            self.output_buffer.append(data)
            self.bytes_proxied += len(data)
            
            # Send to all watchers
            dead_watchers = []
            for watcher_id, watcher_info in self.watchers.items():
                try:
                    channel = watcher_info['channel']
                    if not channel.closed:
                        channel.send(data)
                        watcher_info['bytes_sent'] += len(data)
                    else:
                        dead_watchers.append(watcher_id)
                except Exception as e:
                    logger.error(f"Error sending to watcher {watcher_id}: {e}")
                    dead_watchers.append(watcher_id)
            
            # Clean up dead watchers
            for watcher_id in dead_watchers:
                self.remove_watcher(watcher_id)
    
    def handle_participant_input(self, watcher_id: str, data: bytes) -> Optional[bytes]:
        """Handle input from a participant (join mode)
        
        Args:
            watcher_id: ID of the participant sending input
            data: Input data to forward to backend
            
        Returns:
            Data to forward to backend, or None if participant not allowed
        """
        with self.lock:
            if watcher_id not in self.watchers:
                logger.warning(f"Input from unknown watcher {watcher_id}")
                return None
            
            watcher = self.watchers[watcher_id]
            if watcher['mode'] != 'join':
                logger.warning(f"Input from read-only watcher {watcher_id} - rejecting")
                return None
            
            # Add to input queue for forward_channel to pick up
            self.input_queue.append((watcher_id, data))
            return data
    
    def get_pending_input(self) -> Optional[bytes]:
        """Get pending input from participants (for forward_channel)
        
        Returns:
            Input data to forward to backend, or None if queue empty
        """
        with self.lock:
            if self.input_queue:
                watcher_id, data = self.input_queue.popleft()
                logger.debug(f"Forwarding input from {watcher_id}: {len(data)} bytes")
                return data
            return None
    
    def _send_history_to_watcher(self, watcher_id: str):
        """Send buffered output history to a newly joined watcher"""
        with self.lock:
            if watcher_id not in self.watchers:
                return
            
            watcher = self.watchers[watcher_id]
            channel = watcher['channel']
            
            # Clear screen and send banner
            try:
                banner = (
                    f"\r\n{'='*60}\r\n"
                    f"Joined session: {self.session_id}\r\n"
                    f"Owner: {self.owner_username}\r\n"
                    f"Server: {self.server_name}\r\n"
                    f"Mode: {watcher['mode']}\r\n"
                    f"{'='*60}\r\n\r\n"
                    "--- Session History ---\r\n"
                )
                channel.send(banner.encode('utf-8'))
                
                # Send buffered output
                for chunk in self.output_buffer:
                    if not channel.closed:
                        channel.send(chunk)
                        watcher['bytes_sent'] += len(chunk)
                
                footer = b"\r\n--- End History (Live Stream) ---\r\n\r\n"
                channel.send(footer)
                
            except Exception as e:
                logger.error(f"Error sending history to watcher {watcher_id}: {e}")
    
    def _announce_join(self, username: str, mode: str):
        """Announce that someone joined the session"""
        mode_text = "watching" if mode == 'watch' else "joined (read-write)"
        announcement = f"\r\n*** {username} is now {mode_text} this session ***\r\n"
        
        # Broadcast to all watchers
        with self.lock:
            for watcher_id, watcher_info in self.watchers.items():
                try:
                    channel = watcher_info['channel']
                    if not channel.closed:
                        channel.send(announcement.encode('utf-8'))
                except Exception as e:
                    logger.error(f"Error announcing join to watcher {watcher_id}: {e}")
    
    def _announce_leave(self, username: str, mode: str):
        """Announce that someone left the session"""
        mode_text = "stopped watching" if mode == 'watch' else "left"
        announcement = f"\r\n*** {username} {mode_text} ***\r\n"
        
        # Broadcast to all watchers
        with self.lock:
            for watcher_id, watcher_info in self.watchers.items():
                try:
                    channel = watcher_info['channel']
                    if not channel.closed:
                        channel.send(announcement.encode('utf-8'))
                except Exception as e:
                    logger.error(f"Error announcing leave to watcher {watcher_id}: {e}")
    
    def deactivate(self):
        """Mark session as inactive - no new watchers allowed"""
        with self.lock:
            self.active = False
            logger.info(f"SessionMultiplexer deactivated for session {self.session_id}")
    
    def get_stats(self) -> dict:
        """Get current statistics about this multiplexed session"""
        with self.lock:
            return {
                'session_id': self.session_id,
                'owner_username': self.owner_username,
                'server_name': self.server_name,
                'active': self.active,
                'watcher_count': len(self.watchers),
                'watchers': [
                    {
                        'username': w['username'],
                        'mode': w['mode'],
                        'joined_at': w['joined_at'].isoformat(),
                        'bytes_sent': w['bytes_sent']
                    }
                    for w in self.watchers.values()
                ],
                'bytes_proxied': self.bytes_proxied,
                'buffer_size': len(self.output_buffer),
                'created_at': self.created_at.isoformat()
            }


class SessionMultiplexerRegistry:
    """Global registry of all active multiplexed sessions
    
    This is a singleton that tracks all sessions that can be joined/watched.
    Lives in the gate process memory.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.sessions: Dict[str, SessionMultiplexer] = {}
        self.lock = threading.RLock()
        self._initialized = True
        logger.info("SessionMultiplexerRegistry initialized")
    
    def register_session(self, session_id: str, owner_username: str, server_name: str) -> SessionMultiplexer:
        """Register a new session for multiplexing
        
        Returns:
            SessionMultiplexer instance for this session
        """
        with self.lock:
            if session_id in self.sessions:
                logger.warning(f"Session {session_id} already registered - returning existing multiplexer")
                return self.sessions[session_id]
            
            multiplexer = SessionMultiplexer(session_id, owner_username, server_name)
            self.sessions[session_id] = multiplexer
            
            logger.info(f"Registered session {session_id} for multiplexing ({len(self.sessions)} total)")
            return multiplexer
    
    def get_session(self, session_id: str) -> Optional[SessionMultiplexer]:
        """Get multiplexer for a session ID
        
        Returns:
            SessionMultiplexer if found, None otherwise
        """
        with self.lock:
            return self.sessions.get(session_id)
    
    def unregister_session(self, session_id: str):
        """Remove a session from registry (when session ends)"""
        with self.lock:
            if session_id in self.sessions:
                multiplexer = self.sessions[session_id]
                multiplexer.deactivate()
                del self.sessions[session_id]
                logger.info(f"Unregistered session {session_id} ({len(self.sessions)} remaining)")
    
    def list_active_sessions(self) -> List[dict]:
        """List all active sessions that can be joined/watched
        
        Returns:
            List of session statistics
        """
        with self.lock:
            return [
                multiplexer.get_stats()
                for multiplexer in self.sessions.values()
                if multiplexer.active
            ]
    
    def cleanup_inactive(self):
        """Remove inactive sessions from registry"""
        with self.lock:
            inactive = [sid for sid, mux in self.sessions.items() if not mux.active]
            for sid in inactive:
                self.unregister_session(sid)
            
            if inactive:
                logger.info(f"Cleaned up {len(inactive)} inactive sessions")
