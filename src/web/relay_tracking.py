"""
Relay Tracking - Manages browser watch requests for gate sessions

This module tracks which sessions browsers want to watch and provides
that information to gates via heartbeat responses.
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

# Global state: which sessions are being watched from browsers
# Format: {session_id: {'watchers': [sid1, sid2], 'gate_name': 'gate-name', 'session': DBSession}}
active_relay_requests: Dict[str, dict] = {}


def register_watch_request(session_id: str, gate_name: str, watcher_sid: str, session_obj=None):
    """Register that a browser wants to watch a session on a gate
    
    Args:
        session_id: Session ID to watch
        gate_name: Gate name where session is running
        watcher_sid: Socket.IO session ID of the browser
        session_obj: Optional database session object
    """
    if session_id not in active_relay_requests:
        active_relay_requests[session_id] = {
            'watchers': [],
            'gate_name': gate_name,
            'session': session_obj
        }
    
    if watcher_sid not in active_relay_requests[session_id]['watchers']:
        active_relay_requests[session_id]['watchers'].append(watcher_sid)
        logger.info(f"Relay request registered: {session_id} on {gate_name} (watcher: {watcher_sid})")


def unregister_watch_request(watcher_sid: str) -> List[str]:
    """Remove watcher from all relay requests
    
    Args:
        watcher_sid: Socket.IO session ID to remove
        
    Returns:
        List of session IDs that no longer have any watchers
    """
    sessions_to_cleanup = []
    
    for session_id, info in list(active_relay_requests.items()):
        if watcher_sid in info['watchers']:
            info['watchers'].remove(watcher_sid)
            logger.info(f"Watcher {watcher_sid} removed from {session_id}")
            
            # If no more watchers, mark for cleanup
            if len(info['watchers']) == 0:
                del active_relay_requests[session_id]
                sessions_to_cleanup.append(session_id)
                logger.info(f"Last watcher removed from {session_id} - relay will stop")
    
    return sessions_to_cleanup


def get_relay_requests_for_gate(gate_name: str, active_session_ids: List[str]) -> List[dict]:
    """Get list of sessions on this gate that need relay activation
    
    Called by heartbeat endpoint to inform gate which sessions to relay.
    
    Args:
        gate_name: Name of the gate
        active_session_ids: List of session IDs currently active on this gate
        
    Returns:
        List of relay commands:
        [
            {'session_id': 'abc123', 'action': 'start', 'watchers_count': 2},
            ...
        ]
    """
    relay_sessions = []
    
    # Find sessions from this gate that have browser watchers
    for session_id, info in active_relay_requests.items():
        if info['gate_name'] == gate_name and session_id in active_session_ids:
            relay_sessions.append({
                'session_id': session_id,
                'action': 'start',
                'watchers_count': len(info['watchers'])
            })
    
    return relay_sessions


def get_watchers_for_session(session_id: str) -> List[str]:
    """Get list of watcher Socket.IO session IDs for a session
    
    Args:
        session_id: Session ID
        
    Returns:
        List of watcher SIDs
    """
    if session_id in active_relay_requests:
        return active_relay_requests[session_id]['watchers'].copy()
    return []
