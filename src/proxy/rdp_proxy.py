#!/usr/bin/env python3
"""
RDP Proxy Server using PyRDP MITM with dynamic backend routing
"""

import logging
import sys
import os
from pathlib import Path
from datetime import datetime
import asyncio
from twisted.internet import asyncioreactor
asyncioreactor.install(asyncio.new_event_loop())

import socket
from twisted.internet import reactor, tcp
from twisted.internet.protocol import Factory
from pyrdp.core.mitm import MITMServerFactory
from pyrdp.mitm.config import MITMConfig
from pyrdp.logging import LOGGER_NAMES

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import SessionLocal, AuditLog
from core.access_control_v2 import AccessControlEngineV2

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/jumphost/rdp_proxy.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('rdp_proxy')


class JumpHostPort(tcp.Port):
    """Custom Port that extracts destination IP and passes it to factory"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    def doRead(self):
        """Override to capture connection info"""
        return super().doRead()


class JumpHostMITMFactory(MITMServerFactory):
    """
    Custom PyRDP factory with dynamic backend routing and access control
    """
    
    def __init__(self, config: MITMConfig):
        super().__init__(config)
        self.access_control = AccessControlEngineV2()
        self._backend_cache = {}  # Cache backend per source IP to avoid repeated lookups
        logger.info("JumpHostMITMFactory initialized with dynamic routing")
    
    def buildProtocol(self, addr):
        """
        Build protocol for incoming connection with access control check
        
        Extracts destination IP from listening socket to determine backend
        """
        source_ip = addr.host
        
        # Get destination IP from the listening port
        # We need to get this from the accepted socket, which we'll do via the protocol
        logger.info(f"New RDP connection attempt from {source_ip}")
        
        # Create protocol and let it handle the destination IP extraction
        protocol = super().buildProtocol(addr)
        
        if protocol:
            # Wrap protocol to inject our access control logic
            original_connection_made = protocol.connectionMade
            
            def wrapped_connection_made():
                # Extract destination IP from transport
                try:
                    sock = protocol.transport.socket
                    dest_ip = sock.getsockname()[0]
                    
                    logger.info(f"Connection from {source_ip} to {dest_ip}")
                    
                    # Perform access control check
                    db = SessionLocal()
                    try:
                        # Find backend by destination IP
                        backend_lookup = self.access_control.find_backend_by_proxy_ip(db, dest_ip)
                        if not backend_lookup:
                            logger.error(f"No backend server found for destination IP {dest_ip}")
                            protocol.transport.loseConnection()
                            return
                        
                        backend_server = backend_lookup['server']
                        logger.info(f"Destination IP {dest_ip} maps to backend {backend_server.ip_address}")
                        
                        # Check access control with V2 engine
                        result = self.access_control.check_access_v2(
                            db, 
                            source_ip, 
                            dest_ip,
                            'rdp'  # Protocol filter
                        )
                        
                        if not result['has_access']:
                            reason = result['reason']
                            logger.warning(f"ACCESS DENIED: {source_ip} - {reason}")
                            
                            # Audit log
                            audit = AuditLog(
                                action='rdp_access_denied',
                                source_ip=source_ip,
                                resource_type='rdp_server',
                                details=f"Access denied: {reason}",
                                success=False
                            )
                            db.add(audit)
                            db.commit()
                            
                            protocol.transport.loseConnection()
                            return
                        
                        user = result['user']
                        backend_server_from_policy = result['server']
                        
                        # V2 already verified the server matches, no need to double-check
                        logger.info(f"ACCESS GRANTED: {user.username} ({source_ip}) -> {backend_server_from_policy.ip_address}")
                        logger.info(f"Policy: {result.get('policy_count', 0)} matching policies")
                        
                        # Update config to target correct backend
                        self.config.targetHost = backend_server_from_policy.ip_address
                        self.config.targetPort = 3389
                        
                        # Audit log
                        audit = AuditLog(
                            action='rdp_access_granted',
                            source_ip=source_ip,
                            user_id=user.id,
                            resource_type='rdp_server',
                            resource_id=backend_server_from_policy.id,
                            details=f"User {user.username} connected to {backend_server_from_policy.ip_address} via {dest_ip}",
                            success=True
                        )
                        db.add(audit)
                        db.commit()
                        
                    except Exception as e:
                        logger.error(f"Error in access control: {e}", exc_info=True)
                        protocol.transport.loseConnection()
                        return
                    finally:
                        db.close()
                    
                    # Continue with original connection
                    original_connection_made()
                    
                except Exception as e:
                    logger.error(f"Error extracting destination IP: {e}", exc_info=True)
                    protocol.transport.loseConnection()
            
            protocol.connectionMade = wrapped_connection_made
        
        return protocol


def create_rdp_proxy_config() -> MITMConfig:
    """Create PyRDP MITM configuration for jump host"""
    config = MITMConfig()
    
    # Listen configuration - listen on ALL interfaces for dynamic routing
    config.listenAddress = '0.0.0.0'
    config.listenPort = 3389
    
    # Target configuration - will be set dynamically per connection
    config.targetHost = '127.0.0.1'  # Placeholder, set dynamically
    config.targetPort = 3389
    
    # Disable TLS requirement for testing
    config.downgrade = True  # Allow downgrade to non-TLS
    
    # Recording configuration
    recordings_dir = Path('/var/log/jumphost/rdp_recordings')
    recordings_dir.mkdir(parents=True, exist_ok=True)
    config.outDir = recordings_dir  # This sets replayDir, fileDir, etc
    config.recordReplays = True
    
    # Crawler disabled for now
    config.enableCrawler = False
    
    # SSL certificates (auto-generated if not exist)
    cert_dir = Path('/opt/jumphost/certs')
    cert_dir.mkdir(parents=True, exist_ok=True)
    config.privateKeyFileName = str(cert_dir / 'rdp_private_key.pem')
    config.certificateFileName = str(cert_dir / 'rdp_certificate.pem')
    
    return config


def main():
    """Start RDP proxy with PyRDP MITM"""
    logger.info("=" * 60)
    logger.info("Starting Jump Host RDP Proxy (PyRDP MITM)")
    logger.info("=" * 60)
    
    config = create_rdp_proxy_config()
    factory = JumpHostMITMFactory(config)
    
    # Create listening socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setblocking(0)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((config.listenAddress, config.listenPort))
    s.listen()
    
    reactor.adoptStreamPort(s.fileno(), socket.AF_INET, factory)
    s.close()  # reactor creates a copy of the fd
    
    logger.info(f"RDP Proxy listening on {config.listenAddress}:{config.listenPort}")
    logger.info(f"Recordings directory: {config.replayDir}")
    logger.info("Dynamic backend routing enabled via destination IP extraction")
    logger.info("Access control integrated: checks source IP and grants")
    
    # Start reactor
    reactor.run()
    
    logger.info("RDP Proxy terminated")


if __name__ == '__main__':
    main()
