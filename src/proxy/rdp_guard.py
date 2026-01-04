#!/usr/bin/env python3
"""
RDP Guard Proxy - Access control gateway before PyRDP MITM

This proxy sits in front of PyRDP and enforces access control based on source IP.
Architecture:
- Client -> RDP Guard (10.0.160.129:3389) -> PyRDP MITM (localhost:13389) -> Backend
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import SessionLocal
from core.access_control_v2 import AccessControlEngineV2
from core.database import AuditLog

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/jumphost/rdp_guard.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('rdp_guard')


class RDPGuardProxy:
    """TCP proxy with access control for RDP"""
    
    def __init__(self, listen_host: str, listen_port: int, 
                 pyrdp_host: str, pyrdp_port: int):
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.pyrdp_host = pyrdp_host
        self.pyrdp_port = pyrdp_port
        self.access_control = AccessControlEngineV2()
    
    async def handle_client(self, client_reader, client_writer):
        """Handle incoming client connection with access control"""
        
        client_addr = client_writer.get_extra_info('peername')
        source_ip = client_addr[0]
        source_port = client_addr[1]
        
        # NEW: Extract destination IP (the IP client connected to)
        sock = client_writer.get_extra_info('socket')
        dest_ip = sock.getsockname()[0]
        
        logger.info(f"New RDP connection attempt from {source_ip}:{source_port} to {dest_ip}")
        
        # First, find backend server by destination IP
        db = SessionLocal()
        try:
            backend_lookup = self.access_control.find_backend_by_proxy_ip(db, dest_ip)
            if not backend_lookup:
                logger.error(f"No backend server found for destination IP {dest_ip}")
                
                # Log to audit
                audit = AuditLog(
                    action='rdp_access_denied',
                    source_ip=source_ip,
                    resource_type='rdp_server',
                    details=f"No backend configured for proxy IP {dest_ip}",
                    success=False
                )
                db.add(audit)
                db.commit()
                
                # Send rejection
                try:
                    reject_msg = f"ACCESS DENIED\nNo backend server configured for {dest_ip}\nContact administrator.\n"
                    client_writer.write(reject_msg.encode('utf-8'))
                    await client_writer.drain()
                    await asyncio.sleep(0.5)
                    client_writer.close()
                    await client_writer.wait_closed()
                except Exception as e:
                    logger.debug(f"Error sending rejection: {e}")
                
                return
            
            backend_server = backend_lookup['server']
            logger.info(f"Destination IP {dest_ip} maps to backend {backend_server.ip_address}")
            
            # Check access control using V2 engine
            result = self.access_control.check_access_v2(db, source_ip, dest_ip, 'rdp', ssh_login=None)
            
            if not result['has_access']:
                reason = result['reason']
                logger.warning(f"ACCESS DENIED: {source_ip} - {reason}")
                
                # Log to audit
                audit = AuditLog(
                    action='rdp_access_denied',
                    source_ip=source_ip,
                    resource_type='rdp_server',
                    details=f"Access denied from {source_ip}: {reason}",
                    success=False
                )
                db.add(audit)
                db.commit()
                
                # Send rejection message and close
                try:
                    # Send ASCII message (for telnet debugging, RDP client will ignore)
                    reject_msg = f"ACCESS DENIED\nSource IP: {source_ip}\nReason: {reason}\nContact administrator for access.\n"
                    client_writer.write(reject_msg.encode('utf-8'))
                    await client_writer.drain()
                    await asyncio.sleep(0.5)  # Give time to send
                    client_writer.close()
                    await client_writer.wait_closed()
                except Exception as e:
                    logger.debug(f"Error sending rejection: {e}")
                
                return
            
            # Access granted - but verify it's for THIS backend server
            user = result['user']
            grant_server = result['server']
            grant = result['grant']
            
            # CRITICAL: Check if the grant is for the correct backend
            if grant_server.id != backend_server.id:
                reason = f"Grant is for {grant_server.ip_address}, but connected to proxy for {backend_server.ip_address}"
                logger.warning(f"ACCESS DENIED: {user.username} ({source_ip}) - {reason}")
                
                # Log to audit
                audit = AuditLog(
                    action='rdp_access_denied',
                    source_ip=source_ip,
                    resource_type='rdp_server',
                    details=f"User {user.username} tried to access {backend_server.ip_address} (via {dest_ip}) but grant is for {grant_server.ip_address}",
                    success=False
                )
                db.add(audit)
                db.commit()
                
                # Send rejection
                try:
                    reject_msg = f"ACCESS DENIED\nSource IP: {source_ip}\nUser: {user.username}\nReason: {reason}\nContact administrator.\n"
                    client_writer.write(reject_msg.encode('utf-8'))
                    await client_writer.drain()
                    await asyncio.sleep(0.5)
                    client_writer.close()
                    await client_writer.wait_closed()
                except Exception as e:
                    logger.debug(f"Error sending rejection: {e}")
                
                return
            
            logger.info(f"ACCESS GRANTED: {user.username} (source {source_ip}) -> Server {backend_server.ip_address} (via {dest_ip})")
            logger.info(f"Grant expires: {grant.end_time}")
            
            # Log to audit
            audit = AuditLog(
                action='rdp_access_granted',
                source_ip=source_ip,
                resource_type='rdp_server',
                resource_id=backend_server.id,
                details=f"User {user.username} connected to {backend_server.ip_address} via proxy {dest_ip}, grant expires {grant.end_time}",
                success=True
            )
            db.add(audit)
            db.commit()
            
        except Exception as e:
            logger.error(f"Error checking access for {source_ip}: {e}", exc_info=True)
            client_writer.close()
            await client_writer.wait_closed()
            return
        finally:
            db.close()
        
        # Connect to PyRDP backend
        try:
            backend_reader, backend_writer = await asyncio.open_connection(
                self.pyrdp_host, self.pyrdp_port
            )
            logger.info(f"Connected to PyRDP backend for {source_ip}")
        except Exception as e:
            logger.error(f"Failed to connect to PyRDP backend: {e}")
            client_writer.close()
            await client_writer.wait_closed()
            return
        
        # Start bidirectional forwarding
        try:
            await asyncio.gather(
                self.forward(client_reader, backend_writer, f"{source_ip}->PyRDP"),
                self.forward(backend_reader, client_writer, f"PyRDP->{source_ip}")
            )
        except Exception as e:
            logger.error(f"Error during forwarding for {source_ip}: {e}")
        finally:
            client_writer.close()
            backend_writer.close()
            try:
                await client_writer.wait_closed()
                await backend_writer.wait_closed()
            except:
                pass
            logger.info(f"Connection closed for {source_ip}")
    
    async def forward(self, reader, writer, direction: str):
        """Forward data from reader to writer"""
        try:
            while True:
                data = await reader.read(8192)
                if not data:
                    break
                writer.write(data)
                await writer.drain()
        except Exception as e:
            logger.debug(f"Forward {direction} ended: {e}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except:
                pass
    
    async def start(self):
        """Start the guard proxy server"""
        server = await asyncio.start_server(
            self.handle_client,
            self.listen_host,
            self.listen_port
        )
        
        addr = server.sockets[0].getsockname()
        logger.info("=" * 60)
        logger.info("RDP Guard Proxy Started")
        logger.info("=" * 60)
        logger.info("=" * 60)
        logger.info("RDP Guard Proxy Started")
        logger.info("=" * 60)
        logger.info(f"Listening on: {addr[0]}:{addr[1]}")
        logger.info(f"PyRDP backend: {self.pyrdp_host}:{self.pyrdp_port}")
        logger.info("Access control: ENABLED (source IP based)")
        logger.info("Backend routing: DYNAMIC (via ip_allocations)")
        logger.info("=" * 60)
        
        async with server:
            await server.serve_forever()


async def main():
    """Start RDP guard proxy"""
    guard = RDPGuardProxy(
        listen_host='0.0.0.0',  # Listen on all interfaces
        listen_port=3389,
        pyrdp_host='127.0.0.1',
        pyrdp_port=13389
    )
    
    await guard.start()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("RDP Guard Proxy stopped by user")
