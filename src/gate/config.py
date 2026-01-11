"""Gate configuration loader.

Loads Gate configuration from gate.conf file.
"""

import os
import configparser
from pathlib import Path


class GateConfig:
    """Gate configuration from gate.conf file."""
    
    def __init__(self, config_path=None):
        """Load configuration from file.
        
        Args:
            config_path: Path to gate.conf file. If None, searches in:
                1. /opt/jumphost/config/gate.conf
                2. /etc/inside/gate.conf
                3. ./config/gate.conf
        """
        if config_path is None:
            # Search for config file in standard locations
            search_paths = [
                '/opt/jumphost/config/gate.conf',
                '/etc/inside/gate.conf',
                './config/gate.conf'
            ]
            
            for path in search_paths:
                if os.path.exists(path):
                    config_path = path
                    break
            
            if config_path is None:
                raise FileNotFoundError('gate.conf not found in standard locations')
        
        self.config_path = config_path
        self.config = configparser.ConfigParser()
        self.config.read(config_path)
        
        # Tower settings
        self.tower_url = self.config.get('tower', 'url')
        self.tower_token = self.config.get('tower', 'token')
        self.verify_ssl = self.config.getboolean('tower', 'verify_ssl', fallback=True)
        
        # Gate identification
        self.gate_name = self.config.get('gate', 'name', fallback='gate-unknown')
        self.hostname = self.config.get('gate', 'hostname', fallback=os.uname().nodename)
        self.location = self.config.get('gate', 'location', fallback='Unknown')
        self.version = self.config.get('gate', 'version', fallback='1.9.0')
        
        # Cache settings
        self.cache_enabled = self.config.getboolean('gate', 'cache_enabled', fallback=True)
        self.cache_ttl = self.config.getint('gate', 'cache_ttl', fallback=30)
        self.cache_path = self.config.get('gate', 'cache_path', fallback='/var/lib/inside-gate/cache.db')
        
        # Offline mode
        self.offline_mode_enabled = self.config.getboolean('gate', 'offline_mode_enabled', fallback=True)
        self.offline_cache_duration = self.config.getint('gate', 'offline_cache_duration', fallback=300)
        
        # Heartbeat settings
        self.heartbeat_interval = self.config.getint('gate', 'heartbeat_interval', fallback=30)
        self.heartbeat_timeout = self.config.getint('gate', 'heartbeat_timeout', fallback=10)
        
        # API client settings
        self.api_timeout = self.config.getint('api', 'timeout', fallback=10)
        self.api_retry_attempts = self.config.getint('api', 'retry_attempts', fallback=3)
        self.api_retry_backoff = self.config.getfloat('api', 'retry_backoff', fallback=2.0)
        
        # Logging settings
        self.log_level = self.config.get('logging', 'level', fallback='INFO')
        self.log_file = self.config.get('logging', 'file', fallback='/var/log/inside/gate.log')
        self.log_max_size = self.config.getint('logging', 'max_size', fallback=10485760)
        self.log_backup_count = self.config.getint('logging', 'backup_count', fallback=5)
    
    def __repr__(self):
        return f'<GateConfig gate_name={self.gate_name} tower_url={self.tower_url}>'
    
    @property
    def auth_header(self):
        """Get Authorization header value for Tower API requests."""
        return f'Bearer {self.tower_token}'


# Global config instance
_config = None


def get_config(config_path=None):
    """Get global Gate configuration instance.
    
    Args:
        config_path: Optional path to config file. Only used on first call.
    
    Returns:
        GateConfig instance
    """
    global _config
    if _config is None:
        _config = GateConfig(config_path)
    return _config
