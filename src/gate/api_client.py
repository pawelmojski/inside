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
                    ssh_login: Optional[str] = None) -> Dict[str, Any]:
        """Check if connection is allowed via Tower API.
        
        Args:
            source_ip: Client source IP address
            destination_ip: Destination IP (proxy IP on gate)
            protocol: 'ssh' or 'rdp'
            ssh_login: SSH login name (required for SSH)
        
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
    
    def start_stay(self, username: str, server: str, grant_id: int, 
                   source_ip: Optional[str] = None) -> int:
        """Report person entered server (create Stay).
        
        Args:
            username: Person username
            server: Server hostname or IP
            grant_id: Grant ID from check_grant()
            source_ip: Optional client source IP
        
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
    
    def heartbeat(self, active_stays: int = 0, active_sessions: int = 0) -> Dict[str, Any]:
        """Send heartbeat to Tower to report Gate is alive.
        
        Args:
            active_stays: Number of active stays on this Gate
            active_sessions: Number of active sessions on this Gate
        
        Returns:
            Tower response with gate status
        
        Raises:
            TowerUnreachableError: Tower not reachable
        """
        data = {
            'version': self.config.version,
            'hostname': self.config.hostname,
            'active_stays': active_stays,
            'active_sessions': active_sessions
        }
        
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
    
    def create_session(self, session_id: str, stay_id: int, person_id: int,
                      server_id: int, protocol: str, source_ip: str,
                      proxy_ip: str, backend_ip: str, backend_port: int,
                      grant_id: int, ssh_username: Optional[str] = None,
                      subsystem_name: Optional[str] = None,
                      ssh_agent_used: bool = False,
                      recording_path: Optional[str] = None,
                      protocol_version: Optional[str] = None) -> Dict[str, Any]:
        """Report session creation to Tower.
        
        Args:
            session_id: Unique session identifier
            stay_id: Stay ID from /stays/start
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
                'started_at': str,
                'is_active': bool,
                'message': str
            }
        """
        payload = {
            'session_id': session_id,
            'stay_id': stay_id,
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
        
        response = self._request('POST', '/api/v1/sessions/create', data=payload)
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
