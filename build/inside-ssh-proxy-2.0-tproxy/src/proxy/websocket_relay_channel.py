"""
WebSocket Relay Channel - Relays session output from Gate to Tower

Implements Paramiko channel interface to integrate with SessionMultiplexer.
Acts as a watcher that sends output to Tower via WebSocket.
"""

import logging
import socketio
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)


class WebSocketRelayChannel:
    """Paramiko channel interface that relays session output to Tower via WebSocket
    
    This channel is added as a watcher to SessionMultiplexer. When multiplexer
    broadcasts output, this channel relays it to Tower via WebSocket connection.
    Tower then broadcasts to browser clients.
    """
    
    def __init__(self, session_id: str, tower_url: str, gate_api_key: str, gate_name: str, 
                 owner_username: str, server_name: str):
        """Initialize relay channel
        
        Args:
            session_id: Session ID to relay
            tower_url: Tower WebSocket URL (e.g., https://tower:5000)
            gate_api_key: API key for gate authentication
            gate_name: Name of this gate
            owner_username: Session owner username
            server_name: Target server name
        """
        self.session_id = session_id
        self.tower_url = tower_url
        self.gate_api_key = gate_api_key
        self.gate_name = gate_name
        self.owner_username = owner_username
        self.server_name = server_name
        
        self.closed = False
        self._lock = threading.Lock()
        
        # Create Socket.IO client (not server!)
        self.sio = socketio.Client(
            reconnection=True,
            reconnection_attempts=10,
            reconnection_delay=1,
            reconnection_delay_max=5,
            logger=False,
            engineio_logger=False
        )
        
        # Register event handlers
        self.sio.on('connect', self._on_connect)
        self.sio.on('disconnect', self._on_disconnect)
        self.sio.on('relay_ack', self._on_relay_ack)
        
        # Connect to Tower
        try:
            logger.info(f"[Relay:{session_id}] Connecting to Tower at {tower_url}")
            self.sio.connect(
                tower_url,
                auth={'gate_api_key': gate_api_key, 'gate_name': gate_name},
                transports=['websocket', 'polling'],
                wait_timeout=10
            )
            logger.info(f"[Relay:{session_id}] Connected to Tower successfully")
        except Exception as e:
            logger.error(f"[Relay:{session_id}] Failed to connect to Tower: {e}")
            raise
    
    def _on_connect(self):
        """Called when WebSocket connects to Tower"""
        logger.info(f"[Relay:{self.session_id}] WebSocket connected to Tower")
        
        # Send registration message
        self.sio.emit('gate_relay_register', {
            'session_id': self.session_id,
            'gate_name': self.gate_name,
            'owner_username': self.owner_username,
            'server_name': self.server_name
        })
    
    def _on_disconnect(self):
        """Called when WebSocket disconnects"""
        logger.warning(f"[Relay:{self.session_id}] WebSocket disconnected from Tower")
    
    def _on_relay_ack(self, data):
        """Called when Tower acknowledges relay registration"""
        logger.info(f"[Relay:{self.session_id}] Tower acknowledged registration: {data}")
    
    # Paramiko channel interface methods
    
    def send(self, data: bytes) -> int:
        """Send data to Tower (called by SessionMultiplexer.broadcast_output)
        
        Args:
            data: Output bytes to relay
            
        Returns:
            Number of bytes sent
        """
        if self.closed:
            return 0
        
        try:
            # Convert bytes to list for JSON serialization
            data_array = list(data)
            
            # Emit to Tower
            self.sio.emit('gate_session_output', {
                'session_id': self.session_id,
                'gate_name': self.gate_name,
                'output': data_array
            })
            
            return len(data)
        except Exception as e:
            logger.error(f"[Relay:{self.session_id}] Failed to relay output: {e}")
            return 0
    
    def recv(self, size: int) -> bytes:
        """Receive data (not used for watch-only relay)"""
        # Relay channels don't receive input (watch mode only)
        return b''
    
    def recv_ready(self) -> bool:
        """Check if data available (always False for watch-only)"""
        return False
    
    def send_ready(self) -> bool:
        """Check if ready to send"""
        return not self.closed and self.sio.connected
    
    def close(self):
        """Close the relay channel"""
        with self._lock:
            if self.closed:
                return
            
            self.closed = True
            logger.info(f"[Relay:{self.session_id}] Closing relay channel")
            
            try:
                # Send unregister message
                if self.sio.connected:
                    self.sio.emit('gate_relay_unregister', {
                        'session_id': self.session_id,
                        'gate_name': self.gate_name
                    })
                    
                    # Give it a moment to send
                    time.sleep(0.1)
                
                # Disconnect
                self.sio.disconnect()
            except Exception as e:
                logger.error(f"[Relay:{self.session_id}] Error during close: {e}")
    
    def fileno(self) -> int:
        """Return file descriptor (not applicable for WebSocket)"""
        return -1
    
    def __del__(self):
        """Cleanup on garbage collection"""
        if not self.closed:
            self.close()
