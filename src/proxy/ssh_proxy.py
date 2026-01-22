#!/usr/bin/env python3
"""
SSH Proxy Server with session recording
Intercepts SSH connections, validates access, forwards to backend, and records sessions
"""
import os
import sys
import json
import socket
import struct
import select
import threading
import logging
import time
import configparser
from datetime import datetime, timedelta
from pathlib import Path
import paramiko
import pytz

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Gate ALWAYS uses Tower API - no direct database access
from src.core.ip_pool import IPPoolManager
from src.core.utmp_helper import write_utmp_login, write_utmp_logout
from src.gate.api_client import TowerClient
from src.gate.config import GateConfig

# SO_ORIGINAL_DST constant for Linux TPROXY
SO_ORIGINAL_DST = 80

# Logging - basic setup (will be reconfigured after loading config)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ssh_proxy')

# Global variable for custom messages from Tower API
GATE_MESSAGES = {
    'welcome_banner': None,
    'no_backend': None,
    'no_person': None,
    'no_grant': None,
    'maintenance': None,
    'time_window': None
}


def load_messages():
    """Load custom messages from Tower API on startup"""
    global GATE_MESSAGES
    logger.info("Loading custom messages from Tower API")
    try:
        tower_client = TowerClient(GateConfig())
        messages = tower_client.get_messages()
        GATE_MESSAGES.update(messages)
        logger.info(f"Custom messages loaded successfully ({len([m for m in messages.values() if m])} configured)")
    except Exception as e:
        logger.error(f"Failed to load custom messages from Tower: {e}")
        # Use defaults - will be set when needed


def format_denial_message(result: dict, username: str, dest_ip: str, tower_client) -> str:
    """Format denial message based on denial_reason and custom messages from Tower.
    
    Args:
        result: Result dict from Tower API check_grant
        username: SSH username attempted
        dest_ip: Destination IP
        tower_client: Tower API client (for gate_name)
    
    Returns:
        Formatted message with replaced placeholders
    """
    denial_reason = result.get('denial_reason', 'access_denied')
    
    # Use person_fullname if available, fallback to person_username, then username parameter
    person = result.get('person_fullname') or result.get('person_username') or username
    backend = result.get('server_name') or result.get('server_ip') or dest_ip
    
    # Select appropriate message based on denial reason
    if denial_reason in ['gate_maintenance', 'backend_maintenance', 'maintenance_grace_period']:
        msg_template = GATE_MESSAGES.get('maintenance')
    elif denial_reason in ['unknown_source_ip', 'user_inactive']:
        msg_template = GATE_MESSAGES.get('no_person')
    elif denial_reason == 'server_not_found':
        msg_template = GATE_MESSAGES.get('no_backend')
    elif denial_reason == 'outside_schedule':
        msg_template = GATE_MESSAGES.get('time_window')
    else:  # no_matching_policy, ssh_login_not_allowed, etc.
        msg_template = GATE_MESSAGES.get('no_grant')
    
    # Fallback if message not configured
    if not msg_template:
        msg_template = f"Access denied: {{reason}}"
    
    # Replace placeholders
    msg = msg_template.replace('{person}', person)
    msg = msg.replace('{backend}', backend)
    msg = msg.replace('{gate_name}', getattr(tower_client.config, 'gate_name', 'Gate'))
    msg = msg.replace('{reason}', result.get('reason', 'Access denied'))
    
    return msg


class SSHSessionRecorder:
    """Records SSH session I/O and streams to Tower API in JSONL format.
    
    JSONL Format (JSON Lines - one event per line):
    {"type":"session_start","timestamp":"2026-01-07T12:00:00.000Z","username":"p.mojski","server":"10.0.160.4"}
    {"type":"client","timestamp":"2026-01-07T12:00:01.123Z","data":"ls -la\n"}
    {"type":"server","timestamp":"2026-01-07T12:00:01.245Z","data":"total 24\ndrwxr-xr-x..."}
    {"type":"session_end","timestamp":"2026-01-07T12:05:30.456Z","duration":330}
    
    - Buffers JSONL events in memory (~50 events)
    - Flushes to Tower every 3 seconds or when buffer full
    - Falls back to /tmp/ storage if Tower offline
    - Auto-uploads buffered recordings when Tower back online
    """
    
    def __init__(self, session_id: str, username: str, server_ip: str, server_name: str, tower_client, server_instance=None):
        self.session_id = session_id
        self.username = username
        self.server_ip = server_ip
        self.server_name = server_name
        self.tower_client = tower_client
        self.server_instance = server_instance  # Reference to SSHProxyServer for activity tracking
        self.start_time = datetime.now(pytz.UTC)
        
        # JSONL event buffer (list of event dicts)
        self.events_buffer = []
        self.buffer_max_events = 50  # Max events before flush
        self.chunk_index = 0
        self.total_events = 0
        self.total_bytes = 0
        self.last_flush = time.time()
        self.flush_interval = 3.0  # Flush every 3 seconds
        self.recording_path = None  # Will be set by Tower
        self.tower_online = True
        self.offline_file = None
        self.offline_path = None
        
        # Write session_start event
        self._write_event({
            'type': 'session_start',
            'timestamp': self.start_time.isoformat(),
            'username': username,
            'server': server_ip,
            'server_name': server_name
        })
        
        # Try to start recording on Tower
        try:
            response = self.tower_client.start_recording(
                session_id=session_id,
                person_username=username,
                server_name=server_name,
                server_ip=server_ip
            )
            self.recording_path = response.get('recording_path')
            self.recording_file = self.recording_path  # For compatibility
            logger.debug(f"Recording streaming to Tower: {self.recording_path}")
            
        except Exception as e:
            logger.warning(f"Tower unavailable for recording start: {e}. Using offline mode.")
            self.tower_online = False
            # Fallback to /tmp/ storage
            self.offline_path = f"/tmp/gate-recordings/{session_id}.jsonl"
            os.makedirs("/tmp/gate-recordings", exist_ok=True)
            self.offline_file = open(self.offline_path, 'a')  # Append mode for JSONL
            self.recording_file = self.offline_path
            logger.info(f"Recording to offline buffer: {self.offline_path}")
    
    def record_event(self, event_type: str, data: str):
        """Record a named event (session_start, session_end, etc.)"""
        self._write_event({
            'type': event_type,
            'timestamp': datetime.now(pytz.UTC).isoformat(),
            'data': data
        })
    
    def write_data(self, data: bytes, direction: str):
        """Write terminal I/O data as JSONL event
        
        Args:
            data: Raw bytes from terminal
            direction: 'client' or 'server'
        """
        try:
            # Decode bytes to string (replace invalid UTF-8)
            data_str = data.decode('utf-8', errors='replace')
        except Exception as e:
            logger.warning(f"Failed to decode data: {e}")
            data_str = repr(data)  # Fallback to repr
        
        self._write_event({
            'type': direction,
            'timestamp': datetime.now(pytz.UTC).isoformat(),
            'data': data_str
        })
    
    def _write_event(self, event: dict):
        """Write single event to buffer"""
        # Update last activity timestamp for inactivity timeout tracking
        if self.server_instance and self.session_id:
            self.server_instance.session_last_activity[self.session_id] = datetime.utcnow()
        
        if self.tower_online:
            # Add to buffer
            self.events_buffer.append(event)
            self.total_events += 1
            
            # Check if flush needed
            now = time.time()
            buffer_full = len(self.events_buffer) >= self.buffer_max_events
            time_to_flush = (now - self.last_flush) >= self.flush_interval
            
            if buffer_full or time_to_flush:
                self.flush()
        else:
            # Offline mode - write directly to /tmp/ as JSONL
            if self.offline_file:
                jsonl_line = json.dumps(event, separators=(',', ':')) + '\n'
                self.offline_file.write(jsonl_line)
                self.offline_file.flush()
                self.total_events += 1
                self.total_bytes += len(jsonl_line)
    
    def flush(self):
        """Flush JSONL events buffer to Tower"""
        if len(self.events_buffer) == 0:
            return
        
        try:
            # Convert events to JSONL (newline-delimited JSON)
            jsonl_data = '\n'.join(json.dumps(event, separators=(',', ':')) for event in self.events_buffer) + '\n'
            jsonl_bytes = jsonl_data.encode('utf-8')
            
            # Upload chunk to Tower
            self.tower_client.upload_recording_chunk(
                session_id=self.session_id,
                recording_path=self.recording_path,
                chunk_data=jsonl_bytes,
                chunk_index=self.chunk_index
            )
            
            logger.debug(f"Flushed {len(self.events_buffer)} events ({len(jsonl_bytes)} bytes) to Tower (chunk {self.chunk_index})")
            
            # Clear buffer
            self.total_bytes += len(jsonl_bytes)
            self.events_buffer.clear()
            self.chunk_index += 1
            self.last_flush = time.time()
            
        except Exception as e:
            logger.error(f"Failed to flush recording chunk: {e}")
            # Switch to offline mode
            if self.tower_online:
                logger.warning("Switching to offline recording mode")
                self.tower_online = False
                self.offline_path = f"/tmp/gate-recordings/{self.session_id}.jsonl"
                os.makedirs("/tmp/gate-recordings", exist_ok=True)
                self.offline_file = open(self.offline_path, 'a')
                # Write buffered events to offline file
                for event in self.events_buffer:
                    jsonl_line = json.dumps(event, separators=(',', ':')) + '\n'
                    self.offline_file.write(jsonl_line)
                self.offline_file.flush()
                self.events_buffer.clear()
    
    def save(self):
        """Finalize recording"""
        # Write session_end event
        duration = int((datetime.now(pytz.UTC) - self.start_time).total_seconds())
        self._write_event({
            'type': 'session_end',
            'timestamp': datetime.now(pytz.UTC).isoformat(),
            'duration': duration
        })
        
        # Final flush
        if self.tower_online and len(self.events_buffer) > 0:
            self.flush()
        
        # Close offline file if used
        if self.offline_file:
            self.offline_file.close()
            logger.info(f"Offline recording saved: {self.offline_path} ({self.total_events} events, {self.total_bytes} bytes)")
            
            # Try to upload offline recording
            self._upload_offline_recording()
        
        # Notify Tower that recording is complete
        if self.tower_online and self.recording_path:
            try:
                self.tower_client.finalize_recording(
                    session_id=self.session_id,
                    recording_path=self.recording_path,
                    total_bytes=self.total_bytes,
                    duration_seconds=duration
                )
                logger.info(f"Recording finalized on Tower: {self.total_events} events, {self.total_bytes} bytes")
            except Exception as e:
                logger.error(f"Failed to finalize recording: {e}")
    
    def _upload_offline_recording(self):
        """Upload offline JSONL recording to Tower when it comes back online"""
        if not self.offline_path or not os.path.exists(self.offline_path):
            return
        
        try:
            # Try to start recording on Tower
            response = self.tower_client.start_recording(
                session_id=self.session_id,
                person_username=self.username,
                server_name=self.server_name,
                server_ip=self.server_ip
            )
            recording_path = response.get('recording_path')
            
            # Upload file in chunks (read ~50 lines at a time)
            chunk_index = 0
            lines_per_chunk = 50
            
            with open(self.offline_path, 'r') as f:
                while True:
                    lines = []
                    for _ in range(lines_per_chunk):
                        line = f.readline()
                        if not line:
                            break
                        lines.append(line.rstrip('\n'))
                    
                    if not lines:
                        break
                    
                    # Join lines with newline and add final newline
                    jsonl_chunk = '\n'.join(lines) + '\n'
                    
                    self.tower_client.upload_recording_chunk(
                        session_id=self.session_id,
                        recording_path=recording_path,
                        chunk_data=jsonl_chunk.encode('utf-8'),
                        chunk_index=chunk_index
                    )
                    chunk_index += 1
            
            # Finalize
            duration = int((datetime.now(pytz.UTC) - self.start_time).total_seconds())
            self.tower_client.finalize_recording(
                session_id=self.session_id,
                recording_path=recording_path,
                total_bytes=self.total_bytes,
                duration_seconds=duration
            )
            
            # Delete offline file
            os.remove(self.offline_path)
            logger.info(f"Offline JSONL recording uploaded and deleted: {self.offline_path}")
            
        except Exception as e:
            logger.error(f"Failed to upload offline recording: {e}. Will retry later.")
            # Keep file for manual recovery or next startup


