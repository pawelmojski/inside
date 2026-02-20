"""
Lazy Relay Manager - Manages on-demand WebSocket relays to Tower

Creates and destroys relay channels based on Tower's heartbeat responses.
Only active when browsers are watching sessions (zero overhead otherwise).
"""

import logging
from typing import Dict, List, Optional
from src.proxy.websocket_relay_channel import WebSocketRelayChannel
from src.proxy.session_multiplexer import SessionMultiplexerRegistry

logger = logging.getLogger(__name__)


class LazyRelayManager:
    """Manages on-demand WebSocket relays to Tower
    
    Creates relay channels only when Tower requests them (browser watchers exist).
    Destroys relays when Tower no longer needs them (no browser watchers).
    """
    
    def __init__(self, tower_url: str, gate_api_key: str, gate_name: str, 
                 multiplexer_registry: SessionMultiplexerRegistry):
        """Initialize lazy relay manager
        
        Args:
            tower_url: Tower WebSocket URL (e.g., https://tower:5000)
            gate_api_key: API key for gate authentication
            gate_name: Name of this gate
            multiplexer_registry: Registry of active session multiplexers
        """
        self.tower_url = tower_url
        self.gate_api_key = gate_api_key
        self.gate_name = gate_name
        self.multiplexer_registry = multiplexer_registry
        
        # Active relays: {session_id: WebSocketRelayChannel}
        self.active_relays: Dict[str, WebSocketRelayChannel] = {}
        
        logger.info(f"LazyRelayManager initialized for gate {gate_name} (Tower: {tower_url})")
    
    def process_relay_commands(self, relay_sessions: List[dict]):
        """Process relay commands from Tower heartbeat response
        
        Args:
            relay_sessions: List of relay commands from Tower:
                [
                    {'session_id': 'abc', 'action': 'start', 'watchers_count': 2},
                    {'session_id': 'def', 'action': 'stop'},
                    ...
                ]
        """
        if not relay_sessions:
            # No active browser watchers - stop all relays
            if self.active_relays:
                logger.info(f"No relay requests from Tower - stopping {len(self.active_relays)} active relays")
                for session_id in list(self.active_relays.keys()):
                    self._stop_relay(session_id)
            return
        
        # Get list of sessions Tower wants us to relay
        requested_session_ids = {rs['session_id'] for rs in relay_sessions if rs.get('action') == 'start'}
        
        # Start new relays
        for relay_cmd in relay_sessions:
            session_id = relay_cmd['session_id']
            action = relay_cmd.get('action', 'start')
            watchers_count = relay_cmd.get('watchers_count', 0)
            
            if action == 'start' and session_id not in self.active_relays:
                self._start_relay(session_id, watchers_count)
            elif action == 'stop' and session_id in self.active_relays:
                self._stop_relay(session_id)
        
        # Stop relays that are no longer requested
        for session_id in list(self.active_relays.keys()):
            if session_id not in requested_session_ids:
                logger.info(f"[Relay:{session_id}] No longer requested by Tower - stopping")
                self._stop_relay(session_id)
    
    def _start_relay(self, session_id: str, watchers_count: int):
        """Start WebSocket relay for a session
        
        Args:
            session_id: Session ID to relay
            watchers_count: Number of browser watchers
        """
        # Get multiplexer for this session
        multiplexer = self.multiplexer_registry.get_session(session_id)
        
        if not multiplexer:
            logger.warning(f"[Relay:{session_id}] Cannot start relay - no multiplexer found")
            return
        
        try:
            logger.info(
                f"[Relay:{session_id}] Starting relay to Tower "
                f"({watchers_count} browser watcher{'s' if watchers_count != 1 else ''})"
            )
            
            # Create relay channel
            relay_channel = WebSocketRelayChannel(
                session_id=session_id,
                tower_url=self.tower_url,
                gate_api_key=self.gate_api_key,
                gate_name=self.gate_name,
                owner_username=multiplexer.owner_username,
                server_name=multiplexer.server_name,
                multiplexer=multiplexer  # Pass multiplexer for bidirectional relay
            )
            
            # Add as watcher to existing multiplexer
            watcher_id = f"tower_relay_{session_id}"
            success = multiplexer.add_watcher(
                watcher_id=watcher_id,
                channel=relay_channel,
                username="[Tower Relay]",
                mode="join"  # Join mode for bidirectional relay (input + output)
            )
            
            if success:
                self.active_relays[session_id] = relay_channel
                logger.info(
                    f"[Relay:{session_id}] ✓ Relay activated "
                    f"(Tower will broadcast to {watchers_count} browser client{'s' if watchers_count != 1 else ''})"
                )
            else:
                relay_channel.close()
                logger.error(f"[Relay:{session_id}] Failed to add as watcher to multiplexer")
        
        except Exception as e:
            logger.error(f"[Relay:{session_id}] Failed to start relay: {e}", exc_info=True)
    
    def _stop_relay(self, session_id: str):
        """Stop WebSocket relay for a session
        
        Args:
            session_id: Session ID
        """
        relay_channel = self.active_relays.pop(session_id, None)
        
        if not relay_channel:
            return
        
        try:
            logger.info(f"[Relay:{session_id}] Stopping relay (no more browser watchers)")
            
            # Remove from multiplexer
            multiplexer = self.multiplexer_registry.get_session(session_id)
            if multiplexer:
                watcher_id = f"tower_relay_{session_id}"
                multiplexer.remove_watcher(watcher_id)
            
            # Close WebSocket connection
            relay_channel.close()
            
            logger.info(f"[Relay:{session_id}] ✗ Relay stopped")
        
        except Exception as e:
            logger.error(f"[Relay:{session_id}] Error stopping relay: {e}")
    
    def stop_all(self):
        """Stop all active relays (called on gate shutdown)"""
        logger.info(f"Stopping all relays ({len(self.active_relays)} active)")
        
        for session_id in list(self.active_relays.keys()):
            self._stop_relay(session_id)
    
    def get_active_relay_count(self) -> int:
        """Get number of active relays"""
        return len(self.active_relays)
