"""Tower API client for Gate.

Gate uses this client to communicate with Tower API.
Never touches PostgreSQL directly - always uses Tower REST API.
"""

import time
import logging
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime

from src.gate.config import get_config

logger = logging.getLogger(__name__)


class TowerAPIError(Exception):
    """Base exception for Tower API errors."""
    pass


class TowerUnreachableError(TowerAPIError):
    """Tower is unreachable (network error, timeout, etc)."""
    pass


class TowerAuthError(TowerAPIError):
    """Authentication failed (invalid token)."""
    pass


class TowerClient:
    """Client for Tower REST API.
    
    Usage:
        client = TowerClient()
        result = client.check_grant(username='jan.kowalski', server='srv-prod-01', protocol='ssh')
        if result['allowed']:
            stay_id = client.start_stay(...)
    """
    
    def __init__(self, config=None):
        """Initialize Tower API client.
        
        Args:
            config: GateConfig instance. If None, loads from gate.conf.
        """
        self.config = config or get_config()
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': self.config.auth_header,
            'Content-Type': 'application/json',
            'User-Agent': f'Inside-Gate/{self.config.version} ({self.config.gate_name})'
        })
        
        # Disable SSL verification if configured (dev only!)
        if not self.config.verify_ssl:
            self.session.verify = False
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                 params: Optional[Dict] = None, retry: bool = True) -> Dict[str, Any]:
        """Make HTTP request to Tower API with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc)
            endpoint: API endpoint (e.g., '/api/v1/auth/check')
            data: JSON body for POST/PUT
            params: Query parameters for GET
            retry: Enable retry with exponential backoff
        
        Returns:
            Response JSON as dict
        
        Raises:
            TowerUnreachableError: Network error, timeout
            TowerAuthError: 401/403 authentication error
            TowerAPIError: Other API errors
        """
        url = f"{self.config.tower_url}{endpoint}"
        
        attempts = self.config.api_retry_attempts if retry else 1
        backoff = 1.0
        
        for attempt in range(attempts):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    timeout=self.config.api_timeout
                )
                
                # Check for auth errors
                if response.status_code in [401, 403]:
                    error_data = response.json() if response.content else {}
                    raise TowerAuthError(
                        f"Authentication failed: {error_data.get('message', response.text)}"
                    )
                
                # Check for other HTTP errors
                if response.status_code >= 400:
                    error_data = response.json() if response.content else {}
                    raise TowerAPIError(
                        f"Tower API error {response.status_code}: "
                        f"{error_data.get('message', response.text)}"
                    )
                
                # Success
                return response.json() if response.content else {}
            
            except (requests.ConnectionError, requests.Timeout) as e:
                if attempt < attempts - 1:
                    logger.warning(
                        f"Tower API request failed (attempt {attempt + 1}/{attempts}): {e}. "
                        f"Retrying in {backoff}s..."
                    )
                    time.sleep(backoff)
                    backoff *= self.config.api_retry_backoff
                else:
                    raise TowerUnreachableError(
                        f"Tower unreachable after {attempts} attempts: {e}"
                    )
            
            except TowerAuthError:
                # Don't retry auth errors
                raise
            
            except Exception as e:
                logger.error(f"Unexpected error in Tower API request: {e}")
                raise TowerAPIError(f"Unexpected error: {e}")
        
        # Should never reach here
        raise TowerAPIError("Request failed with unknown error")
    
    def check_grant(self, source_ip: str, destination_ip: str, protocol: str, 
                    ssh_login: Optional[str] = None, ssh_key_fingerprint: Optional[str] = None,
                    mfa_token: Optional[str] = None) -> Dict[str, Any]:
        """Check if connection is allowed via Tower API.
        
        Args:
            source_ip: Client source IP address
            destination_ip: Destination IP (proxy IP on gate)
            protocol: 'ssh' or 'rdp'
            ssh_login: SSH login name (required for SSH)
            ssh_key_fingerprint: SSH key SHA256 fingerprint for MFA session persistence
            mfa_token: Verified MFA challenge token (proof of authentication)
        
        Returns:
            {
                'allowed': bool,
                'user': dict,  # User info if allowed
                'server': dict,  # Backend server info if allowed
                'reason': str,
                'denial_reason': str,  # If denied
                'port_forwarding_allowed': bool
            }
        
        Raises:
            TowerUnreachableError: Tower not reachable
            TowerAuthError: Gate token invalid
        """
        data = {
            'source_ip': source_ip,
            'destination_ip': destination_ip,
            'protocol': protocol
        }
        if ssh_login:
            data['ssh_login'] = ssh_login
        if ssh_key_fingerprint:
            data['ssh_key_fingerprint'] = ssh_key_fingerprint
        if mfa_token:
            data['mfa_token'] = mfa_token
        
        try:
            response = self._request('POST', '/api/v1/auth/check', data=data)
            logger.info(
                f"Grant check: {source_ip} -> {destination_ip} ({protocol}): "
                f"{'ALLOWED' if response.get('allowed') else 'DENIED'}"
            )
            return response
        
        except TowerAuthError as e:
            # For auth errors (403), parse the JSON response from error message
            # Tower returns access denial details in 403 response body
            import json
            try:
                # Error message contains JSON response
                error_str = str(e).replace('Authentication failed: ', '')
                error_data = json.loads(error_str)
                # If it's a proper denial response, return it
                if 'allowed' in error_data:
                    logger.info(
                        f"Grant check: {source_ip} -> {destination_ip} ({protocol}): "
                        f"DENIED - {error_data.get('denial_reason', error_data.get('reason', 'unknown'))}"
                    )
                    return error_data
            except Exception as parse_err:
                logger.error(f"Failed to parse denial response: {parse_err}")
            # Fallback for malformed responses
            logger.error(f"Grant check authentication error: {e}")
            return {
                'allowed': False,
                'reason': 'authentication_error',
                'details': str(e)
            }
        
        except TowerAPIError as e:
            logger.error(f"Grant check failed: {e}")
            raise
    
    def create_mfa_challenge(
        self, 
        ssh_username: str,
        source_ip: Optional[str] = None,
        user_id: Optional[int] = None, 
        grant_id: Optional[int] = None,
        destination_ip: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create MFA challenge for user authentication.
        
        Phase 1 (known user):
            user_id and grant_id provided
        
        Phase 2 (unknown user):
            destination_ip provided, user identified via SAML email
        
        Args:
            ssh_username: SSH login username
            source_ip: Client source IP
            user_id: User ID from check_grant response (Phase 1)
            grant_id: Grant ID from check_grant response (Phase 1)
            destination_ip: Destination IP for Phase 2 identification
        
        Returns:
            {
                'mfa_required': True,
                'mfa_token': str,
                'mfa_url': str,
                'mfa_qr': str,  # ASCII QR code
                'timeout_minutes': int
            }
        """
        data = {
            'ssh_username': ssh_username
        }
        
        if source_ip:
            data['source_ip'] = source_ip
        if user_id:
            data['user_id'] = user_id
        if grant_id:
            data['grant_id'] = grant_id
        if destination_ip:
            data['destination_ip'] = destination_ip
        
        response = self._request('POST', '/api/v1/mfa/challenge', data=data)
        logger.info(f"MFA challenge created: user_id={user_id}, destination_ip={destination_ip}, token={response.get('mfa_token')}")
        return response
    
    def check_mfa_status(self, token: str) -> Dict[str, Any]:
        """Check MFA challenge verification status.
        
        Args:
            token: MFA token from create_mfa_challenge
        
        Returns:
            {
                'verified': bool,
                'stay_id': int,  # If verified
                'expired': bool  # If challenge expired
            }
        """
        response = self._request('GET', f'/api/v1/mfa/status/{token}', retry=False)
        return response
    
    def cancel_mfa_challenge(self, token: str) -> Dict[str, Any]:
        """Cancel pending MFA challenge (user disconnected before completing MFA).
        
        Args:
            token: MFA token from create_mfa_challenge
        
        Returns:
            {'success': bool, 'message': str}
        """
        try:
            response = self._request('DELETE', f'/api/v1/mfa/challenge/{token}', retry=False)
            return response
        except Exception as e:
            logger.warning(f"Failed to cancel MFA challenge {token[:20]}: {e}")
            return {'success': False, 'message': str(e)}
    
    def start_stay(self, username: str, server: str, grant_id: int, 
                   source_ip: Optional[str] = None, ssh_key_fingerprint: Optional[str] = None) -> int:
        """Report person entered server (create Stay).
        
        Args:
            username: Person username
            server: Server hostname or IP
            grant_id: Grant ID from check_grant()
            source_ip: Optional client source IP
            ssh_key_fingerprint: Optional SSH key fingerprint for MFA session persistence
        
        Returns:
            dict: Stay details including stay_id
        
        Raises:
            TowerUnreachableError: Tower not reachable
        """
        data = {
            'username': username,
            'server': server,
            'grant_id': grant_id
        }
        if source_ip:
            data['source_ip'] = source_ip
        if ssh_key_fingerprint:
            data['ssh_key_fingerprint'] = ssh_key_fingerprint
        
        response = self._request('POST', '/api/v1/stays/start', data=data)
        stay_id = response.get('stay_id')
        
        logger.info(f"Stay started: #{stay_id} - {username} entered {server}")
        return response
    
    def end_stay(self, stay_id: int, termination_reason: str = 'normal_disconnect') -> Dict[str, Any]:
        """Report person left server (end Stay).
        
        Args:
            stay_id: Stay ID from start_stay()
            termination_reason: Reason for ending stay
        
        Returns:
            Stay details including duration
        
        Raises:
            TowerUnreachableError: Tower not reachable
        """
        data = {
            'stay_id': stay_id,
            'termination_reason': termination_reason
        }
        
        response = self._request('POST', '/api/v1/stays/end', data=data)
        
        logger.info(
            f"Stay ended: #{stay_id} - duration {response.get('duration_seconds')}s, "
            f"reason: {termination_reason}"
        )
        return response
    
    def get_active_grants(self, protocol: Optional[str] = None, limit: int = 1000) -> List[Dict[str, Any]]:
        """Fetch active grants for cache refresh.
        
        Args:
            protocol: Filter by protocol ('ssh' or 'rdp')
            limit: Max grants to fetch
        
        Returns:
            List of grant dicts
        
        Raises:
            TowerUnreachableError: Tower not reachable
        """
        params = {'limit': limit}
        if protocol:
            params['protocol'] = protocol
        
        response = self._request('GET', '/api/v1/grants/active', params=params)
        grants = response.get('grants', [])
        
        logger.debug(f"Fetched {len(grants)} active grants from Tower")
        return grants
    
    def heartbeat(self, active_stays: int = 0, active_sessions: int = 0, active_session_ids: list = None) -> Dict[str, Any]:
        """Send heartbeat to Tower to report Gate is alive.
        
        Args:
            active_stays: Number of active stays on this Gate
            active_sessions: Number of active sessions on this Gate
            active_session_ids: List of active session IDs (for relay management)
        
        Returns:
            Tower response with gate status and relay_sessions
        
        Raises:
            TowerUnreachableError: Tower not reachable
        """
        data = {
            'version': self.config.version,
            'hostname': self.config.hostname,
            'active_stays': active_stays,
            'active_sessions': active_sessions
        }
        
        # Add session IDs if provided (for relay management)
        if active_session_ids:
            data['active_session_ids'] = active_session_ids
        
        response = self._request('POST', '/api/v1/gates/heartbeat', data=data, retry=False)
        
        logger.debug(
            f"Heartbeat sent: {self.config.gate_name} - "
            f"{active_stays} stays, {active_sessions} sessions"
        )
        return response
    
    def cleanup_stale_sessions(self) -> Dict[str, Any]:
        """Request Tower to close all active sessions/stays for this gate (on startup).
        
        Returns:
            {
                'closed_sessions': int,
                'closed_stays': int,
                'message': str
            }
        
        Raises:
            TowerUnreachableError: Tower not reachable
        """
        response = self._request('POST', '/api/v1/gates/cleanup', data={})
        
        logger.info(
            f"Cleanup complete: {response.get('closed_sessions')} sessions, "
            f"{response.get('closed_stays')} stays closed"
        )
        return response
    
    def get_config(self) -> Dict[str, Any]:
        """Fetch configuration from Tower.
        
        Returns:
            Configuration dict from Tower
        
        Raises:
            TowerUnreachableError: Tower not reachable
        """
        response = self._request('GET', '/api/v1/gates/config')
        
        logger.debug(f"Fetched config from Tower: {response.get('config', {})}")
        return response
    
    def get_status(self) -> Dict[str, Any]:
        """Get current Gate status from Tower.
        
        Returns:
            Status dict with statistics
        
        Raises:
            TowerUnreachableError: Tower not reachable
        """
        response = self._request('GET', '/api/v1/gates/status')
        return response
    
    def get_messages(self) -> Dict[str, str]:
        """Fetch custom messages for SSH banners and errors from Tower.
        
        Messages support placeholders: {person}, {backend}, {gate_name}, {reason}
        
        Returns:
            {
                'welcome_banner': str or None,
                'no_backend': str,
                'no_person': str,
                'no_grant': str,
                'maintenance': str,
                'time_window': str
            }
        
        Raises:
            TowerUnreachableError: Tower not reachable
        """
        response = self._request('GET', '/api/v1/gates/messages')
        messages = response.get('messages', {})
        
        logger.debug(f"Fetched custom messages from Tower ({len(messages)} message types)")
        return messages
    
    def create_session(self, session_id: str, person_id: int,
                      server_id: int, protocol: str, source_ip: str,
                      proxy_ip: str, backend_ip: str, backend_port: int,
                      grant_id: int, ssh_username: Optional[str] = None,
                      subsystem_name: Optional[str] = None,
                      ssh_agent_used: bool = False,
                      recording_path: Optional[str] = None,
                      protocol_version: Optional[str] = None,
                      ssh_key_fingerprint: Optional[str] = None,
                      effective_end_time: Optional[str] = None) -> Dict[str, Any]:
        """Report session creation to Tower.
        
        Tower API will automatically create or reuse Stay based on user's active sessions.
        
        Args:
            session_id: Unique session identifier
            person_id: Person ID
            server_id: Server ID
            protocol: 'ssh' or 'rdp'
            source_ip: Client source IP
            proxy_ip: IP from pool (what client connected to)
            backend_ip: Real backend server IP
            backend_port: Backend port
            grant_id: Grant/policy ID that allowed access
            ssh_username: SSH login used (optional)
            subsystem_name: SSH subsystem like 'sftp' (optional)
            ssh_agent_used: Whether SSH agent forwarding used (optional)
            recording_path: Path to session recording file (optional)
            protocol_version: Client protocol version string (optional)
        
        Returns:
            {
                'session_id': str,
                'db_session_id': int,
                'person_username': str,
                'server_name': str,
                'stay_id': int,
                'started_at': str,
                'is_active': bool,
                'message': str
            }
        """
        payload = {
            'session_id': session_id,
            'person_id': person_id,
            'server_id': server_id,
            'protocol': protocol,
            'source_ip': source_ip,
            'proxy_ip': proxy_ip,
            'backend_ip': backend_ip,
            'backend_port': backend_port,
            'grant_id': grant_id
        }
        
        # Optional fields
        if ssh_username:
            payload['ssh_username'] = ssh_username
        if subsystem_name:
            payload['subsystem_name'] = subsystem_name
        if ssh_agent_used:
            payload['ssh_agent_used'] = ssh_agent_used
        if recording_path:
            payload['recording_path'] = recording_path
        if protocol_version:
            payload['protocol_version'] = protocol_version
        if ssh_key_fingerprint:
            payload['ssh_key_fingerprint'] = ssh_key_fingerprint
        if effective_end_time:
            payload['effective_end_time'] = effective_end_time
        
        response = self._request('POST', '/api/v1/sessions/create', data=payload)
        return response
    
    def get_session_grant_status(self, db_session_id: int) -> Dict[str, Any]:
        """Get current grant status for a session (v1.11 - single source of truth).
        
        Args:
            db_session_id: Database session ID from session creation
        
        Returns:
            {
                'valid': bool,  # Is grant still valid?
                'end_time': str or null,  # ISO format with 'Z' suffix (UTC), null = permanent
                'reason': str  # If invalid: reason for denial
            }
        """
        response = self._request('GET', f'/api/v1/sessions/{db_session_id}/grant_status')
        return response
    
    def update_session(self, session_id: str, ended_at: Optional[str] = None,
                      duration_seconds: Optional[int] = None,
                      is_active: Optional[bool] = None,
                      termination_reason: Optional[str] = None,
                      recording_path: Optional[str] = None,
                      recording_size: Optional[int] = None) -> Dict[str, Any]:
        """Update session status in Tower.
        
        Args:
            session_id: Session identifier
            ended_at: When session ended (ISO format string, optional)
            duration_seconds: Session duration in seconds (optional)
            is_active: Whether session is still active (optional)
            termination_reason: Why session ended (optional)
            recording_path: Updated recording path (optional)
            recording_size: Recording file size in bytes (optional)
        
        Returns:
            {
                'session_id': str,
                'db_session_id': int,
                'updated_fields': list,
                'is_active': bool,
                'message': str
            }
        """
        payload = {}
        
        if ended_at is not None:
            payload['ended_at'] = ended_at
        if duration_seconds is not None:
            payload['duration_seconds'] = duration_seconds
        if is_active is not None:
            payload['is_active'] = is_active
        if termination_reason is not None:
            payload['termination_reason'] = termination_reason
        if recording_path is not None:
            payload['recording_path'] = recording_path
        if recording_size is not None:
            payload['recording_size'] = recording_size
        
        response = self._request('PATCH', f'/api/v1/sessions/{session_id}', data=payload)
        return response
    
    def start_recording(self, session_id: str, person_username: str,
                       server_name: str, server_ip: str) -> Dict[str, Any]:
        """Notify Tower that recording has started.
        
        Args:
            session_id: Session identifier
            person_username: Person username
            server_name: Server name
            server_ip: Server IP address
        
        Returns:
            {
                'session_id': str,
                'recording_path': str,
                'message': str
            }
        """
        payload = {
            'session_id': session_id,
            'person_username': person_username,
            'server_name': server_name,
            'server_ip': server_ip
        }
        
        response = self._request('POST', '/api/v1/recordings/start', data=payload)
        return response
    
    def upload_recording_chunk(self, session_id: str, recording_path: str,
                              chunk_data: bytes, chunk_index: int = 0) -> Dict[str, Any]:
        """Upload a chunk of recording data to Tower.
        
        Args:
            session_id: Session identifier
            recording_path: Recording path from start_recording response
            chunk_data: Raw bytes to upload
            chunk_index: Chunk sequence number
        
        Returns:
            {
                'session_id': str,
                'chunk_index': int,
                'bytes_written': int,
                'message': str
            }
        """
        import base64
        
        chunk_data_b64 = base64.b64encode(chunk_data).decode('ascii')
        
        payload = {
            'session_id': session_id,
            'recording_path': recording_path,
            'chunk_data': chunk_data_b64,
            'chunk_index': chunk_index,
            'timestamp': datetime.now().isoformat()
        }
        
        response = self._request('POST', '/api/v1/recordings/chunk', data=payload)
        return response
    
    def finalize_recording(self, session_id: str, recording_path: str,
                          total_bytes: int, duration_seconds: int = 0) -> Dict[str, Any]:
        """Notify Tower that recording is complete.
        
        Args:
            session_id: Session identifier
            recording_path: Recording path
            total_bytes: Total bytes uploaded
            duration_seconds: Session duration
        
        Returns:
            {
                'session_id': str,
                'recording_path': str,
                'file_size': int,
                'message': str
            }
        """
        payload = {
            'session_id': session_id,
            'recording_path': recording_path,
            'total_bytes': total_bytes,
            'duration_seconds': duration_seconds
        }
        
        response = self._request('POST', '/api/v1/recordings/finalize', data=payload)
        return response
    
    def ping(self) -> bool:
        """Test Tower connectivity.
        
        Returns:
            True if Tower is reachable, False otherwise
        """
        try:
            self.get_status()
            return True
        except TowerUnreachableError:
            return False
        except Exception as e:
            logger.warning(f"Tower ping failed: {e}")
            return False
    
    def get_active_stays(self) -> List[Dict[str, Any]]:
        """Get list of active stays from Tower (for admin console).
        
        Returns:
            List of active stay dictionaries
        """
        try:
            response = self._request('GET', '/api/v1/admin/active-stays')
            return response.get('stays', [])
        except Exception as e:
            logger.error(f"Failed to fetch active stays: {e}")
            return []
    
    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get list of active sessions from Tower (for admin console).
        
        Returns:
            List of active session dictionaries
        """
        try:
            response = self._request('GET', '/api/v1/admin/active-sessions')
            return response.get('sessions', [])
        except Exception as e:
            logger.error(f"Failed to fetch active sessions: {e}")
            return []
    
    def kill_session(self, session_id: str) -> Dict[str, Any]:
        """Kill/terminate an active session (for admin console).
        
        Args:
            session_id: Session ID to terminate
        
        Returns:
            {'success': bool, 'message': str, 'error': str (optional)}
        """
        try:
            response = self._request('POST', f'/api/v1/admin/kill-session/{session_id}')
            return {'success': True, 'message': response.get('message', 'Session terminated')}
        except Exception as e:
            logger.error(f"Failed to kill session {session_id}: {e}")
            return {'success': False, 'error': str(e)}


# Global client instance
_client = None


def get_client(config=None):
    """Get global Tower API client instance.
    
    Args:
        config: Optional GateConfig instance. Only used on first call.
    
    Returns:
        TowerClient instance
    """
    global _client
    if _client is None:
        _client = TowerClient(config)
    return _client