class SSHProxyHandler(paramiko.ServerInterface):
    """Handles SSH authentication and channel requests"""
    
    def __init__(self, source_ip: str, dest_ip: str):
        self.source_ip = source_ip
        self.dest_ip = dest_ip  # NEW: destination IP client connected to
        self.tower_client = TowerClient(GateConfig())
        self.authenticated_user = None
        self.target_server = None
        self.matching_policies = []  # Policies that granted access
        self.client_password = None
        self.client_key = None
        self.agent_channel = None  # For agent forwarding
        self.no_grant_reason = None  # Reason for no grant (for banner message)
        self.attempted_username = None  # Username from first auth attempt (for banner)
        self.is_tproxy = False  # Will be set to True by handle_client if TPROXY connection
        
        # EARLY grant check - BEFORE get_banner() is called
        # Check if source IP has ANY access to this destination
        # This allows us to show banner early if IP has no access at all
        logger.info(f"SSHProxyHandler init: early check for {source_ip} -> {dest_ip}")
        try:
            # Call Tower API for access check (without ssh_login for early check)
            result = self.tower_client.check_grant(
                source_ip=self.source_ip,
                destination_ip=self.dest_ip,
                protocol='ssh',
                ssh_login=None  # Early check without specific username
            )
            
            if not result.get('allowed'):
                logger.warning(f"No grant for IP {self.source_ip} to {self.dest_ip}: {result.get('reason')}")
                # Format denial message for banner
                self.no_grant_reason = format_denial_message(result, "user", self.dest_ip, self.tower_client)
            else:
                logger.debug(f"Grant found for {self.source_ip}, proceeding with auth")
                
        except Exception as e:
            logger.error(f"Error in early grant check: {e}", exc_info=True)
        
        # PTY parameters from client
        self.pty_term = None
        self.pty_width = None
        self.pty_height = None
        self.pty_modes = None
        # Grant check cache - check only once per connection
        self.grant_checked = False
        self.grant_result = None
        # Channel type and exec command
        self.channel_type = None  # 'shell', 'exec', or 'subsystem'
        self.exec_command = None
        self.subsystem_name = None
        self.ssh_login = None  # SSH login name for backend
        # Port forwarding destinations
        self.forward_destinations = {}  # chanid -> (host, port)
        
    def check_auth_none(self, username: str):
        """Check 'none' authentication - called AFTER get_banner
        
        NOTE: Paramiko calls get_banner() FIRST, then check_auth_none()!
        If no_grant_reason was set by early check (without username), 
        we re-check here with username to get proper person info.
        
        Return AUTH_FAILED to proceed with other auth methods.
        """
        logger.debug(f"check_auth_none called for {username} from {self.source_ip}")
        
        # Save username
        self.attempted_username = username
        
        # If no_grant_reason already set from early check, or if not yet checked,
        # do grant check now with username for proper person info
        if not self.grant_checked:
            try:
                result = self.tower_client.check_grant(
                    source_ip=self.source_ip,
                    destination_ip=self.dest_ip,
                    protocol='ssh',
                    ssh_login=username
                )
                
                # Cache result regardless of outcome to avoid redundant API calls
                self.grant_checked = True
                self.grant_result = result
                
                if not result.get('allowed'):
                    # NO GRANT - format denial message with username
                    logger.warning(f"Access denied in check_auth_none: {result.get('reason')}")
                    self.no_grant_reason = format_denial_message(result, username, self.dest_ip, self.tower_client)
                else:
                    # Grant OK - clear any early denial
                    self.no_grant_reason = None  # Clear early denial if now granted
            except Exception as e:
                logger.error(f"Failed to check grant in check_auth_none: {e}")
                self.no_grant_reason = f"Hello, I'm Gate, an entry point of Inside.\nInternal error occurred. Please contact your system administrator."
        
        return paramiko.AUTH_FAILED
        
    def check_auth_password(self, username: str, password: str):
        """Check password authentication"""
        logger.info(f"Auth attempt: {username} from {self.source_ip} to {self.dest_ip}")
        
        # Check access permissions using Tower API (cache result)
        if not self.grant_checked:
            result = self.tower_client.check_grant(
                source_ip=self.source_ip,
                destination_ip=self.dest_ip,
                protocol='ssh',
                ssh_login=username
            )
            self.grant_checked = True
            self.grant_result = result
        else:
            result = self.grant_result
        
        if not result.get('allowed'):
            logger.warning(f"Access denied for {username} from {self.source_ip}: {result.get('reason')}")
            # Denied sessions are logged via Tower API audit trail (check_grant call)
            
            # Format denial message using custom messages from Tower
            self.no_grant_reason = format_denial_message(result, username, self.dest_ip, self.tower_client)
            return paramiko.AUTH_FAILED
        
        # All checks passed - store result data
        # Build target_server and authenticated_user objects from API response
        self.target_server = type('Server', (), {
            'id': result['server_id'],
            'name': result['server_name'],
            'ip_address': result['server_ip']
        })()
        self.authenticated_user = type('User', (), {
            'id': result['person_id'],
            'username': result['person_username'],
            'full_name': result.get('person_fullname')
        })()
        self.access_result = result  # Store full result for effective_end_time
        self.ssh_login = username  # SSH login for backend (e.g., "ideo")
        self.client_password = password
        
        logger.info(f"Access granted: {username} → {self.target_server.ip_address} (via {self.dest_ip})")
        return paramiko.AUTH_SUCCESSFUL
    
    def check_auth_publickey(self, username: str, key):
        """Check public key authentication by testing it on backend server.
        
        This is the correct approach:
        1. Check if user has access policy
        2. Try to authenticate to backend with this key
        3. If backend accepts key → AUTH_SUCCESSFUL
        4. If backend rejects key → AUTH_FAILED (client will try password)
        """
        logger.debug(f"Pubkey auth attempt: {username} from {self.source_ip} to {self.dest_ip}, key type: {key.get_name()}")
        
        # Check access permissions using Tower API (cache result)
        if not self.grant_checked:
            result = self.tower_client.check_grant(
                source_ip=self.source_ip,
                destination_ip=self.dest_ip,
                protocol='ssh',
                ssh_login=username
            )
            self.grant_checked = True
            self.grant_result = result
        else:
            result = self.grant_result
        
        if not result.get('allowed'):
            logger.warning(f"Access denied for {username} from {self.source_ip}: {result.get('reason')}")
            # Format denial message using custom messages from Tower
            self.no_grant_reason = format_denial_message(result, username, self.dest_ip, self.tower_client)
            return paramiko.AUTH_FAILED
        
        # Accept pubkey - backend will verify agent forwarding works
        # If agent fails, we'll disconnect properly for password retry
        logger.debug(f"Pubkey accepted - will verify agent forwarding in backend")
        
        # Store authentication info from API response
        self.target_server = type('Server', (), {
            'id': result['server_id'],
            'name': result['server_name'],
            'ip_address': result['server_ip']
        })()
        self.authenticated_user = type('User', (), {
            'id': result['person_id'],
            'username': result['person_username'],
            'full_name': result.get('person_fullname')
        })()
        self.access_result = result  # Store full result for effective_end_time
        self.ssh_login = username  # SSH login for backend (e.g., "ideo")
        self.client_key = key
        
        return paramiko.AUTH_SUCCESSFUL
    
    def check_auth_interactive(self, username, submethods):
        """Check keyboard-interactive authentication (for switches, telnet-like devices).
        
        Some devices (especially switches) use keyboard-interactive method
        where they send custom prompts (e.g. "User Name:", "Password:").
        
        IMPORTANT: OpenSSH client prefers keyboard-interactive over password auth.
        We must distinguish between:
        1. Real keyboard-interactive devices (switches) - accept this method
        2. Normal Linux servers - reject this method to force client to use password
        
        We detect switches by attempting to connect to backend and check if it
        accepts auth_none (no SSH authentication, telnet-like).
        """
        logger.info(f"Interactive auth attempt: {username} from {self.source_ip} to {self.dest_ip}")
        
        # Check access permissions using Tower API (cache result)
        if not self.grant_checked:
            result = self.tower_client.check_grant(
                source_ip=self.source_ip,
                destination_ip=self.dest_ip,
                protocol='ssh',
                ssh_login=username
            )
            self.grant_checked = True
            self.grant_result = result
        else:
            result = self.grant_result
        
        if not result.get('allowed'):
            logger.warning(f"Access denied for {username} from {self.source_ip}: {result.get('reason')}")
            # Format denial message using custom messages from Tower
            self.no_grant_reason = format_denial_message(result, username, self.dest_ip, self.tower_client)
            return paramiko.AUTH_FAILED
        
        # Quick test: Try to detect if backend is a switch (accepts auth_none)
        # This prevents normal Linux servers from accepting keyboard-interactive
        # when client should be using password auth
        import socket
        try:
            backend_ip = result['server_ip']
            logger.info(f"Testing if {backend_ip} is a switch (accepts auth_none)...")
            
            # Quick connection test
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_sock.settimeout(2.0)
            test_sock.connect((backend_ip, 22))
            
            test_transport = paramiko.Transport(test_sock)
            test_transport.start_client()
            
            # Try auth_none - switches accept this
            try:
                test_transport.auth_none(username)
                # Success - this is a switch!
                logger.info(f"Backend {backend_ip} accepts auth_none - detected as switch/telnet-like device")
                test_transport.close()
                is_switch = True
            except paramiko.BadAuthenticationType as e:
                # Backend requires real auth - this is a normal server
                logger.info(f"Backend {backend_ip} requires auth - this is NOT a switch, rejecting keyboard-interactive")
                test_transport.close()
                is_switch = False
            except Exception as e:
                logger.warning(f"Backend auth test failed: {e}, assuming NOT a switch")
                test_transport.close()
                is_switch = False
        
        except Exception as e:
            logger.error(f"Failed to test backend: {e}, assuming NOT a switch")
            is_switch = False
        
        # If not a switch, reject keyboard-interactive to force client to use password
        if not is_switch:
            logger.info(f"Rejecting keyboard-interactive for normal server, client should try password")
            return paramiko.AUTH_FAILED
        
        # This is a switch - accept keyboard-interactive
        logger.info(f"Backend is a switch - accepting keyboard-interactive")
        
        # Store authentication info from API response
        self.target_server = type('Server', (), {
            'id': result['server_id'],
            'name': result['server_name'],
            'ip_address': result['server_ip']
        })()
        self.authenticated_user = type('User', (), {
            'id': result['person_id'],
            'username': result['person_username'],
            'full_name': result.get('person_fullname')
        })()
        self.access_result = result
        self.ssh_login = username
        self.client_interactive = True  # Flag for backend auth
        
        # Return interactive response - backend will send prompts
        # InteractiveQuery takes *prompts as varargs, not keyword argument
        # For now, return empty query - we'll proxy backend's prompts later
        logger.info(f"Interactive auth accepted for {username}, backend will handle prompts")
        return paramiko.InteractiveQuery('', '')
    
    def check_auth_interactive_response(self, responses):
        """Process keyboard-interactive responses.
        
        Called after user provides responses to prompts.
        For switch authentication, we accept the responses and will
        forward them to backend during connection.
        """
        logger.info(f"Interactive auth responses received: {len(responses)} responses")
        # Store responses to forward to backend
        self.interactive_responses = responses
        return paramiko.AUTH_SUCCESSFUL
    
    def get_allowed_auths(self, username):
        """Return allowed authentication methods
        
        Called after check_auth_none() and before get_banner().
        Grant check is already done in check_auth_none().
        
        We support:
        - publickey: Standard SSH key authentication
        - password: Standard password authentication
        - keyboard-interactive: For switches and devices with custom prompts
        """
        logger.info(f"get_allowed_auths called for {username} from {self.source_ip} to {self.dest_ip}")
        
        # If denied (check_auth_none already set no_grant_reason), return only publickey
        # Client will see banner and stop without password prompt
        if self.no_grant_reason:
            logger.info(f"get_allowed_auths: no grant detected, returning only publickey")
            return "publickey"
        
        # Grant OK - return all methods
        logger.info(f"get_allowed_auths: grant OK, returning publickey,password,keyboard-interactive")
        return "publickey,password,keyboard-interactive"
    
    def get_banner(self):
        """Return SSH banner message
        
        If user has no grant, return a polite rejection message.
        Uses custom messages from Tower API (already prepared in check_auth).
        Must return tuple (banner, language) - default is (None, None).
        
        Note: Paramiko expects str (Python 3 unicode string) and will encode it as UTF-8.
        """
        logger.debug(f"get_banner called, no_grant_reason={'set' if self.no_grant_reason else 'None'}")
        if self.no_grant_reason:
            # no_grant_reason already contains formatted message with replaced placeholders
            # Ensure it's a proper unicode string (Python 3 str)
            banner = f"\r\n{self.no_grant_reason}\r\n\r\n"
            
            # Ensure the string is properly encoded/decoded as UTF-8
            # In case there are any encoding issues from the API
            if isinstance(banner, bytes):
                banner = banner.decode('utf-8')
            
            logger.debug(f"get_banner returning banner message ({len(banner)} chars)")
            return (banner, "en-US")
        
        # No banner - return default as per paramiko docs
        return (None, None)
    
    def check_channel_request(self, kind: str, chanid: int):
        """Allow session, direct-tcpip (port forwarding -L) and dynamic-tcpip (SOCKS -D) channel requests"""
        logger.debug(f"Channel request: kind={kind}, chanid={chanid}")
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        elif kind == 'direct-tcpip':
            # Port forwarding (-L local forward)
            return paramiko.OPEN_SUCCEEDED
        elif kind == 'dynamic-tcpip':
            # SOCKS proxy (-D dynamic forward)
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED
    
    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        """Allow PTY requests and save parameters"""
        logger.debug(f"PTY request: term={term}, width={width}, height={height}")
        # Save PTY parameters to use for backend connection
        self.pty_term = term
        self.pty_width = width
        self.pty_height = height
        self.pty_modes = modes
        return True
    
    def check_channel_shell_request(self, channel):
        """Allow shell requests"""
        logger.debug("Shell request received")
        self.channel_type = 'shell'
        return True
    
    def check_channel_exec_request(self, channel, command):
        """Allow exec requests (for SCP, etc)"""
        cmd_str = command.decode('utf-8') if isinstance(command, bytes) else command
        logger.info(f"Exec request: {cmd_str}")
        self.channel_type = 'exec'
        self.exec_command = command
        return True
    
    def check_channel_subsystem_request(self, channel, name):
        """Allow subsystem requests (for SFTP/SCP)"""
        subsys_name = name.decode('utf-8') if isinstance(name, bytes) else name
        logger.info(f"Subsystem request: {subsys_name}")
        self.channel_type = 'subsystem'
        self.subsystem_name = name
        return True
    
    def check_channel_forward_agent_request(self, channel):
        """Allow agent forwarding and setup handler"""
        logger.debug("Client requested agent forwarding")
        # Store the channel for later use
        self.agent_channel = channel
        return True
    
    def check_port_forward_request(self, address, port):
        """Handle tcpip-forward requests for remote port forwarding (-R)
        
        For -R, we open the port locally on the jump host and forward 
        connections to the client via SSH channel.
        
        Args:
            address: Address to bind (usually '' or 'localhost')
            port: Port to bind
            
        Note: SSH protocol does NOT send the destination (e.g. localhost:8080 from -R 9090:localhost:8080).
        We only know the bind address/port. The destination is stored only on client side.
        """
        logger.info(f"Remote forward request: bind {address}:{port} (destination unknown - SSH protocol limitation)")
        
        # Check if user has port forwarding permission (from Tower API result)
        allowed = self.access_result.get('port_forwarding_allowed', False) if hasattr(self, 'access_result') else False
        
        if not allowed:
            logger.warning(f"Remote port forwarding denied for source {self.source_ip}")
            return False
        
        logger.info(f"Remote port forwarding allowed for {address}:{port}")
        
        # Store the request so we can open the port later
        # (after we have the transport object)
        # ASSUMPTION: We assume -R forwards to the same port (e.g. -R 9090:localhost:9090)
        # because SSH protocol doesn't send destination in tcpip-forward message
        if not hasattr(self, 'remote_forward_requests'):
            self.remote_forward_requests = []
        self.remote_forward_requests.append((address, port))
        
        return port  # Return the port that will be bound
    
    def cancel_port_forward_request(self, address, port):
        """Handle cancel-tcpip-forward requests"""
        logger.info(f"Cancel remote forward: {address}:{port}")
        return True
    
    def check_channel_direct_tcpip_request(self, chanid, origin, destination):
        """Handle direct-tcpip requests for port forwarding (-L)
        
        Args:
            chanid: Channel ID
            origin: (host, port) where client is connecting from
            destination: (host, port) where client wants to connect to
        """
        logger.info(f"Direct-TCPIP request: {origin} -> {destination}")
        
        # Check if user has port forwarding permission (from Tower API result)
        allowed = self.access_result.get('port_forwarding_allowed', False) if hasattr(self, 'access_result') else False
        
        if not allowed:
            logger.warning(f"Port forwarding denied for source {self.source_ip}")
            return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED
        
        # Store destination for the forwarding handler
        self.forward_destinations = getattr(self, 'forward_destinations', {})
        self.forward_destinations[chanid] = destination
        
        logger.info(f"Port forwarding allowed to {destination}")
        return paramiko.OPEN_SUCCEEDED


