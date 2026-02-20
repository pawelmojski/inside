"""
Proxy Multiplexer - Represents a session running on remote gate

Receives output from gate via WebSocket relay and broadcasts to browser watchers.
Similar to SessionMultiplexer but for proxied sessions (not local).
"""

import logging
import threading
from collections import deque
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class ProxySessionMultiplexer:
    """Represents a session running on remote gate
    
    Receives output from gate via WebSocket relay.
    Allows browser clients to watch as if session was local.
    """
    
    def __init__(self, session_id: str, gate_name: str, owner_username: str, server_name: str):
        """Initialize proxy multiplexer
        
        Args:
            session_id: Session ID
            gate_name: Gate where session is running
            owner_username: Session owner
            server_name: Target server name
        """
        self.session_id = session_id
        self.gate_name = gate_name
        self.owner_username = owner_username
        self.server_name = server_name
        
        # Ring buffer for session history (50KB)
        self.ring_buffer = deque(maxlen=512)  # ~50KB with 100-byte chunks
        self.total_bytes_received = 0
        
        # Browser watchers: {sid: WebSocketChannelAdapter}
        self.web_watchers: Dict[str, any] = {}
        self._lock = threading.Lock()
        
        self.is_proxy = True  # Flag: this is relay, not direct
        
        logger.info(f"ProxyMultiplexer created for session {session_id} (gate: {gate_name}, owner: {owner_username})")
    
    def receive_output_from_gate(self, data: bytes):
        """Called when gate sends output via relay
        
        Args:
            data: Output bytes from gate
        """
        with self._lock:
            # Add to ring buffer (history)
            self.ring_buffer.append(data)
            self.total_bytes_received += len(data)
            
            # Broadcast to all web watchers
            disconnected = []
            for sid, watcher in self.web_watchers.items():
                try:
                    watcher.send(data)
                except Exception as e:
                    logger.error(f"[Proxy:{self.session_id}] Error sending to watcher {sid}: {e}")
                    disconnected.append(sid)
            
            # Remove disconnected watchers
            for sid in disconnected:
                self.web_watchers.pop(sid, None)
    
    def add_watcher(self, watcher_id: str, channel: any, username: str, mode: str = "watch") -> bool:
        """Add browser watcher
        
        Args:
            watcher_id: Watcher ID (usually Socket.IO sid)
            channel: WebSocketChannelAdapter
            username: Username of watcher
            mode: 'watch' (read-only) or 'join' (read-write, future)
            
        Returns:
            True if added successfully
        """
        with self._lock:
            if watcher_id in self.web_watchers:
                logger.warning(f"[Proxy:{self.session_id}] Watcher {watcher_id} already exists")
                return False
            
            self.web_watchers[watcher_id] = channel
            
            logger.info(
                f"[Proxy:{self.session_id}] Watcher added: {username} (mode: {mode}, "
                f"total watchers: {len(self.web_watchers)})"
            )
            
            # Send session history to new watcher
            try:
                history_bytes = b''.join(self.ring_buffer)
                if history_bytes:
                    channel.send(history_bytes)
                    logger.info(
                        f"[Proxy:{self.session_id}] Sent {len(history_bytes)} bytes history to {username}"
                    )
            except Exception as e:
                logger.error(f"[Proxy:{self.session_id}] Failed to send history to {username}: {e}")
            
            return True
    
    def remove_watcher(self, watcher_id: str):
        """Remove browser watcher
        
        Args:
            watcher_id: Watcher ID to remove
        """
        with self._lock:
            if watcher_id in self.web_watchers:
                del self.web_watchers[watcher_id]
                logger.info(
                    f"[Proxy:{self.session_id}] Watcher removed: {watcher_id} "
                    f"(remaining: {len(self.web_watchers)})"
                )
    
    def get_watcher_count(self) -> int:
        """Get number of active watchers"""
        return len(self.web_watchers)
    
    def has_watchers(self) -> bool:
        """Check if any watchers are active"""
        return len(self.web_watchers) > 0


class ProxyMultiplexerRegistry:
    """Registry of proxy multiplexers for sessions on remote gates"""
    
    def __init__(self):
        """Initialize registry"""
        self._sessions: Dict[str, ProxySessionMultiplexer] = {}
        self._lock = threading.Lock()
        logger.info("ProxyMultiplexerRegistry initialized")
    
    def register_session(self, session_id: str, gate_name: str, owner_username: str, 
                        server_name: str) -> ProxySessionMultiplexer:
        """Register a proxied session
        
        Args:
            session_id: Session ID
            gate_name: Gate where session is running
            owner_username: Session owner
            server_name: Target server name
            
        Returns:
            ProxySessionMultiplexer instance
        """
        with self._lock:
            if session_id in self._sessions:
                logger.warning(f"Proxy session {session_id} already registered")
                return self._sessions[session_id]
            
            multiplexer = ProxySessionMultiplexer(
                session_id=session_id,
                gate_name=gate_name,
                owner_username=owner_username,
                server_name=server_name
            )
            
            self._sessions[session_id] = multiplexer
            logger.info(f"Registered proxy session {session_id} (total: {len(self._sessions)})")
            
            return multiplexer
    
    def unregister_session(self, session_id: str):
        """Unregister a proxied session
        
        Args:
            session_id: Session ID to remove
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                logger.info(f"Unregistered proxy session {session_id} (remaining: {len(self._sessions)})")
    
    def get_session(self, session_id: str) -> Optional[ProxySessionMultiplexer]:
        """Get proxy multiplexer for a session
        
        Args:
            session_id: Session ID
            
        Returns:
            ProxySessionMultiplexer or None
        """
        return self._sessions.get(session_id)
    
    def get_session_count(self) -> int:
        """Get number of registered proxy sessions"""
        return len(self._sessions)


# Global singleton
_proxy_registry = None

def get_proxy_registry() -> ProxyMultiplexerRegistry:
    """Get global proxy multiplexer registry (singleton)"""
    global _proxy_registry
    if _proxy_registry is None:
        _proxy_registry = ProxyMultiplexerRegistry()
    return _proxy_registry
