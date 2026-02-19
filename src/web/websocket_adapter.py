"""
WebSocket Channel Adapter - Implements Paramiko channel interface for WebSocket
Allows SessionMultiplexer to treat WebSocket clients as Paramiko channels
"""
import logging
import threading
from typing import Optional
from flask_socketio import emit

logger = logging.getLogger(__name__)


class WebSocketChannelAdapter:
    """Adapter that implements Paramiko channel interface for WebSocket clients
    
    This allows SessionMultiplexer (designed for Paramiko channels) to work
    with WebSocket clients from the web GUI.
    
    Implements minimal Paramiko channel interface:
    - send(data) - broadcast output to web client
    - recv(size) - receive input from web client (for join mode)
    - closed - connection status
    """
    
    def __init__(self, socketio, room: str, session_id: str, username: str):
        """Initialize WebSocket channel adapter
        
        Args:
            socketio: Flask-SocketIO instance
            room: SocketIO room ID (unique per web client)
            session_id: Target session ID
            username: Web user username
        """
        self.socketio = socketio
        self.room = room
        self.session_id = session_id
        self.username = username
        self.closed = False
        self.lock = threading.Lock()
        
        # Input buffer for join mode (when web client sends keystrokes)
        self.input_buffer = bytearray()
        self.input_available = threading.Event()
        
        logger.info(f"WebSocketChannelAdapter created: session={session_id}, user={username}, room={room}")
    
    def send(self, data: bytes) -> int:
        """Send data to web client via WebSocket
        
        This is called by SessionMultiplexer.broadcast_output()
        
        Args:
            data: Raw terminal output bytes
            
        Returns:
            Number of bytes sent
        """
        if self.closed:
            return 0
        
        try:
            # Emit binary data to specific room (web client)
            # xterm.js will receive this as Uint8Array
            self.socketio.emit('session_output', 
                              {'data': list(data)},  # Convert bytes to list for JSON
                              room=self.room)
            return len(data)
        except Exception as e:
            logger.error(f"Error sending to WebSocket {self.room}: {e}")
            self.closed = True
            return 0
    
    def recv(self, size: int, timeout: Optional[float] = None) -> bytes:
        """Receive data from web client (for join mode)
        
        This would be called by SessionMultiplexer.handle_participant_input()
        when implementing join mode from web.
        
        Args:
            size: Maximum bytes to receive
            timeout: Optional timeout in seconds
            
        Returns:
            Input data from web client
        """
        with self.lock:
            if not self.input_buffer:
                # Wait for input (with timeout)
                if not self.input_available.wait(timeout):
                    return b''
            
            # Return up to 'size' bytes
            data = bytes(self.input_buffer[:size])
            self.input_buffer = self.input_buffer[size:]
            
            if not self.input_buffer:
                self.input_available.clear()
            
            return data
    
    def queue_input(self, data: bytes):
        """Queue input from web client (called by WebSocket handler)
        
        This is called when web client sends keystrokes via WebSocket.
        Used for join mode (read-write).
        
        Args:
            data: Input data from web client
        """
        with self.lock:
            self.input_buffer.extend(data)
            self.input_available.set()
    
    def close(self):
        """Close the WebSocket channel"""
        if not self.closed:
            self.closed = True
            logger.info(f"WebSocketChannelAdapter closed: session={self.session_id}, user={self.username}")
    
    def __repr__(self):
        return f"<WebSocketChannelAdapter session={self.session_id} user={self.username} closed={self.closed}>"