class SSHProxyServer:
    """SSH Proxy Server - intercepts and forwards connections"""
    
    def __init__(self, nat_config=None, tproxy_config=None, host_key_path='/var/lib/inside-gate/ssh_host_key'):
        """
        Initialize SSH Proxy Server with dual mode support
        
        Args:
            nat_config: Dict with 'host' and 'port' for NAT mode (or None to disable)
            tproxy_config: Dict with 'host' and 'port' for TPROXY mode (or None to disable)
            host_key_path: Path to SSH host key file
        """
        self.nat_config = nat_config  # Keep None if not provided
        self.tproxy_config = tproxy_config
        self.host_key_path = host_key_path
        self.host_key = self._load_or_generate_host_key()
        self.tower_client = TowerClient(GateConfig())
        self.heartbeat_interval = 30  # seconds
        self.heartbeat_thread = None
        self.running = False
        # Registry of active connections: session_id -> (client_transport, backend_transport)
        self.active_connections = {}
        # Forced disconnection times: session_id -> datetime (UTC)
        # Used by heartbeat to inject immediate/scheduled disconnections
        self.session_forced_endtimes = {}
        # Current grant end times: session_id -> datetime (UTC)
        # Used to detect grant extensions (renew)
        self.session_grant_endtimes = {}
        # Last activity tracking for inactivity timeout: session_id -> datetime (UTC)
        self.session_last_activity = {}
        # Session metadata for terminal title: session_id -> {grant_end_time, inactivity_timeout, server_name}
        self.session_metadata = {}
        
    def _load_or_generate_host_key(self):
        """Load or generate SSH host key"""
        key_file = Path(self.host_key_path)
        
        # Create directory if not exists
        key_file.parent.mkdir(parents=True, exist_ok=True)
        
        if key_file.exists():
            logger.info(f"Loading SSH host key from {key_file}")
            return paramiko.RSAKey(filename=str(key_file))
        else:
            logger.info(f"Generating new SSH host key at {key_file}...")
            key = paramiko.RSAKey.generate(2048)
            key.write_private_key_file(str(key_file))
            return key
    
    def get_original_dst(self, sock):
        """
        Extract original destination IP:port from TPROXY socket.
        
        For TPROXY mode, the original destination is preserved on the socket itself.
        Use getsockname() on the accepted client socket to get original destination.
        
        Returns tuple (ip, port) or None if extraction fails.
        """
        try:
            # For TPROXY, the socket preserves the original destination address
            # getsockname() returns the original destination (not local bind address)
            original_ip, original_port = sock.getsockname()
            
            logger.debug(f"TPROXY: Extracted original destination {original_ip}:{original_port}")
            return (original_ip, original_port)
            
        except Exception as e:
            logger.error(f"Failed to extract original destination: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def forward_channel(self, client_channel, backend_channel, recorder: SSHSessionRecorder = None, db_session_id=None, is_sftp=False, session_id=None, server_name=None):
        """Forward data between client and backend server via SSH channels
        
        Args:
            session_id: Session identifier for terminal title clearing
            server_name: Server name for terminal title
        """
        bytes_sent = 0
        bytes_received = 0
        sftp_transfer_id = None
        
        # For SFTP, create transfer record
        if is_sftp and db_session_id:
            try:
                sftp_transfer_id = self.log_sftp_transfer(db_session_id)
            except Exception as e:
                logger.error(f"Failed to create SFTP transfer record: {e}")
        
        try:
            while True:
                # Check if channels are still open
                if client_channel.closed or backend_channel.closed:
                    break
                
                r, w, x = select.select([client_channel, backend_channel], [], [], 1.0)
                
                if client_channel in r:
                    data = client_channel.recv(4096)
                    if len(data) == 0:
                        break
                    backend_channel.send(data)
                    bytes_sent += len(data)
                    if recorder:
                        # Stream client→server data to Tower as JSONL
                        recorder.write_data(data, 'client')
                
                if backend_channel in r:
                    data = backend_channel.recv(4096)
                    if len(data) == 0:
                        break
                    client_channel.send(data)
                    bytes_received += len(data)
                    if recorder:
                        # Stream server→client data to Tower as JSONL
                        recorder.write_data(data, 'server')
        
        except Exception as e:
            logger.debug(f"Channel forwarding ended: {e}")
        
        finally:
            # Clear terminal title BEFORE closing channels (still writable)
            if session_id and server_name:
                try:
                    self.clear_terminal_title(client_channel, server_name)
                    logger.debug(f"Session {session_id}: Cleared terminal title on disconnect")
                except:
                    pass
            
            # Update SFTP transfer stats
            if is_sftp and sftp_transfer_id:
                try:
                    self.update_transfer_stats(sftp_transfer_id, bytes_sent, bytes_received)
                    logger.info(f"SFTP transfer completed: sent={bytes_sent} bytes, received={bytes_received} bytes")
                except Exception as e:
                    logger.error(f"Failed to update SFTP transfer stats: {e}")
            
            # Give client time to send DISCONNECT message
            import time
            time.sleep(0.1)
            
            # Close channels gracefully if still open
            try:
                if not client_channel.closed:
                    client_channel.close()
            except:
                pass
            try:
                if not backend_channel.closed:
                    backend_channel.close()
            except:
                pass
    
    def handle_port_forwarding(self, client_transport, backend_transport, server_handler, user, target_server):
        """Handle port forwarding requests (-L, -R, -D)
        
        Monitors client transport for new channel requests and forwards them to backend.
        This runs in a background thread while the main session is active.
        """
        try:
            logger.debug(f"Port forwarding handler started for {user.username}")
            
            # Wait for transport to become fully active
            while not client_transport.is_active():
                import time
                time.sleep(0.1)
            
            # Continuously accept new forwarding channels
            while client_transport.is_active():
                try:
                    # Accept new channel with short timeout
                    channel = client_transport.accept(timeout=1.0)
                    
                    if channel is None:
                        continue
                    
                    # Get the destination for this channel
                    chanid = channel.get_id()
                    destination = server_handler.forward_destinations.get(chanid)
                    
                    if not destination:
                        logger.warning(f"No destination found for channel {chanid}")
                        channel.close()
                        continue
                    
                    dest_addr, dest_port = destination
                    logger.info(f"Forwarding channel {chanid} to {dest_addr}:{dest_port}")
                    
                    # Log port forward to database
                    transfer_id = None
                    db_session = getattr(server_handler, 'db_session', None)
                    if db_session:
                        try:
                            # Get local address/port from channel
                            local_addr, local_port = channel.getpeername() if hasattr(channel, 'getpeername') else ('unknown', 0)
                            transfer_id = self.log_port_forward(
                                db_session.id,
                                'port_forward_local',  # -L
                                local_addr,
                                local_port,
                                dest_addr,
                                dest_port
                            )
                        except Exception as e:
                            logger.error(f"Failed to log port forward: {e}")
                    
                    # Open corresponding channel on backend
                    try:
                        # For direct-tcpip, we need to connect from backend to the target
                        backend_channel = backend_transport.open_channel(
                            'direct-tcpip',
                            (dest_addr, dest_port),
                            ('127.0.0.1', 0)  # Our address from backend's perspective
                        )
                        
                        # Start forwarding in a new thread
                        forward_thread = threading.Thread(
                            target=self.forward_port_channel,
                            args=(channel, backend_channel, dest_addr, dest_port, transfer_id),
                            daemon=True
                        )
                        forward_thread.start()
                        logger.info(f"Started forwarding thread for {dest_addr}:{dest_port}")
                        
                    except Exception as e:
                        logger.error(f"Failed to open backend channel: {e}")
                        channel.close()
                        
                except Exception as e:
                    if "timeout" not in str(e).lower():
                        logger.debug(f"Accept error: {e}")
            
            logger.info("Port forwarding handler exiting (transport inactive)")
            
        except Exception as e:
            logger.error(f"Port forwarding handler error: {e}", exc_info=True)
    
    def handle_reverse_forwarding(self, client_transport, backend_transport, server_handler, port_map):
        """Handle reverse port forwarding (-R) from backend to client
        
        Args:
            port_map: Dict mapping backend port -> (client_addr, client_port)
        
        When someone connects to a port on backend that was opened by -R,
        backend sends us a channel that we need to forward to client.
        """
        try:
            logger.info("Reverse forwarding handler started")
            
            # Wait for backend transport to become active
            while not backend_transport.is_active():
                import time
                time.sleep(0.1)
            
            # Accept channels from backend
            while backend_transport.is_active() and client_transport.is_active():
                try:
                    # Accept channel from backend with timeout
                    backend_channel = backend_transport.accept(timeout=1.0)
                    
                    if backend_channel is None:
                        continue
                    
                    logger.info(f"Got reverse forward channel from backend")
                    
                    # Get channel info - for forwarded-tcpip, paramiko should have this
                    # We need to extract where backend wants us to connect
                    origin = getattr(backend_channel, 'origin_addr', ('unknown', 0))
                    
                    logger.info(f"Reverse forward from backend: {origin}")
                    
                    # Open channel to client - this should trigger client to connect locally
                    # For -R, client expects forwarded-tcpip channel
                    try:
                        # We need to forward this back to client
                        # The client will handle connecting to its local service
                        
                        # Just forward the existing backend channel to client
                        # Client transport should accept this as forwarded-tcpip
                        
                        # Start forwarding thread
                        forward_thread = threading.Thread(
                            target=self.forward_reverse_channel,
                            args=(client_transport, backend_channel, origin, port_map),
                            daemon=True
                        )
                        forward_thread.start()
                        
                    except Exception as e:
                        logger.error(f"Failed to setup reverse forward: {e}")
                        backend_channel.close()
                        
                except Exception as e:
                    if "timeout" not in str(e).lower():
                        logger.debug(f"Reverse accept error: {e}")
            
            logger.info("Reverse forwarding handler exiting")
            
        except Exception as e:
            logger.error(f"Reverse forwarding handler error: {e}", exc_info=True)
    
    def forward_reverse_channel(self, client_transport, backend_channel, origin, port_map):
        """Forward a reverse channel from backend to client
        
        Args:
            port_map: Dict mapping backend port -> (client_addr, client_port)
        
        When someone connects to the forwarded port on backend, backend opens
        a channel to us. We need to relay this to the client, which will
        connect to its local service.
        """
        try:
            # For now, if we only have one mapping, use it
            if len(port_map) == 1:
                dest_addr, dest_port = list(port_map.values())[0]
                logger.info(f"Using single port mapping: {dest_addr}:{dest_port}")
            else:
                logger.error(f"Multiple port mappings not yet supported: {port_map}")
                backend_channel.close()
                return
            
            # Instead of trying to open SSH channel to client (which fails),
            # we need to make client open a channel to US and connect to localhost:8080
            # The way to do this is to send a forwarded-tcpip channel request
            
            # Try using the proper paramiko method for server-initiated forwarded-tcpip
            try:
                # Get the Transport object's  channel open method
                # We need to manually craft the channel open request
                from paramiko import Channel
                from paramiko.common import cMSG_CHANNEL_OPEN
                
                # Create a new channel on client transport
                chanid = client_transport._next_channel()
                chan = Channel(chanid)
                client_transport._channels.put(chanid, chan)
                
                m = paramiko.Message()
                m.add_byte(cMSG_CHANNEL_OPEN)
                m.add_string('forwarded-tcpip')
                m.add_int(chanid)
                m.add_int(chan.in_window_size)
                m.add_int(chan.in_max_packet_size)
                m.add_string(dest_addr)  # Address to connect to on client
                m.add_int(dest_port)  # Port to connect to on client
                m.add_string(origin[0])  # Origin address
                m.add_int(origin[1])  # Origin port
                
                client_transport._send_user_message(m)
                chan._wait_for_event()
                
                logger.info(f"Opened forwarded-tcpip channel to client {dest_addr}:{dest_port}")
                
                # Forward data
                self.forward_port_channel(backend_channel, chan, dest_addr, dest_port)
                
            except Exception as e:
                logger.error(f"Failed to open forwarded-tcpip: {e}, traceback:", exc_info=True)
                backend_channel.close()
            
        except Exception as e:
            logger.error(f"Reverse forward channel error: {e}")
            backend_channel.close()
    
    def forward_port_channel(self, client_channel, backend_channel, dest_addr, dest_port, transfer_id=None):
        """Forward data between port forwarding channels (no recording)"""
        bytes_sent = 0
        bytes_received = 0
        
        try:
            logger.info(f"Forwarding data for {dest_addr}:{dest_port}")
            
            while True:
                if client_channel.closed or backend_channel.closed:
                    break
                
                r, w, x = select.select([client_channel, backend_channel], [], [], 1.0)
                
                if client_channel in r:
                    data = client_channel.recv(4096)
                    if len(data) == 0:
                        break
                    backend_channel.send(data)
                    bytes_sent += len(data)
                
                if backend_channel in r:
                    data = backend_channel.recv(4096)
                    if len(data) == 0:
                        break
                    client_channel.send(data)
                    bytes_received += len(data)
        
        except Exception as e:
            logger.debug(f"Port forward channel ended: {e}")
        
        finally:
            logger.info(f"Closing forward channel for {dest_addr}:{dest_port} (sent={bytes_sent}, received={bytes_received})")
            
            # Update transfer stats in database
            if transfer_id:
                try:
                    self.update_transfer_stats(transfer_id, bytes_sent, bytes_received)
                except Exception as e:
                    logger.error(f"Failed to update transfer stats: {e}")
            
            try:
                if not client_channel.closed:
                    client_channel.close()
            except:
                pass
            try:
                if not backend_channel.closed:
                    backend_channel.close()
            except:
                pass
    
    def handle_pool_ip_to_localhost_forward(self, pool_ip, port, client_transport):
        """Forward connections from pool IP to client via SSH forwarded-tcpip channel
        
        Pool IP listener accepts connections (e.g. from backend) and opens 
        forwarded-tcpip channels to the client.
        
        Args:
            pool_ip: IP address from pool (e.g. 10.0.160.129)
            port: Port to forward
            client_transport: Client's SSH transport for opening channels
        """
        import socket
        
        try:
            # Create listening socket on pool IP
            listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listen_sock.bind((pool_ip, port))
            listen_sock.listen(5)
            listen_sock.settimeout(1.0)
            
            logger.info(f"Listening on {pool_ip}:{port}, forwarding via SSH to client")
            
            # Accept connections and forward to client via SSH channel
            while client_transport.is_active():
                try:
                    conn, conn_addr = listen_sock.accept()
                    logger.info(f"Connection from {conn_addr} to {pool_ip}:{port}")
                    
                    # Open forwarded-tcpip channel to client
                    # SSH protocol limitation: we don't know the actual destination from -R request
                    # We assume client used -R port:localhost:port (same port for bind and destination)
                    try:
                        client_channel = client_transport.open_channel(
                            'forwarded-tcpip',
                            ('localhost', port),  # Assumed destination - same port as bind
                            (conn_addr[0], conn_addr[1])  # Originator (who connected)
                        )
                        
                        logger.info(f"Opened forwarded-tcpip channel to client for {conn_addr}")
                        
                        # Relay data bidirectionally between socket and channel
                        def relay_socket_to_channel(sock, chan):
                            try:
                                while True:
                                    r, _, _ = select.select([sock, chan], [], [], 1.0)
                                    
                                    if sock in r:
                                        data = sock.recv(4096)
                                        if len(data) == 0:
                                            break
                                        chan.send(data)
                                    
                                    if chan in r:
                                        data = chan.recv(4096)
                                        if len(data) == 0:
                                            break
                                        sock.send(data)
                            except Exception as e:
                                logger.debug(f"Relay ended: {e}")
                            finally:
                                try:
                                    sock.close()
                                except:
                                    pass
                                try:
                                    chan.close()
                                except:
                                    pass
                        
                        relay_thread = threading.Thread(
                            target=relay_socket_to_channel,
                            args=(conn, client_channel),
                            daemon=True
                        )
                        relay_thread.start()
                        
                    except Exception as e:
                        logger.error(f"Failed to open channel to client: {e}")
                        conn.close()
                        
                except socket.timeout:
                    continue
                except Exception as e:
                    if client_transport.is_active():
                        logger.error(f"Accept error on {pool_ip}:{port}: {e}")
                    break
            
            logger.info(f"Pool IP listener on {pool_ip}:{port} exiting")
            listen_sock.close()
            
        except Exception as e:
            logger.error(f"Pool IP listener error on {pool_ip}:{port}: {e}", exc_info=True)
    
    def handle_cascaded_reverse_forward(self, client_transport, backend_transport, server_handler):
        """Handle cascaded -R forward: backend -> jump -> client
        
        When backend opens a forwarded channel to us (because someone connected
        to backend:port), we forward it directly to client via forwarded-tcpip.
        
        Works in both TPROXY and NAT modes.
        """
        try:
            logger.info("Cascaded reverse forward handler started")
            
            while backend_transport.is_active() and client_transport.is_active():
                try:
                    # Accept channel from backend
                    backend_channel = backend_transport.accept(timeout=1.0)
                    
                    if backend_channel is None:
                        continue
                    
                    logger.info(f"Got cascaded -R channel from backend")
                    
                    # Get port info
                    if hasattr(server_handler, 'remote_forward_listeners') and len(server_handler.remote_forward_listeners) > 0:
                        # Get port from first listener entry
                        _, backend_port, _ = server_handler.remote_forward_listeners[0]
                        
                        # Forward directly to client via SSH channel
                        try:
                            client_channel = client_transport.open_channel(
                                'forwarded-tcpip',
                                ('localhost', backend_port),  # Destination on client side
                                ('127.0.0.1', 0)  # Originator (unknown in cascade)
                            )
                            
                            logger.info(f"Opened forwarded-tcpip to client for port {backend_port}")
                            
                            # Forward data bidirectionally between backend and client channels
                            def forward_channels(backend_chan, client_chan):
                                try:
                                    while True:
                                        r, _, _ = select.select([backend_chan, client_chan], [], [], 1.0)
                                        
                                        if backend_chan in r:
                                            data = backend_chan.recv(4096)
                                            if len(data) == 0:
                                                break
                                            client_chan.send(data)
                                        
                                        if client_chan in r:
                                            data = client_chan.recv(4096)
                                            if len(data) == 0:
                                                break
                                            backend_chan.send(data)
                                except Exception as e:
                                    logger.debug(f"Channel forward ended: {e}")
                                finally:
                                    try:
                                        client_chan.close()
                                    except:
                                        pass
                                    try:
                                        backend_chan.close()
                                    except:
                                        pass
                            
                            forward_thread = threading.Thread(
                                target=forward_channels,
                                args=(backend_channel, client_channel),
                                daemon=True
                            )
                            forward_thread.start()
                            
                        except Exception as e:
                            logger.error(f"Failed to open channel to client: {e}")
                            backend_channel.close()
                    else:
                        logger.error("No remote forward listeners stored")
                        backend_channel.close()
                    
                except Exception as e:
                    if "timeout" not in str(e).lower():
                        logger.error(f"Cascade accept error: {e}")
            
            logger.info("Cascaded reverse forward handler exiting")
            
        except Exception as e:
            logger.error(f"Cascaded reverse forward error: {e}", exc_info=True)
    
    def handle_reverse_forward_on_backend_ip(self, client_transport, backend_ip, address, port):
        """Open socket listener on backend's IP address from pool
        
        For -R 9090:localhost:8080:
        - Client sends -R request
        - We open socket on backend_ip:9090 (e.g. 10.0.160.4:9090)
        - Backend connects to localhost:9090 (which resolves to 10.0.160.4:9090 via routing)
        - We forward connection to client via SSH
        - Client connects to its localhost:8080
        
        Args:
            client_transport: SSH transport to client
            backend_ip: IP address from pool assigned to this backend
            address: Bind address (usually '' or 'localhost')
            port: Port to bind
        """
        import socket
        
        try:
            # Create listening socket on backend's IP
            listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Bind to backend IP (from pool) so backend can connect to it
            listen_sock.bind((backend_ip, port))
            listen_sock.listen(5)
            listen_sock.settimeout(1.0)
            
            logger.info(f"Listening on backend IP {backend_ip}:{port} for -R forward to client")
            
            # Accept connections while client is connected
            while client_transport.is_active():
                try:
                    conn, conn_addr = listen_sock.accept()
                    logger.info(f"Reverse forward connection from {conn_addr} to {backend_ip}:{port}")
                    
                    # Open channel to client - use direct-tcpip instead of forwarded-tcpip
                    # Client will connect to localhost:port
                    try:
                        # direct-tcpip: tell client to connect to destination
                        client_chan = client_transport.open_channel(
                            'direct-tcpip',
                            ('localhost', port),  # Destination on client
                            conn_addr  # Our address (source)
                        )
                        
                        logger.info(f"Opened direct-tcpip channel to client localhost:{port}, forwarding data")
                        
                        # Forward data between socket and SSH channel
                        def forward_socket_to_channel(sock, chan):
                            try:
                                while True:
                                    r, _, _ = select.select([sock, chan], [], [], 1.0)
                                    
                                    if sock in r:
                                        data = sock.recv(4096)
                                        if len(data) == 0:
                                            break
                                        chan.send(data)
                                    
                                    if chan in r:
                                        data = chan.recv(4096)
                                        if len(data) == 0:
                                            break
                                        sock.send(data)
                            except Exception as e:
                                logger.debug(f"Forward ended: {e}")
                            finally:
                                try:
                                    sock.close()
                                except:
                                    pass
                                try:
                                    chan.close()
                                except:
                                    pass
                        
                        forward_thread = threading.Thread(
                            target=forward_socket_to_channel,
                            args=(conn, client_chan),
                            daemon=True
                        )
                        forward_thread.start()
                        
                    except Exception as e:
                        logger.error(f"Failed to open channel to client: {e}")
                        conn.close()
                        
                except socket.timeout:
                    continue
                except Exception as e:
                    if client_transport.is_active():
                        logger.error(f"Accept error on {backend_ip}:{port}: {e}")
                    break
            
            logger.info(f"Reverse forward listener on {backend_ip}:{port} exiting")
            listen_sock.close()
            
        except Exception as e:
            logger.error(f"Reverse forward listener error on {backend_ip}:{port}: {e}", exc_info=True)
    
    def handle_backend_socket_forward(self, client_transport, backend_ip, address, port):
        """Open a socket listener on backend via SSH and forward to client
        
        This is a workaround for -R through proxy. We can't use SSH -R to backend
        because client doesn't know to accept the forwarded-tcpip channels.
        
        Instead, we:
        1. SSH to backend and run: nc -l -p 9090
        2. Accept connections  
        3. Forward each connection to client via forwarded-tcpip
        
        Actually, simpler: use SSH dynamic forward to create a listening port
        """
        import socket
        import paramiko
        
        try:
            # Connect to backend via SSH and open a remote tunnel
            logger.info(f"Opening socket listener on backend {backend_ip}:{port}")
            
            # Create SSH connection to backend
            backend_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            backend_sock.connect((backend_ip, 22))
            
            backend_trans = paramiko.Transport(backend_sock)
            backend_trans.start_client()
            
            # TODO: We need credentials here... this won't work without them
            # This approach is too complex
            
            logger.error("Backend socket forward not yet fully implemented")
            backend_trans.close()
            
        except Exception as e:
            logger.error(f"Backend socket forward error: {e}", exc_info=True)
    
    def handle_reverse_forwarding_v2(self, client_transport, backend_transport, server_handler):
        """Accept forwarded connections from backend and forward to client
        
        For -R 9090:localhost:8080:
        - Backend has port 9090 open
        - When someone connects, backend opens channel to us
        - We accept it and connect via socket to client's localhost:8080
        """
        try:
            logger.info("Reverse forwarding v2 handler started")
            
            # Build port mapping: we need to know which backend port maps to which client destination
            port_map = {}
            if hasattr(server_handler, 'remote_forward_requests'):
                for dest_addr, dest_port in server_handler.remote_forward_requests:
                    # For -R 9090:localhost:8080, backend port 9090 -> client localhost:8080
                    port_map[dest_port] = (dest_addr if dest_addr else 'localhost', dest_port)
                    logger.info(f"Port mapping: backend {dest_port} -> client {dest_addr}:{dest_port}")
            
            while backend_transport.is_active() and client_transport.is_active():
                try:
                    # Accept channel from backend
                    backend_channel = backend_transport.accept(timeout=1.0)
                    
                    if backend_channel is None:
                        continue
                    
                    # Get origin info from channel
                    origin = getattr(backend_channel, 'origin_addr', ('unknown', 0))
                    logger.info(f"Got reverse forward channel from backend, origin={origin}")
                    
                    # For now, if we only have one mapping, use it
                    if len(port_map) == 1:
                        dest_addr, dest_port = list(port_map.values())[0]
                        server_port = list(port_map.keys())[0]
                        logger.info(f"Forwarding to client {dest_addr}:{dest_port} (from backend port {server_port})")
                        
                        # Open forwarded-tcpip channel to client
                        # Parameters according to paramiko docs:
                        # - src_addr: (src_addr, src_port) of the incoming connection (origin)
                        # - dest_addr: (dest_addr, dest_port) of the forwarded server
                        try:
                            client_channel = client_transport.open_forwarded_tcpip_channel(
                                origin,  # Source: who connected to backend
                                ('', server_port)  # Dest: where backend was listening
                            )
                            
                            logger.info(f"Opened forwarded-tcpip channel to client, forwarding data")
                            
                            # Forward data
                            forward_thread = threading.Thread(
                                target=self.forward_port_channel,
                                args=(backend_channel, client_channel, dest_addr, dest_port),
                                daemon=True
                            )
                            forward_thread.start()
                            
                        except Exception as e:
                            logger.error(f"Failed to open channel to client: {e}")
                            backend_channel.close()
                    else:
                        logger.error(f"Multiple port mappings not yet supported: {port_map}")
                        backend_channel.close()
                    
                except Exception as e:
                    if "timeout" not in str(e).lower():
                        logger.error(f"Reverse accept error: {e}")
            
            logger.info("Reverse forwarding v2 handler exiting")
            
        except Exception as e:
            logger.error(f"Reverse forwarding v2 error: {e}", exc_info=True)
    
    def handle_reverse_forward_listener(self, client_transport, address, port, dest_addr, dest_port):
        """Listen on a port and forward connections to SSH client
        
        This implements the server side of SSH -R (remote forward).
        We open a socket, listen for connections, and for each connection
        we open a forwarded-tcpip channel to the client.
        
        Args:
            client_transport: SSH transport to client
            address: Address to bind ('', 'localhost', etc)
            port: Port to bind
            dest_addr: Destination address on client side (e.g. 'localhost')
            dest_port: Destination port on client side (e.g. 8080)
        """
        import socket
        
        try:
            # Create listening socket
            listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            bind_addr = '0.0.0.0' if address == '' else address
            listen_sock.bind((bind_addr, port))
            listen_sock.listen(5)
            listen_sock.settimeout(1.0)  # Timeout for accept
            
            logger.info(f"Listening for reverse forward on {bind_addr}:{port} -> client {dest_addr}:{dest_port}")
            
            # Accept connections while client is connected
            while client_transport.is_active():
                try:
                    conn, conn_addr = listen_sock.accept()
                    logger.info(f"Reverse forward connection from {conn_addr}")
                    
                    # Open forwarded-tcpip channel to client
                    # Client will connect to dest_addr:dest_port locally
                    try:
                        # Use direct method to open channel
                        client_chan = client_transport.open_channel(
                            'forwarded-tcpip',
                            (dest_addr, dest_port),
                            conn_addr
                        )
                        
                        logger.info(f"Opened forwarded-tcpip to client for {dest_addr}:{dest_port}")
                        
                        # Forward data in background thread
                        def forward_socket_to_channel(sock, chan):
                            try:
                                while True:
                                    r, _, _ = select.select([sock, chan], [], [], 1.0)
                                    
                                    if sock in r:
                                        data = sock.recv(4096)
                                        if len(data) == 0:
                                            break
                                        chan.send(data)
                                    
                                    if chan in r:
                                        data = chan.recv(4096)
                                        if len(data) == 0:
                                            break
                                        sock.send(data)
                            except:
                                pass
                            finally:
                                sock.close()
                                chan.close()
                        
                        forward_thread = threading.Thread(
                            target=forward_socket_to_channel,
                            args=(conn, client_chan),
                            daemon=True
                        )
                        forward_thread.start()
                        
                    except Exception as e:
                        logger.error(f"Failed to open channel to client: {e}")
                        conn.close()
                        
                except socket.timeout:
                    continue
                except Exception as e:
                    if client_transport.is_active():
                        logger.error(f"Accept error: {e}")
                    break
            
            logger.info(f"Reverse forward listener on port {port} exiting")
            listen_sock.close()
            
        except Exception as e:
            logger.error(f"Reverse forward listener error: {e}", exc_info=True)
    
    def update_terminal_title(self, channel, server_name, grant_remaining_minutes=None, 
                              idle_current_minutes=None, idle_max_minutes=None, is_warning=False):
        """Update terminal window title with countdown timers (non-intrusive monitoring).
        
        Uses ANSI OSC 2 escape sequence to set window title. Works in most terminals:
        xterm, gnome-terminal, konsole, iTerm2, Windows Terminal, PuTTY.
        
        Args:
            channel: SSH channel to send title update
            server_name: Target server name (truncated if >20 chars)
            grant_remaining_minutes: Minutes until grant expires (None for permanent)
            idle_current_minutes: Current idle time in minutes
            idle_max_minutes: Max idle timeout (None/0 for disabled)
            is_warning: Add [!] suffix if warning condition
        """
        try:
            # Truncate long server names
            if len(server_name) > 20:
                server_name = server_name[:17] + "..."
            
            parts = [f"Inside: {server_name}"]
            
            # Add grant countdown if applicable
            if grant_remaining_minutes is not None:
                if grant_remaining_minutes >= 60:
                    hours = grant_remaining_minutes // 60
                    mins = grant_remaining_minutes % 60
                    parts.append(f"Grant: {hours}h{mins}m")
                else:
                    parts.append(f"Grant: {grant_remaining_minutes}m")
            
            # Add idle timeout if enabled
            if idle_max_minutes and idle_max_minutes > 0:
                parts.append(f"Idle: {idle_current_minutes}/{idle_max_minutes}m")
            
            # Build title
            title = " | ".join(parts)
            if is_warning:
                title += " [!]"
            
            # Send ANSI escape sequence: OSC 2 ; title BEL
            # \033]2; = OSC 2 (set window title)
            # \007 = BEL (bell terminator)
            channel.send(f"\033]2;{title}\007".encode())
            
        except Exception as e:
            # Silently ignore errors (channel might be closed, terminal might not support)
            pass
    
    def clear_terminal_title(self, channel, server_name):
        """Clear terminal title and show 'disconnected' status.
        
        Called when session ends (grant expiry, idle timeout, user logout, etc.)
        """
        try:
            if len(server_name) > 20:
                server_name = server_name[:17] + "..."
            
            title = f"Inside: {server_name} | disconnected"
            channel.send(f"\033]2;{title}\007".encode())
        except:
            pass
    
    def monitor_inactivity_timeout(self, channel, backend_channel, transport, backend_transport,
                                    inactivity_timeout_minutes, db_session_id, session_id, server_name="unknown"):
        """Monitor session inactivity and disconnect after configured timeout.
        
        Args:
            channel: Client channel
            backend_channel: Backend channel
            transport: Client transport
            backend_transport: Backend transport
            inactivity_timeout_minutes: Timeout in minutes (0 or None = disabled)
            db_session_id: Database session ID for termination reason
            session_id: Session ID for tracking
        """
        try:
            # Disabled or invalid timeout
            if not inactivity_timeout_minutes or inactivity_timeout_minutes <= 0:
                logger.debug(f"Session {session_id}: Inactivity timeout disabled")
                return
            
            logger.info(f"Session {session_id}: Monitoring inactivity timeout ({inactivity_timeout_minutes} minutes)")
            
            # Initialize last activity timestamp
            if session_id not in self.session_last_activity:
                self.session_last_activity[session_id] = datetime.utcnow()
            
            # Convert timeout to seconds
            timeout_seconds = inactivity_timeout_minutes * 60
            warning_5min = 300  # 5 minutes in seconds
            warning_1min = 60   # 1 minute in seconds
            
            sent_5min_warning = False
            sent_1min_warning = False
            
            last_title_update = 0  # Track last title update time
            while True:
                time.sleep(10)  # Check every 10 seconds
                
                # Check if session is still active
                if not transport.is_active() or not backend_transport.is_active():
                    logger.debug(f"Session {session_id}: Session disconnected, stopping inactivity monitor")
                    return
                
                # Get last activity time
                last_activity = self.session_last_activity.get(session_id)
                if not last_activity:
                    logger.warning(f"Session {session_id}: No last activity timestamp found")
                    return
                
                # Calculate idle time
                now = datetime.utcnow()
                idle_seconds = (now - last_activity).total_seconds()
                remaining_seconds = timeout_seconds - idle_seconds
                
                # Update terminal title periodically (this monitor runs every 10s, so it's the main title updater)
                # Frequency: 60s normally, 10s when idle >50 min OR grant <10 min
                current_time = time.time()
                idle_minutes = int(idle_seconds / 60)
                
                # Get grant info from metadata
                grant_remaining_minutes = None
                is_warning = False
                metadata = self.session_metadata.get(session_id, {})
                grant_end_time = metadata.get('grant_end_time')
                if grant_end_time:
                    grant_remaining = (grant_end_time - now).total_seconds()
                    grant_remaining_minutes = int(grant_remaining / 60)
                    if grant_remaining < 300:  # <5 min
                        is_warning = True
                
                # Check if we should update title (faster when warning)
                if remaining_seconds < 300:  # Idle timeout warning
                    is_warning = True
                
                update_interval = 10 if (is_warning or idle_minutes >= (inactivity_timeout_minutes - 10)) else 60
                
                if current_time - last_title_update >= update_interval:
                    self.update_terminal_title(
                        channel=channel,
                        server_name=server_name,
                        grant_remaining_minutes=grant_remaining_minutes,
                        idle_current_minutes=idle_minutes,
                        idle_max_minutes=inactivity_timeout_minutes,
                        is_warning=is_warning
                    )
                    last_title_update = current_time
                
                # Check if timeout reached
                if remaining_seconds <= 0:
                    logger.info(f"Session {session_id}: Inactivity timeout reached ({inactivity_timeout_minutes} min)")
                    
                    # Clear terminal title
                    self.clear_terminal_title(channel, server_name)
                    
                    # Send disconnect message
                    try:
                        message = (
                            f"\r\n\r\n"
                            f"{'='*70}\r\n"
                            f"  Session disconnected due to inactivity\r\n"
                            f"  No activity detected for {inactivity_timeout_minutes} minutes\r\n"
                            f"{'='*70}\r\n\r\n"
                        )
                        channel.send(message.encode())
                        time.sleep(0.5)  # Give time for message to be delivered
                    except Exception as e:
                        logger.error(f"Session {session_id}: Failed to send disconnect message: {e}")
                    
                    # Close connection
                    try:
                        channel.close()
                        backend_channel.close()
                    except:
                        pass
                    
                    # Mark termination in database
                    if db_session_id:
                        try:
                            self.tower_client.update_session(
                                session_id=db_session_id,
                                is_active=False,
                                ended_at=datetime.utcnow().isoformat(),
                                termination_reason='inactivity_timeout'
                            )
                        except Exception as e:
                            logger.error(f"Session {session_id}: Failed to update termination reason: {e}")
                    
                    # Remove from tracking
                    if session_id in self.session_last_activity:
                        del self.session_last_activity[session_id]
                    if session_id in self.session_metadata:
                        del self.session_metadata[session_id]
                    
                    return
                
                # Send warnings (only for shell sessions with channel)
                if remaining_seconds <= warning_5min and not sent_5min_warning:
                    try:
                        mins_remaining = int(remaining_seconds / 60)
                        message = (
                            f"\r\n\r\n"
                            f"{'='*70}\r\n"
                            f"  *** WARNING: Inactivity detected ***\r\n"
                            f"  No activity for {int(idle_seconds / 60)} minutes\r\n"
                            f"  Session will disconnect in {mins_remaining} minute(s)\r\n"
                            f"  Press any key to continue working\r\n"
                            f"{'='*70}\r\n\r\n"
                        )
                        channel.send(message.encode())
                        sent_5min_warning = True
                        logger.info(f"Session {session_id}: Sent 5-minute inactivity warning")
                    except Exception as e:
                        logger.error(f"Session {session_id}: Failed to send 5-minute warning: {e}")
                
                if remaining_seconds <= warning_1min and not sent_1min_warning:
                    try:
                        message = (
                            f"\r\n\r\n"
                            f"{'='*70}\r\n"
                            f"  *** WARNING: Session disconnecting in 1 minute ***\r\n"
                            f"  No activity detected - press any key to continue\r\n"
                            f"{'='*70}\r\n\r\n"
                        )
                        channel.send(message.encode())
                        sent_1min_warning = True
                        logger.info(f"Session {session_id}: Sent 1-minute inactivity warning")
                    except Exception as e:
                        logger.error(f"Session {session_id}: Failed to send 1-minute warning: {e}")
                        
        except Exception as e:
            logger.error(f"Session {session_id}: Error in inactivity monitor: {e}")
    
    def monitor_grant_expiry(self, channel, backend_channel, transport, backend_transport, 
                             grant_end_time, db_session_id, session_id, server_name="unknown"):
        """Monitor grant expiry and send warnings, then disconnect when grant expires.
        
        Also checks for forced disconnection times injected by heartbeat.
        For permanent grants (grant_end_time=None), only monitors for forced disconnection.
        Updates terminal title with countdown timer.
        
        Args:
            server_name: Target server name for terminal title display
        """
        try:
            # Check if there's a forced disconnection time (from heartbeat)
            if session_id in self.session_forced_endtimes:
                forced_end = self.session_forced_endtimes[session_id]
                # Use the earlier time between grant expiry and forced disconnect
                if grant_end_time is None or forced_end < grant_end_time:
                    logger.info(f"Session {session_id}: Using forced disconnect time {forced_end}")
                    grant_end_time = forced_end
            
            # Permanent grant - only check for forced disconnection every 30 seconds
            if grant_end_time is None:
                logger.debug(f"Session {session_id}: Permanent grant, monitoring for revocation only")
                while True:
                    time.sleep(30)
                    # Check if session is still active
                    if not transport.is_active() or not backend_transport.is_active():
                        logger.info(f"Session {session_id}: Disconnected normally")
                        return
                    
                    # Check if forced disconnect was injected (grant revoked)
                    if session_id in self.session_forced_endtimes:
                        forced_end = self.session_forced_endtimes[session_id]
                        now = datetime.utcnow()
                        if forced_end <= now:
                            logger.info(f"Session {session_id}: Grant revoked, terminating immediately")
                            grant_end_time = forced_end
                            break
                        else:
                            grant_end_time = forced_end
                            logger.info(f"Session {session_id}: Grant revoked, will disconnect at {forced_end}")
                            break
            
            # Main monitoring loop - restarts if grant is extended
            while True:
                now = datetime.utcnow()
                remaining = (grant_end_time - now).total_seconds()
                
                logger.debug(f"Session {session_id}: Grant expires in {remaining/60:.1f} minutes ({grant_end_time})")
                
                # Store grant end time in metadata for inactivity monitor to use in title
                if session_id in self.session_metadata:
                    self.session_metadata[session_id]['grant_end_time'] = grant_end_time
                
                # Warning times (in seconds before expiry)
                warnings = [
                    (300, "5 minutes"),  # 5 minutes
                    (60, "1 minute"),    # 1 minute
                ]
                
                grant_extended_during_warning = False
                for warning_seconds, warning_text in warnings:
                    if remaining > warning_seconds:
                        # Sleep until warning time (in small increments to check for forced disconnect)
                        sleep_time = remaining - warning_seconds
                        logger.debug(f"Session {session_id}: Sleeping {sleep_time:.0f}s until {warning_text} warning")
                        
                        # Sleep in 1-second increments to check for forced disconnect and grant extensions
                        for _ in range(int(sleep_time)):
                            time.sleep(1)
                            
                            # Check if grant was extended or shortened
                            if session_id in self.session_grant_endtimes:
                                new_end_time = self.session_grant_endtimes[session_id]
                                if new_end_time > grant_end_time:
                                    # Grant extended!
                                    logger.info(f"Session {session_id}: Grant extended from {grant_end_time} to {new_end_time}")
                                    
                                    # Calculate new remaining time
                                    now = datetime.utcnow()
                                    new_remaining = (new_end_time - now).total_seconds()
                                    extension_minutes = int((new_end_time - grant_end_time).total_seconds() / 60)
                                    
                                    # Convert to Europe/Warsaw for display
                                    warsaw_tz = pytz.timezone('Europe/Warsaw')
                                    new_end_local = new_end_time if new_end_time.tzinfo else pytz.utc.localize(new_end_time)
                                    new_end_local = new_end_local.astimezone(warsaw_tz)
                                    
                                    # Send notification message
                                    extension_msg = (
                                        f"\r\n\r\n"
                                        f"{'='*70}\r\n"
                                        f"  *** GOOD NEWS: Your access grant has been extended! ***\r\n"
                                        f"  New expiry time: {new_end_local.strftime('%Y-%m-%d %H:%M:%S %Z')}\r\n"
                                        f"  Extended by: {extension_minutes} minute(s)\r\n"
                                        f"{'='*70}\r\n\r\n"
                                    )
                                    try:
                                        channel.send(extension_msg.encode())
                                        logger.info(f"Session {session_id}: Sent grant extension notification")
                                    except Exception as e:
                                        logger.error(f"Session {session_id}: Failed to send extension message: {e}")
                                    
                                    # Update grant_end_time and recalculate remaining time
                                    grant_end_time = new_end_time
                                    remaining = new_remaining
                                    grant_extended_during_warning = True
                                    # Break inner loop to restart warning countdown from new end time
                                    break
                                elif new_end_time < grant_end_time:
                                    # Grant shortened!
                                    logger.info(f"Session {session_id}: Grant shortened from {grant_end_time} to {new_end_time}")
                                    
                                    # Calculate new remaining time
                                    now = datetime.utcnow()
                                    new_remaining = (new_end_time - now).total_seconds()
                                    reduction_minutes = int((grant_end_time - new_end_time).total_seconds() / 60)
                                    
                                    # Convert to Europe/Warsaw for display
                                    warsaw_tz = pytz.timezone('Europe/Warsaw')
                                    new_end_local = new_end_time if new_end_time.tzinfo else pytz.utc.localize(new_end_time)
                                    new_end_local = new_end_local.astimezone(warsaw_tz)
                                    
                                    # Send notification message
                                    shortening_msg = (
                                        f"\r\n\r\n"
                                        f"{'='*70}\r\n"
                                        f"  *** NOTICE: Your access grant has been shortened! ***\r\n"
                                        f"  New expiry time: {new_end_local.strftime('%Y-%m-%d %H:%M:%S %Z')}\r\n"
                                        f"  Reduced by: {reduction_minutes} minute(s)\r\n"
                                        f"{'='*70}\r\n\r\n"
                                    )
                                    try:
                                        channel.send(shortening_msg.encode())
                                        logger.info(f"Session {session_id}: Sent grant shortening notification")
                                    except Exception as e:
                                        logger.error(f"Session {session_id}: Failed to send shortening message: {e}")
                                    
                                    # Update grant_end_time and recalculate remaining time
                                    grant_end_time = new_end_time
                                    remaining = new_remaining
                                    grant_extended_during_warning = True
                                    # Break inner loop to restart warning countdown from new end time
                                    break
                            
                            # Check if forced disconnect was injected
                            if session_id in self.session_forced_endtimes:
                                forced_end = self.session_forced_endtimes[session_id]
                                now = datetime.utcnow()
                                if forced_end <= now:
                                    logger.info(f"Session {session_id}: Forced disconnect detected, terminating immediately")
                                    # Jump to immediate disconnect
                                    remaining = 0
                                    break
                                else:
                                    # Update grant_end_time to forced time
                                    grant_end_time = forced_end
                                    remaining = (grant_end_time - now).total_seconds()
                                    logger.info(f"Session {session_id}: Updated end_time to forced disconnect at {forced_end}")
                                    break
                            # Check if session is still active
                            if not transport.is_active() or not backend_transport.is_active():
                                logger.info(f"Session {session_id}: Already disconnected during sleep")
                                return
                        
                        # If forced disconnect caused break, skip to final disconnect
                        if remaining <= 0:
                            break
                        
                        # If grant was extended, restart from beginning of while loop
                        if grant_extended_during_warning:
                            logger.info(f"Session {session_id}: Restarting countdown due to grant extension")
                            break
                        
                        # Check if session is still active
                        if not transport.is_active() or not backend_transport.is_active():
                            logger.info(f"Session {session_id}: Already disconnected before {warning_text} warning")
                            return
                        
                        # Send wall-style warning
                        now = datetime.utcnow()
                        remaining = (grant_end_time - now).total_seconds()
                        if remaining > 0:
                            message = (
                                f"\r\n\r\n"
                                f"{'='*70}\r\n"
                                f"  *** WARNING: Your access grant expires in {warning_text} ***\r\n"
                                f"  Your session will be automatically disconnected at {grant_end_time} UTC\r\n"
                                f"{'='*70}\r\n\r\n"
                            )
                            try:
                                channel.send(message.encode())
                                logger.info(f"Session {session_id}: Sent {warning_text} warning")
                            except Exception as e:
                                logger.error(f"Session {session_id}: Failed to send warning: {e}")
                                return
                        
                        remaining = (grant_end_time - now).total_seconds()
                
                # If grant was extended during warnings, restart the while loop
                if grant_extended_during_warning:
                    continue
                
                # Sleep until expiry (in small increments to check for forced disconnect and extensions)
                grant_was_extended = False
                if remaining > 0:
                    logger.debug(f"Session {session_id}: Sleeping {remaining:.0f}s until grant expiry")
                    for _ in range(int(remaining)):
                        time.sleep(1)
                        
                        # Check if grant was extended or shortened
                        if session_id in self.session_grant_endtimes:
                            new_end_time = self.session_grant_endtimes[session_id]
                            if new_end_time > grant_end_time:
                                # Grant extended during final countdown!
                                logger.info(f"Session {session_id}: Grant extended during final countdown from {grant_end_time} to {new_end_time}")
                                
                                # Calculate new remaining time
                                now = datetime.utcnow()
                                new_remaining = (new_end_time - now).total_seconds()
                                extension_minutes = int((new_end_time - grant_end_time).total_seconds() / 60)
                                
                                # Convert to Europe/Warsaw for display
                                warsaw_tz = pytz.timezone('Europe/Warsaw')
                                new_end_local = new_end_time if new_end_time.tzinfo else pytz.utc.localize(new_end_time)
                                new_end_local = new_end_local.astimezone(warsaw_tz)
                                
                                # Send notification message
                                extension_msg = (
                                    f"\r\n\r\n"
                                    f"{'='*70}\r\n"
                                    f"  *** GOOD NEWS: Your access grant has been extended! ***\r\n"
                                    f"  New expiry time: {new_end_local.strftime('%Y-%m-%d %H:%M:%S %Z')}\r\n"
                                    f"  Extended by: {extension_minutes} minute(s)\r\n"
                                    f"{'='*70}\r\n\r\n"
                                )
                                try:
                                    channel.send(extension_msg.encode())
                                    logger.info(f"Session {session_id}: Sent grant extension notification during final countdown")
                                except Exception as e:
                                    logger.error(f"Session {session_id}: Failed to send extension message: {e}")
                                
                                # Update grant_end_time and set flag to restart countdown
                                grant_end_time = new_end_time
                                remaining = new_remaining
                                grant_was_extended = True
                                logger.info(f"Session {session_id}: Will restart countdown with new end time")
                                break
                            elif new_end_time < grant_end_time:
                                # Grant shortened during final countdown!
                                logger.info(f"Session {session_id}: Grant shortened during final countdown from {grant_end_time} to {new_end_time}")
                                
                                # Calculate new remaining time
                                now = datetime.utcnow()
                                new_remaining = (new_end_time - now).total_seconds()
                                reduction_minutes = int((grant_end_time - new_end_time).total_seconds() / 60)
                                
                                # Convert to Europe/Warsaw for display
                                warsaw_tz = pytz.timezone('Europe/Warsaw')
                                new_end_local = new_end_time if new_end_time.tzinfo else pytz.utc.localize(new_end_time)
                                new_end_local = new_end_local.astimezone(warsaw_tz)
                                
                                # Send notification message
                                shortening_msg = (
                                    f"\r\n\r\n"
                                    f"{'='*70}\r\n"
                                    f"  *** NOTICE: Your access grant has been shortened! ***\r\n"
                                    f"  New expiry time: {new_end_local.strftime('%Y-%m-%d %H:%M:%S %Z')}\r\n"
                                    f"  Reduced by: {reduction_minutes} minute(s)\r\n"
                                    f"{'='*70}\r\n\r\n"
                                )
                                try:
                                    channel.send(shortening_msg.encode())
                                    logger.info(f"Session {session_id}: Sent grant shortening notification during final countdown")
                                except Exception as e:
                                    logger.error(f"Session {session_id}: Failed to send shortening message: {e}")
                                
                                # Update grant_end_time and set flag to restart countdown
                                grant_end_time = new_end_time
                                remaining = new_remaining
                                grant_was_extended = True
                                logger.info(f"Session {session_id}: Will restart countdown with new end time")
                                break
                        
                        # Check if forced disconnect was injected
                        if session_id in self.session_forced_endtimes:
                            forced_end = self.session_forced_endtimes[session_id]
                            now = datetime.utcnow()
                            if forced_end <= now:
                                logger.info(f"Session {session_id}: Forced disconnect detected during final countdown")
                                break
                        # Check if session is still active
                        if not transport.is_active() or not backend_transport.is_active():
                            logger.info(f"Session {session_id}: Already disconnected during final countdown")
                            return
                
                # If grant was extended, restart the warning loop
                if grant_was_extended:
                    continue
                    
                # Break out of while loop - time to disconnect
                break
            
            # Check if session is still active
            if not transport.is_active() or not backend_transport.is_active():
                logger.info(f"Session {session_id}: Already disconnected before grant expiry")
                return
            
            # Determine disconnect reason
            disconnect_reason = "Your access grant has expired"
            termination_reason = 'grant_expired'
            
            # Check if forced termination reason exists
            if session_id in self.session_forced_endtimes:
                # Tower API would have set termination_reason via update_session
                # Default messages for common reasons
                termination_reason = 'gate_maintenance'  # Will be overridden by Tower API if different
                disconnect_reason = "Session terminated by administrator"
                
                # Clean up forced endtime
                del self.session_forced_endtimes[session_id]
            
            # Clear terminal title before disconnect
            self.clear_terminal_title(channel, server_name)
            
            # Send final disconnection message
            final_message = (
                f"\r\n\r\n"
                f"{'='*70}\r\n"
                f"  *** {disconnect_reason} ***\r\n"
                f"  Disconnecting now...\r\n"
                f"{'='*70}\r\n\r\n"
            )
            try:
                channel.send(final_message.encode())
                time.sleep(1)  # Give time for message to be sent
            except:
                pass
            
            logger.info(f"Session {session_id}: Grant expired, closing connection")
            
            # Close channels and transports
            try:
                backend_channel.close()
            except:
                pass
            
            try:
                channel.close()
            except:
                pass
            
            try:
                backend_transport.close()
            except:
                pass
            
            try:
                transport.close()
            except:
                pass
            
            # Update session via Tower API
            try:
                tower_client = TowerClient(GateConfig())
                tower_client.update_session(
                    session_id=session_id,
                    ended_at=datetime.utcnow().isoformat(),
                    is_active=False,
                    termination_reason=termination_reason
                )
                logger.info(f"Session {session_id}: Updated via Tower API with termination_reason='{termination_reason}'")
            except Exception as e:
                logger.error(f"Session {session_id}: Failed to update via Tower API: {e}")
                
        except Exception as e:
            logger.error(f"Session {session_id}: Error in grant expiry monitor: {e}", exc_info=True)
    
    def log_scp_transfer(self, db_session_id, command, direction):
        """Log SCP file transfer to logger only (Tower API tracks via session recording)"""
        try:
            # Parse SCP command: scp [-r] [-t|-f] [file]
            # -t = to (upload), -f = from (download)
            import re
            
            # Extract file path from command
            match = re.search(r'scp\s+(?:-\w+\s+)*([^\s]+)', command)
            if not match:
                return
            
            file_path = match.group(1)
            logger.info(f"SCP {direction}: {file_path} (session: {db_session_id})")
        except Exception as e:
            logger.error(f"Failed to parse SCP command: {e}")
    
    def log_sftp_transfer(self, db_session_id):
        """Log SFTP transfer session to logger only (Tower API tracks via session recording)"""
        logger.info(f"SFTP session started (session: {db_session_id})")
        return None  # No transfer_id needed anymore
    
    def log_port_forward(self, db_session_id, forward_type, local_addr, local_port, remote_addr, remote_port):
        """Log port forwarding channel to logger only (Tower API tracks via session recording)"""
        logger.info(f"{forward_type}: {local_addr}:{local_port} -> {remote_addr}:{remote_port} (session: {db_session_id})")
        return None  # No transfer_id needed anymore
    
    def log_socks_connection(self, db_session_id, remote_addr, remote_port):
        """Log SOCKS proxy connection to logger only (Tower API tracks via session recording)"""
        logger.info(f"SOCKS connection: {remote_addr}:{remote_port} (session: {db_session_id})")
        return None  # No transfer_id needed anymore
    
    def update_transfer_stats(self, transfer_id, bytes_sent, bytes_received):
        """Update transfer statistics (no-op, Tower API tracks via session recording)"""
        pass  # Transfer stats tracked by Tower API via session recording
    
    def handle_client(self, client_socket, client_addr, is_tproxy=False):
        """Handle incoming client connection"""
        source_ip = client_addr[0]
        
        # Extract destination IP (the IP client connected to)
        if is_tproxy:
            # TPROXY mode: Extract original destination from SO_ORIGINAL_DST
            original_dst = self.get_original_dst(client_socket)
            if original_dst:
                dest_ip, dest_port = original_dst
                logger.info(f"TPROXY connection from {source_ip} to {dest_ip}:{dest_port}")
            else:
                logger.error(f"TPROXY: Failed to extract original destination for {source_ip}")
                client_socket.close()
                return
        else:
            # NAT mode: Use the IP we're bound to (pool IP)
            dest_ip = client_socket.getsockname()[0]
            logger.info(f"NAT connection from {source_ip} to {dest_ip}")
        
        session_id = f"{source_ip}_{datetime.now().timestamp()}"
        
        logger.info(f"New connection from {source_ip} to {dest_ip}")
        
        backend_transport = None
        
        try:
            # Setup SSH transport for client
            transport = paramiko.Transport(client_socket)
            transport.add_server_key(self.host_key)
            
            # Create server handler with source and dest IPs
            server_handler = SSHProxyHandler(source_ip, dest_ip)
            server_handler.is_tproxy = is_tproxy  # Mark as TPROXY connection
            transport.start_server(server=server_handler)
            
            # Wait for authentication
            channel = transport.accept(20)
            if channel is None:
                logger.warning(f"No channel opened from {source_ip}")
                # If no_grant_reason is set, send disconnect message with reason
                if server_handler.no_grant_reason:
                    logger.info(f"Connection rejected due to no grant: {server_handler.no_grant_reason}")
                    # Send disconnect message to client (will be visible in SSH output)
                    try:
                        transport.send_disconnect(
                            code=paramiko.AUTH_FAILED,
                            message=server_handler.no_grant_reason
                        )
                    except:
                        pass  # Transport might already be closed
                return
            
            # Get authenticated user and target server
            if not server_handler.authenticated_user or not server_handler.target_server:
                logger.error("Authentication failed or no target server")
                channel.close()
                return
            
            user = server_handler.authenticated_user
            target_server = server_handler.target_server
            
            # Connect to backend server via SSH
            logger.debug(f"Connecting to backend: {target_server.ip_address}:22")
            backend_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            backend_socket.connect((target_server.ip_address, 22))
            
            backend_transport = paramiko.Transport(backend_socket)
            backend_transport.start_client()
            
            # Note: Agent will be created when needed (after channel requests are processed)
            
            # Authenticate to backend using client credentials
            try:
                authenticated = False
                
                # If client used pubkey, REQUIRE agent forwarding
                if server_handler.client_key:
                    # Wait up to 1 second for agent channel (race condition: sometimes client sends
                    # session request before agent forwarding request)
                    if not server_handler.agent_channel:
                        logger.debug("Waiting for agent channel (race condition mitigation)...")
                        import time
                        for i in range(10):  # 10 x 100ms = 1 second max
                            time.sleep(0.1)
                            if server_handler.agent_channel:
                                logger.debug(f"Agent channel arrived after {(i+1)*100}ms")
                                break
                    
                    if not server_handler.agent_channel:
                        # No agent forwarding after timeout - show hint
                        logger.info("Pubkey but no agent forwarding")
                        channel.send(f"ERROR: Public key authentication requires agent forwarding.\r\n".encode())
                        channel.send(f"Try: ssh -A {server_handler.ssh_login}@{server_handler.dest_ip}\r\n".encode())
                        channel.send(f"Or:  ssh -o PubkeyAuthentication=no {server_handler.ssh_login}@{server_handler.dest_ip}\r\n".encode())
                        channel.close()
                        return
                    
                    # Try agent forwarding
                    logger.debug("Using forwarded agent for backend")
                    try:
                        from paramiko.agent import AgentServerProxy
                        agent = AgentServerProxy(transport)
                        agent.connect()
                        agent_keys = agent.get_keys()
                        logger.debug(f"Got {len(agent_keys)} keys from agent")
                        
                        for key in agent_keys:
                            try:
                                backend_transport.auth_publickey(server_handler.ssh_login, key)
                                logger.debug(f"Backend auth with agent succeeded")
                                authenticated = True
                                break
                            except Exception as e:
                                logger.debug(f"Agent key failed: {e}")
                                continue
                        
                        if not authenticated:
                            # No agent keys worked
                            logger.info("No agent keys worked")
                            channel.send(f"ERROR: None of your SSH keys are authorized on the backend server.\r\n".encode())
                            channel.send(f"Try: ssh -o PubkeyAuthentication=no {server_handler.ssh_login}@{server_handler.dest_ip}\r\n".encode())
                            channel.close()
                            return
                    except Exception as e:
                        logger.info(f"Agent error: {e}")
                        channel.send(f"ERROR: Agent forwarding failed: {e}\r\n".encode())
                        channel.send(f"Try: ssh -o PubkeyAuthentication=no {server_handler.ssh_login}@{server_handler.dest_ip}\r\n".encode())
                        channel.close()
                        return
                
                # If client used password, use it
                elif server_handler.client_password:
                    try:
                        backend_transport.auth_password(server_handler.ssh_login, server_handler.client_password)
                        logger.info(f"Backend auth with password succeeded")
                        authenticated = True
                    except Exception as e:
                        logger.error(f"Backend password auth failed: {e}")
                        channel.send(b"ERROR: Password failed on backend.\r\n")
                        channel.close()
                        return
                
                # If client used keyboard-interactive (switches, telnet-like devices)
                elif hasattr(server_handler, 'client_interactive') and server_handler.client_interactive:
                    try:
                        # For keyboard-interactive, switches often don't use SSH auth at all
                        # They expect raw connection and send prompts in the session itself (like telnet)
                        # Try auth_none first - some switches accept this
                        logger.info("Using keyboard-interactive for backend (switch/telnet-like)")
                        try:
                            backend_transport.auth_none(server_handler.ssh_login)
                            logger.info(f"Backend accepted auth_none (switch mode)")
                            authenticated = True
                        except paramiko.BadAuthenticationType as e:
                            # If switch doesn't accept auth_none, try interactive_dumb
                            logger.info(f"Backend rejected auth_none, trying interactive_dumb: {e}")
                            backend_transport.auth_interactive_dumb(server_handler.ssh_login)
                            logger.info(f"Backend auth with keyboard-interactive succeeded")
                            authenticated = True
                    except Exception as e:
                        logger.error(f"Backend keyboard-interactive auth failed: {e}")
                        channel.send(b"ERROR: Interactive authentication failed on backend.\r\n")
                        channel.close()
                        return
                
                else:
                    logger.error("No authentication method available for backend")
                    channel.close()
                    return
                    
            except Exception as e:
                logger.error(f"Backend auth error: {e}")
                channel.send(b"ERROR: Backend authentication error\r\n")
                channel.close()
                return
            
            # For -R (remote forward): Backend channels forwarded directly to client
            # 
            # Flow: Backend:port -> SSH channel to gate -> SSH channel to client
            # Works in both TPROXY and NAT modes
            if hasattr(server_handler, 'remote_forward_requests'):
                server_handler.remote_forward_listeners = []  # Track ports for cascade handler
                
                for address, port in server_handler.remote_forward_requests:
                    # Track port for cascade handler (always use direct mode)
                    server_handler.remote_forward_listeners.append(('direct', port, port))
                    
                    # Ask backend to create listener - backend will open channels to us
                    try:
                        bound_port = backend_transport.request_port_forward('', port)
                        logger.info(f"Cascaded -R: backend:{port} -> gate SSH channel -> client")
                    except Exception as e:
                        logger.error(f"Failed to setup cascaded -R for port {port}: {e}")
            
            # Open backend channel
            backend_channel = backend_transport.open_session()
            
            # Start port forwarding handler in background thread
            # This will handle any -L/-R/-D requests from client
            forward_thread = threading.Thread(
                target=self.handle_port_forwarding,
                args=(transport, backend_transport, server_handler, user, target_server),
                daemon=True
            )
            forward_thread.start()
            logger.debug("Port forwarding handler started")
            
            # For cascaded -R, accept channels from backend and forward to client
            if hasattr(server_handler, 'remote_forward_requests'):
                # Store listener addresses for cascade handler
                if not hasattr(server_handler, 'remote_forward_listeners'):
                    server_handler.remote_forward_listeners = []
                    
                cascade_thread = threading.Thread(
                    target=self.handle_cascaded_reverse_forward,
                    args=(transport, backend_transport, server_handler),
                    daemon=True
                )
                cascade_thread.start()
                logger.info("Cascaded reverse forward handler started")
            
            # Setup PTY if client requested it (for interactive sessions)
            if server_handler.pty_term:
                logger.debug(f"Setting backend PTY: {server_handler.pty_term} {server_handler.pty_width}x{server_handler.pty_height}")
                # Decode term if it's bytes
                term = server_handler.pty_term.decode('utf-8') if isinstance(server_handler.pty_term, bytes) else server_handler.pty_term
                backend_channel.get_pty(
                    term=term,
                    width=server_handler.pty_width,
                    height=server_handler.pty_height
                )
            
            # Invoke shell, exec command, or subsystem based on client request
            if server_handler.channel_type == 'exec' and server_handler.exec_command:
                # For SCP and other exec commands
                cmd_str = server_handler.exec_command.decode('utf-8') if isinstance(server_handler.exec_command, bytes) else server_handler.exec_command
                logger.info(f"Executing command on backend: {cmd_str}")
                backend_channel.exec_command(cmd_str)
            elif server_handler.channel_type == 'subsystem' and server_handler.subsystem_name:
                # For SFTP and other subsystems
                subsys_name = server_handler.subsystem_name.decode('utf-8') if isinstance(server_handler.subsystem_name, bytes) else server_handler.subsystem_name
                logger.info(f"Invoking subsystem on backend: {subsys_name}")
                backend_channel.invoke_subsystem(subsys_name)
                
                # For SFTP, we'll log transfers by monitoring data flow
                # Note: Full SFTP parsing would require decoding the binary protocol
                if subsys_name == 'sftp':
                    logger.info(f"SFTP subsystem started - transfers will be logged")
            else:
                # For interactive shell sessions
                backend_channel.invoke_shell()
            
            # Determine if we should record this session
            # SCP/SFTP sessions should NOT be recorded (only tracked in SessionTransfer)
            should_record = True
            if server_handler.channel_type == 'exec' and server_handler.exec_command:
                cmd_str = server_handler.exec_command.decode('utf-8') if isinstance(server_handler.exec_command, bytes) else server_handler.exec_command
                if 'scp' in cmd_str:
                    should_record = False
                    logger.info(f"SCP session detected - disabling recording, will track in transfers only")
            elif server_handler.channel_type == 'subsystem' and server_handler.subsystem_name:
                subsys = server_handler.subsystem_name.decode('utf-8') if isinstance(server_handler.subsystem_name, bytes) else server_handler.subsystem_name
                if subsys == 'sftp':
                    should_record = False
                    logger.info(f"SFTP session detected - disabling recording, will track in transfers only")
            
            # Start session recording (only for interactive sessions)
            recorder = None
            if should_record:
                recorder = SSHSessionRecorder(
                    session_id=session_id,
                    username=user.username,
                    server_ip=target_server.ip_address,
                    server_name=target_server.name,
                    tower_client=server_handler.tower_client,
                    server_instance=self
                )
                recorder.record_event('session_start', f"User {user.username} connecting to {target_server.ip_address}")
            
            # Get policy_id from access_result (Tower API response)
            grant_id = server_handler.access_result.get('grant_id') if hasattr(server_handler, 'access_result') else None
            
            # Get SSH protocol version from client
            client_version = transport.remote_version if hasattr(transport, 'remote_version') else None
            protocol_version = client_version.decode('utf-8') if isinstance(client_version, bytes) else str(client_version) if client_version else None
            
            # Create session record via Tower API
            # Tower API will automatically create or reuse Stay based on user's active sessions
            try:
                subsystem = server_handler.subsystem_name
                if subsystem and isinstance(subsystem, bytes):
                    subsystem = subsystem.decode('utf-8')
                
                session_response = server_handler.tower_client.create_session(
                    session_id=session_id,
                    person_id=user.id,
                    server_id=target_server.id,
                    protocol='ssh',
                    source_ip=source_ip,
                    proxy_ip=dest_ip,
                    backend_ip=target_server.ip_address,
                    backend_port=22,
                    grant_id=grant_id,
                    ssh_username=server_handler.ssh_login,
                    subsystem_name=subsystem,
                    ssh_agent_used=bool(server_handler.agent_channel),
                    recording_path=recorder.recording_file if recorder and hasattr(recorder, 'recording_file') else None,
                    protocol_version=protocol_version
                )
                db_session_id = session_response.get('db_session_id')
                logger.info(f"Session {session_id} created via Tower API (DB ID: {db_session_id})")
                
                # Create local session object for compatibility
                db_session = type('Session', (), {
                    'id': db_session_id,
                    'session_id': session_id,
                    'user_id': user.id,
                    'server_id': target_server.id
                })()
                
            except Exception as e:
                logger.error(f"Failed to create session via Tower API: {e}", exc_info=True)
                # Fallback to direct DB insert
                db_session = DBSession(
                    session_id=session_id,
                    user_id=user.id,
                    server_id=target_server.id,
                    protocol='ssh',
                    source_ip=source_ip,
                    proxy_ip=dest_ip,
                    backend_ip=target_server.ip_address,
                    backend_port=22,
                    ssh_username=server_handler.ssh_login,
                    subsystem_name=subsystem if 'subsystem' in locals() else None,
                    ssh_agent_used=bool(server_handler.agent_channel),
                    started_at=datetime.utcnow(),
                    is_active=True,
                    recording_path=recorder.recording_file if recorder and hasattr(recorder, 'recording_file') else None,
                    policy_id=grant_id,
                    connection_status='active',
                    protocol_version=protocol_version
                )
                db.add(db_session)
                db.commit()
                db.refresh(db_session)
            
            # Pass db_session to server_handler for port forwarding logging
            server_handler.db_session = db_session
            
            # Log SCP transfers (now that we have db_session.id)
            if server_handler.channel_type == 'exec' and server_handler.exec_command:
                cmd_str = server_handler.exec_command.decode('utf-8') if isinstance(server_handler.exec_command, bytes) else server_handler.exec_command
                if 'scp' in cmd_str:
                    if '-t' in cmd_str:
                        # SCP upload (to server)
                        self.log_scp_transfer(db_session.id, cmd_str, 'upload')
                    elif '-f' in cmd_str:
                        # SCP download (from server)
                        self.log_scp_transfer(db_session.id, cmd_str, 'download')
            
            # Write to utmp/wtmp (makes session visible in 'w' command)
            tty_name = f"ssh{db_session.id % 100}"  # ssh0-ssh99
            backend_display = f"{server_handler.ssh_login}@{target_server.name}"
            if server_handler.subsystem_name:
                subsys = server_handler.subsystem_name.decode('utf-8') if isinstance(server_handler.subsystem_name, bytes) else server_handler.subsystem_name
                backend_display += f":{subsys}"
            write_utmp_login(session_id, user.username, tty_name, source_ip, backend_display)
            logger.debug(f"Session {session_id} registered in utmp as {tty_name}")
            
            # Register connection in active connections registry for heartbeat monitoring
            self.active_connections[session_id] = {
                'transport': transport,
                'backend_transport': backend_transport,
                'source_ip': source_ip,
                'proxy_ip': dest_ip,
                'protocol': 'ssh',
                'ssh_username': user.username,
                'started_at': datetime.utcnow()
            }
            logger.debug(f"Session {session_id} registered in active connections")
            
            # Check grant expiry for interactive shell sessions
            grant_end_time = None
            if server_handler.channel_type == 'shell':
                # Use effective_end_time from access control if available (Tower API)
                # This considers both policy end_time AND schedule window end
                if hasattr(server_handler, 'access_result') and server_handler.access_result:
                    effective_end_str = server_handler.access_result.get('effective_end_time')
                    if effective_end_str:
                        # Parse ISO format datetime string from API
                        from dateutil import parser as dateparser
                        grant_end_time = dateparser.isoparse(effective_end_str)
                        # Convert to naive UTC for calculations
                        if grant_end_time.tzinfo is not None:
                            grant_end_time = grant_end_time.replace(tzinfo=None)
                
                # Extract inactivity timeout from API response (default 60 minutes)
                inactivity_timeout_minutes = 60
                if hasattr(server_handler, 'access_result') and server_handler.access_result:
                    inactivity_timeout_minutes = server_handler.access_result.get('inactivity_timeout_minutes', 60)
                    if inactivity_timeout_minutes is None:
                        inactivity_timeout_minutes = 60
                
                # Fallback to old behavior (earliest policy end_time) - for legacy code paths
                if grant_end_time is None and hasattr(server_handler, 'matching_policies') and server_handler.matching_policies:
                    end_times = [p.end_time for p in server_handler.matching_policies if p.end_time]
                    if end_times:
                        grant_end_time = min(end_times)
                
                # Send welcome message - even for permanent grants (grant_end_time=None)
                if grant_end_time:
                    logger.info(f"Session {session_id}: Grant expires at {grant_end_time}")
                    
                    # Store initial grant end time for heartbeat monitoring
                    self.session_grant_endtimes[session_id] = grant_end_time
                    
                    # Send welcome message with expiry time
                    now = datetime.utcnow()
                    remaining = grant_end_time - now
                    remaining_seconds = remaining.total_seconds()
                    
                    # Format time remaining in days, hours and minutes
                    days = int(remaining_seconds // 86400)
                    hours = int((remaining_seconds % 86400) // 3600)
                    minutes = int((remaining_seconds % 3600) // 60)
                    
                    # Build human-readable time string
                    time_parts = []
                    if days > 0:
                        time_parts.append(f"{days} day{'s' if days != 1 else ''}")
                    if hours > 0:
                        time_parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
                    if minutes > 0 or len(time_parts) == 0:
                        time_parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
                    time_str = " ".join(time_parts)
                    
                    # Convert UTC to Europe/Warsaw for display
                    warsaw_tz = pytz.timezone('Europe/Warsaw')
                    grant_end_time_local = grant_end_time if grant_end_time.tzinfo else pytz.utc.localize(grant_end_time)
                    grant_end_time_local = grant_end_time_local.astimezone(warsaw_tz)
                    
                    welcome_msg = (
                        f"\r\n"
                        f"{'='*70}\r\n"
                        f"  Access Grant Information\r\n"
                        f"  Your access expires at: {grant_end_time_local.strftime('%Y-%m-%d %H:%M:%S %Z')}\r\n"
                        f"  Time remaining: {time_str}\r\n"
                        f"  Inactivity timeout: {inactivity_timeout_minutes} minute{'s' if inactivity_timeout_minutes != 1 else ''}\r\n"
                        f"  \r\n"
                        f"  You will receive warnings before your access expires.\r\n"
                        f"  Your session will be automatically disconnected at expiry time.\r\n"
                        f"  Session disconnects after {inactivity_timeout_minutes} minutes of no activity.\r\n"
                        f"{'='*70}\r\n\r\n"
                    )
                    
                    try:
                        channel.send(welcome_msg.encode())
                        logger.info(f"Session {session_id}: Sent grant expiry welcome message")
                    except Exception as e:
                        logger.error(f"Session {session_id}: Failed to send welcome message: {e}")
                else:
                    # Permanent grant (no end_time)
                    logger.info(f"Session {session_id}: Permanent grant (no expiration)")
                    
                    # Build welcome message based on inactivity timeout status
                    if inactivity_timeout_minutes and inactivity_timeout_minutes > 0:
                        welcome_msg = (
                            f"\r\n"
                            f"{'='*70}\r\n"
                            f"  Access Grant Information\r\n"
                            f"  Your access has no expiration time (permanent grant)\r\n"
                            f"  Inactivity timeout: {inactivity_timeout_minutes} minute{'s' if inactivity_timeout_minutes != 1 else ''}\r\n"
                            f"  \r\n"
                            f"  Note: The administrator can revoke access at any time.\r\n"
                            f"  Session disconnects after {inactivity_timeout_minutes} minutes of no activity.\r\n"
                            f"{'='*70}\r\n\r\n"
                        )
                    else:
                        welcome_msg = (
                            f"\r\n"
                            f"{'='*70}\r\n"
                            f"  Access Grant Information\r\n"
                            f"  Your access has no expiration time (permanent grant)\r\n"
                            f"  \r\n"
                            f"  Note: The administrator can revoke access at any time.\r\n"
                            f"{'='*70}\r\n\r\n"
                        )
                    try:
                        channel.send(welcome_msg.encode())
                        logger.info(f"Session {session_id}: Sent permanent grant welcome message")
                    except Exception as e:
                        logger.error(f"Session {session_id}: Failed to send welcome message: {e}")
                
                # Always start grant monitor (to detect revocation for permanent grants)
                # Initialize session metadata for terminal title updates
                self.session_metadata[session_id] = {
                    'grant_end_time': grant_end_time,
                    'inactivity_timeout': inactivity_timeout_minutes,
                    'server_name': target_server.name
                }
                
                monitor_thread = threading.Thread(
                    target=self.monitor_grant_expiry,
                    args=(channel, backend_channel, transport, backend_transport, 
                          grant_end_time, db_session.id, session_id, target_server.name),
                    daemon=True
                )
                monitor_thread.start()
                logger.debug(f"Session {session_id}: Started grant monitor thread")
                
                # Start inactivity timeout monitor (if enabled)
                if inactivity_timeout_minutes and inactivity_timeout_minutes > 0:
                    inactivity_monitor = threading.Thread(
                        target=self.monitor_inactivity_timeout,
                        args=(channel, backend_channel, transport, backend_transport,
                              inactivity_timeout_minutes, db_session.id, session_id, target_server.name),
                        daemon=True
                    )
                    inactivity_monitor.start()
                    logger.debug(f"Session {session_id}: Started inactivity timeout monitor ({inactivity_timeout_minutes} min)")
                else:
                    logger.debug(f"Session {session_id}: Inactivity timeout disabled")
            
            # Forward traffic (with SFTP tracking if applicable)
            is_sftp = (server_handler.channel_type == 'subsystem' and 
                      server_handler.subsystem_name and 
                      (server_handler.subsystem_name.decode('utf-8') if isinstance(server_handler.subsystem_name, bytes) else server_handler.subsystem_name) == 'sftp')
            self.forward_channel(channel, backend_channel, recorder, db_session.id, is_sftp, 
                               session_id=session_id, server_name=target_server.name)
            
            # Calculate session duration
            started_at = datetime.utcnow() - timedelta(seconds=0)  # Will be calculated by Tower API
            ended_at = datetime.utcnow()
            
            # Note: Terminal title already cleared in forward_channel finally block
            
            # Update session via Tower API
            try:
                update_payload = {
                    'ended_at': ended_at.isoformat(),
                    'is_active': False,
                    'termination_reason': 'normal'
                }
                
                if recorder and hasattr(recorder, 'recording_file') and os.path.exists(recorder.recording_file):
                    update_payload['recording_path'] = recorder.recording_file
                    update_payload['recording_size'] = os.path.getsize(recorder.recording_file)
                
                server_handler.tower_client.update_session(session_id, **update_payload)
                logger.info(f"Session {session_id} ended normally via Tower API")
            except Exception as e:
                logger.error(f"Failed to update session via Tower API: {e}")
                # Fallback to direct DB update
                try:
                    db_session_obj = db.query(DBSession).filter(DBSession.session_id == session_id).first()
                    if db_session_obj:
                        db_session_obj.ended_at = ended_at
                        db_session_obj.is_active = False
                        db_session_obj.duration_seconds = int((ended_at - db_session_obj.started_at).total_seconds())
                        db_session_obj.termination_reason = 'normal'
                        if recorder and hasattr(recorder, 'recording_file') and os.path.exists(recorder.recording_file):
                            db_session_obj.recording_size = os.path.getsize(recorder.recording_file)
                        db.commit()
                        logger.info(f"Session {session_id} ended normally (fallback DB update)")
                except Exception as e2:
                    logger.error(f"Failed fallback DB update: {e2}")
                    db.rollback()
            
            # Write logout to utmp/wtmp
            write_utmp_logout(tty_name, user.username)
            logger.info(f"Session {session_id} removed from utmp")
            
            # Unregister from active connections
            if session_id in self.active_connections:
                del self.active_connections[session_id]
                logger.debug(f"Session {session_id} unregistered from active connections")
            
            # Save recording (only if we were recording)
            if recorder:
                recorder.record_event('session_end', 'Connection closed')
                recorder.save()
        
        except Exception as e:
            logger.error(f"Error handling client {source_ip}: {e}", exc_info=True)
            # Try to close session via Tower API on error
            try:
                if 'session_id' in locals() and 'server_handler' in locals() and hasattr(server_handler, 'tower_client'):
                    try:
                        server_handler.tower_client.update_session(
                            session_id=session_id,
                            ended_at=datetime.utcnow().isoformat(),
                            is_active=False,
                            termination_reason='error'
                        )
                        logger.info(f"Session {session_id} closed due to error via Tower API")
                    except Exception as api_err:
                        logger.error(f"Failed to close session via API: {api_err}")
                        # Fallback to DB
                        db_session_error = db.query(DBSession).filter(DBSession.session_id == session_id).first()
                        if db_session_error and db_session_error.is_active:
                            db_session_error.ended_at = datetime.utcnow()
                            db_session_error.is_active = False
                            db_session_error.duration_seconds = int((db_session_error.ended_at - db_session_error.started_at).total_seconds())
                            db_session_error.termination_reason = 'error'
                            db.commit()
                            logger.info(f"Session {session_id} closed due to error (fallback DB)")
                
                # Write logout to utmp
                if 'db_session' in locals() and hasattr(db_session, 'id'):
                    tty_name = f"ssh{db_session.id % 100}"
                    write_utmp_logout(tty_name, user.username if 'user' in locals() else "")
                elif 'db_session_error' in locals() and hasattr(db_session_error, 'id'):
                    tty_name = f"ssh{db_session_error.id % 100}"
                    write_utmp_logout(tty_name, user.username if 'user' in locals() else "")
                    
            except Exception as cleanup_error:
                logger.error(f"Error closing session record: {cleanup_error}")
        
        finally:
            if backend_transport:
                backend_transport.close()
            client_socket.close()
    
    def send_heartbeat_loop(self):
        """Send periodic heartbeats to Tower and check for sessions to terminate"""
        logger.info(f"Heartbeat thread started (interval: {self.heartbeat_interval}s)")
        
        while self.running:
            try:
                # Gate always uses Tower API (no direct database access)
                # Tower will track session counts from API calls
                self.tower_client.heartbeat(active_stays=0, active_sessions=0)
                if len(self.active_connections) > 0:
                    logger.info(f"Heartbeat sent, checking {len(self.active_connections)} active sessions")
                else:
                    logger.debug(f"Heartbeat sent, no active sessions")
                
                # Check for sessions that should be terminated
                # 1. Grant expired/cancelled
                # 2. User deactivated
                # 3. Policy changed
                # 4. Maintenance mode
                self.check_and_terminate_sessions()
                
            except Exception as e:
                logger.error(f"Heartbeat thread error: {e}", exc_info=True)
            
            # Sleep in small increments to allow quick shutdown
            for _ in range(self.heartbeat_interval):
                if not self.running:
                    break
                time.sleep(1)
        
        logger.info("Heartbeat thread stopped")
    
    def check_and_terminate_sessions(self):
        """Check active sessions and terminate those that should be killed
        
        Uses local active_connections registry to find sessions, then checks
        via Tower API if each session should still be allowed.
        
        Reasons for termination:
        - Grant expired or cancelled (checked via Tower API)
        - User deactivated (checked via Tower API)  
        - Policy changed (checked via Tower API)
        - Maintenance mode (checked via Tower API)
        """
        try:
            # Get all active sessions from local registry
            # active_connections: {session_id: {transport, source_ip, proxy_ip, ...}}
            for session_id, session_info in list(self.active_connections.items()):
                source_ip = session_info.get('source_ip')
                proxy_ip = session_info.get('proxy_ip')
                protocol = session_info.get('protocol', 'ssh')
                ssh_username = session_info.get('ssh_username')
                
                if not source_ip or not proxy_ip:
                    logger.debug(f"Session {session_id}: Missing connection info, skipping check")
                    continue
                
                try:
                    # Check via Tower API if grant still valid
                    result = self.tower_client.check_grant(
                        source_ip=source_ip,
                        destination_ip=proxy_ip,
                        protocol=protocol,
                        ssh_login=ssh_username
                    )
                    
                    if not result.get('allowed'):
                        # Access denied - terminate session
                        reason = result.get('reason', 'Access revoked')
                        denial_reason = result.get('denial_reason', 'access_denied')
                        
                        # Get disconnect_at from API response or default to 5 seconds
                        disconnect_at_str = result.get('disconnect_at')
                        if disconnect_at_str:
                            from dateutil import parser as dateparser
                            disconnect_at = dateparser.isoparse(disconnect_at_str)
                            if disconnect_at.tzinfo is not None:
                                disconnect_at = disconnect_at.replace(tzinfo=None)
                        else:
                            disconnect_at = datetime.utcnow() + timedelta(seconds=5)
                        
                        logger.warning(
                            f"Session {session_id} ({ssh_username}@{proxy_ip}) should be terminated: {reason} ({denial_reason})"
                        )
                        
                        # Inject forced disconnect time - monitor_grant_expiry thread will handle it
                        self.session_forced_endtimes[session_id] = disconnect_at
                        
                        logger.info(
                            f"Session {session_id}: Forced disconnect injected, "
                            f"will disconnect at {disconnect_at} (reason: {reason})"
                        )
                    else:
                        # Access still allowed - check if grant time changed
                        effective_end_str = result.get('effective_end_time')
                        if effective_end_str:
                            from dateutil import parser as dateparser
                            new_end_time = dateparser.isoparse(effective_end_str)
                            if new_end_time.tzinfo is not None:
                                new_end_time = new_end_time.replace(tzinfo=None)
                            
                            # Check if grant time changed (extended or shortened)
                            old_end_time = self.session_grant_endtimes.get(session_id)
                            if old_end_time and new_end_time != old_end_time:
                                if new_end_time > old_end_time:
                                    logger.info(
                                        f"Session {session_id}: Grant extended from {old_end_time} to {new_end_time}"
                                    )
                                else:
                                    logger.info(
                                        f"Session {session_id}: Grant shortened from {old_end_time} to {new_end_time}"
                                    )
                                # Update stored end time - monitor will detect this
                                self.session_grant_endtimes[session_id] = new_end_time
                            elif not old_end_time:
                                # First time seeing this session - store end time
                                self.session_grant_endtimes[session_id] = new_end_time
                
                except Exception as e:
                    logger.error(f"Error checking session {session_id}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error in check_and_terminate_sessions: {e}")
    
    def start(self):
        """Start the proxy server with NAT and/or TPROXY listeners"""
        logger.info(f"Starting SSH Proxy Server")
        
        # Start heartbeat thread
        self.running = True
        self.heartbeat_thread = threading.Thread(target=self.send_heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
        
        listeners = []
        
        # Setup NAT listener (traditional mode)
        if self.nat_config:
            nat_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            nat_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            nat_socket.bind((self.nat_config['host'], self.nat_config['port']))
            nat_socket.listen(100)
            listeners.append(('NAT', nat_socket, False))
            logger.info(f"NAT mode listening on {self.nat_config['host']}:{self.nat_config['port']}")
        
        # Setup TPROXY listener (transparent mode)
        if self.tproxy_config:
            tproxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tproxy_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Enable IP_TRANSPARENT to receive packets with non-local destination
            IP_TRANSPARENT = 19
            tproxy_socket.setsockopt(socket.SOL_IP, IP_TRANSPARENT, 1)
            
            tproxy_socket.bind((self.tproxy_config['host'], self.tproxy_config['port']))
            tproxy_socket.listen(100)
            listeners.append(('TPROXY', tproxy_socket, True))
            logger.info(f"TPROXY mode listening on {self.tproxy_config['host']}:{self.tproxy_config['port']}")
        
        if not listeners:
            logger.error("No listeners configured (both NAT and TPROXY disabled)")
            return
        
        logger.info(f"SSH Proxy ready with {len(listeners)} listener(s)")
        
        try:
            while True:
                # Use select to handle multiple sockets
                readable, _, _ = select.select([sock for _, sock, _ in listeners], [], [], 1.0)
                
                for listener_name, listener_sock, is_tproxy in listeners:
                    if listener_sock in readable:
                        client_socket, client_addr = listener_sock.accept()
                        logger.debug(f"{listener_name}: Accepted connection from {client_addr}")
                        
                        client_thread = threading.Thread(
                            target=self.handle_client,
                            args=(client_socket, client_addr, is_tproxy)
                        )
                        client_thread.daemon = True
                        client_thread.start()
        
        except KeyboardInterrupt:
            logger.info("Shutting down SSH Proxy Server...")
            self.running = False  # Stop heartbeat thread
            if self.heartbeat_thread:
                self.heartbeat_thread.join(timeout=5)
            
            # Close all listeners
            for _, sock, _ in listeners:
                sock.close()
        
        finally:
            server_socket.close()


def cleanup_stale_sessions():
    """Clean up active sessions and stays from previous runs on startup via Tower API"""
    logger.info("Requesting Tower to cleanup stale sessions for this gate")
    try:
        tower_client = TowerClient(GateConfig())
        result = tower_client.cleanup_stale_sessions()
        logger.info(
            f"Tower cleaned up {result.get('closed_sessions')} sessions and "
            f"{result.get('closed_stays')} stays"
        )
    except Exception as e:
        logger.error(f"Failed to request cleanup from Tower: {e}")


def main():
    """Main entry point"""
    # Load configuration
    config = configparser.ConfigParser()
    
    # Try environment variable first (for standalone deployments)
    config_file_env = os.getenv('INSIDE_SSH_PROXY_CONFIG')
    if config_file_env:
        config_file = Path(config_file_env)
    else:
        # Default locations
        config_file = Path('/opt/jumphost/config/ssh_proxy.conf')
    
    nat_config = None
    tproxy_config = None
    
    if config_file.exists():
        config.read(config_file)
        logger.info(f"Loaded configuration from {config_file}")
        
        # Configure logging level from config
        if config.has_option('logging', 'level'):
            log_level_str = config.get('logging', 'level').upper()
            log_level = getattr(logging, log_level_str, logging.INFO)
            logging.getLogger().setLevel(log_level)
            logger.setLevel(log_level)
            logger.info(f"Log level set to {log_level_str}")
        
        # Configure file logging if specified in config
        if config.has_option('logging', 'file'):
            log_file = config.get('logging', 'file')
            log_dir = Path(log_file).parent
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # Add file handler
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            logging.getLogger().addHandler(file_handler)
            logger.info(f"Logging to file: {log_file}")
        
        # Host key path from config
        host_key_path = config.get('advanced', 'host_key_path', fallback='/var/lib/inside-gate/ssh_host_key')
        
        # NAT mode configuration
        if config.getboolean('proxy', 'nat_enabled', fallback=False):
            nat_config = {
                'host': config.get('proxy', 'nat_host', fallback='0.0.0.0'),
                'port': config.getint('proxy', 'nat_port', fallback=22)
            }
            logger.info(f"NAT mode enabled: {nat_config['host']}:{nat_config['port']}")
        
        # TPROXY mode configuration
        if config.getboolean('proxy', 'tproxy_enabled', fallback=False):
            tproxy_config = {
                'host': config.get('proxy', 'tproxy_host', fallback='0.0.0.0'),
                'port': config.getint('proxy', 'tproxy_port', fallback=8022)
            }
            logger.info(f"TPROXY mode enabled: {tproxy_config['host']}:{tproxy_config['port']}")
    else:
        # Default: TPROXY mode only for standalone
        logger.warning(f"Config file not found: {config_file}, using defaults (TPROXY mode only)")
        tproxy_config = {'host': '0.0.0.0', 'port': 8022}
        host_key_path = '/var/lib/inside-gate/ssh_host_key'
    
    # Clean up stale sessions from previous runs
    cleanup_stale_sessions()
    
    # Load custom messages from Tower
    load_messages()
    
    # Start proxy server
    proxy = SSHProxyServer(nat_config=nat_config, tproxy_config=tproxy_config, host_key_path=host_key_path)
    proxy.start()


if __name__ == '__main__':
    main()
