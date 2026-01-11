"""NAT and routing manager for dynamic IP forwarding."""
import subprocess
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


class NATManager:
    """Manages iptables NAT rules for dynamic port forwarding."""
    
    def __init__(self):
        """Initialize NAT manager."""
        self.rules = []  # Track active rules for cleanup
    
    def add_nat_rule(
        self,
        allocated_ip: str,
        target_ip: str,
        protocol: str = "ssh"
    ) -> bool:
        """
        Add NAT rules to forward traffic from allocated IP to target server.
        
        Args:
            allocated_ip: IP from pool (e.g., 10.0.160.129)
            target_ip: Target server IP (e.g., 10.210.1.156)
            protocol: 'ssh' (port 22) or 'rdp' (port 3389)
            
        Returns:
            True if rules added successfully
        """
        try:
            if protocol == "ssh":
                port = 22
            elif protocol == "rdp":
                port = 3389
            else:
                logger.error(f"Unknown protocol: {protocol}")
                return False
            
            # DNAT rule: incoming traffic to allocated_ip:port -> target_ip:port
            dnat_cmd = [
                "iptables", "-t", "nat", "-A", "PREROUTING",
                "-d", allocated_ip,
                "-p", "tcp", "--dport", str(port),
                "-j", "DNAT", "--to-destination", f"{target_ip}:{port}"
            ]
            
            # SNAT rule: outgoing traffic appears to come from jump host
            snat_cmd = [
                "iptables", "-t", "nat", "-A", "POSTROUTING",
                "-d", target_ip,
                "-p", "tcp", "--dport", str(port),
                "-j", "MASQUERADE"
            ]
            
            # FORWARD rule: allow forwarding
            forward_cmd = [
                "iptables", "-A", "FORWARD",
                "-d", target_ip,
                "-p", "tcp", "--dport", str(port),
                "-j", "ACCEPT"
            ]
            
            # Execute commands
            subprocess.run(["sudo"] + dnat_cmd, check=True, capture_output=True)
            subprocess.run(["sudo"] + snat_cmd, check=True, capture_output=True)
            subprocess.run(["sudo"] + forward_cmd, check=True, capture_output=True)
            
            # Track rule for cleanup
            rule_id = f"{allocated_ip}:{port}->{target_ip}:{port}"
            self.rules.append(rule_id)
            
            logger.info(f"Added NAT rules: {rule_id}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to add NAT rules: {e.stderr.decode() if e.stderr else str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error adding NAT rules: {str(e)}")
            return False
    
    def remove_nat_rule(
        self,
        allocated_ip: str,
        target_ip: str,
        protocol: str = "ssh"
    ) -> bool:
        """
        Remove NAT rules.
        
        Args:
            allocated_ip: IP from pool
            target_ip: Target server IP
            protocol: 'ssh' or 'rdp'
            
        Returns:
            True if rules removed successfully
        """
        try:
            if protocol == "ssh":
                port = 22
            elif protocol == "rdp":
                port = 3389
            else:
                return False
            
            # Remove DNAT rule
            dnat_cmd = [
                "iptables", "-t", "nat", "-D", "PREROUTING",
                "-d", allocated_ip,
                "-p", "tcp", "--dport", str(port),
                "-j", "DNAT", "--to-destination", f"{target_ip}:{port}"
            ]
            
            # Remove SNAT rule
            snat_cmd = [
                "iptables", "-t", "nat", "-D", "POSTROUTING",
                "-d", target_ip,
                "-p", "tcp", "--dport", str(port),
                "-j", "MASQUERADE"
            ]
            
            # Remove FORWARD rule
            forward_cmd = [
                "iptables", "-D", "FORWARD",
                "-d", target_ip,
                "-p", "tcp", "--dport", str(port),
                "-j", "ACCEPT"
            ]
            
            # Execute commands (ignore errors if rule doesn't exist)
            subprocess.run(["sudo"] + dnat_cmd, capture_output=True)
            subprocess.run(["sudo"] + snat_cmd, capture_output=True)
            subprocess.run(["sudo"] + forward_cmd, capture_output=True)
            
            rule_id = f"{allocated_ip}:{port}->{target_ip}:{port}"
            if rule_id in self.rules:
                self.rules.remove(rule_id)
            
            logger.info(f"Removed NAT rules: {rule_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing NAT rules: {str(e)}")
            return False
    
    def list_active_rules(self) -> List[str]:
        """List all NAT rules created by this manager."""
        return self.rules.copy()
    
    def flush_nat_rules(self) -> bool:
        """
        Flush all NAT rules (use with caution!).
        
        Returns:
            True if flushed successfully
        """
        try:
            subprocess.run(["sudo", "iptables", "-t", "nat", "-F"], check=True)
            subprocess.run(["sudo", "iptables", "-F", "FORWARD"], check=True)
            self.rules.clear()
            logger.warning("Flushed all NAT rules")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to flush NAT rules: {e}")
            return False
    
    def save_rules(self) -> bool:
        """Save current iptables rules to persist across reboots."""
        try:
            subprocess.run(
                ["sudo", "iptables-save"],
                stdout=open("/etc/iptables/rules.v4", "w"),
                check=True
            )
            logger.info("Saved iptables rules")
            return True
        except Exception as e:
            logger.error(f"Failed to save iptables rules: {e}")
            return False


# Singleton instance
nat_manager = NATManager()


if __name__ == "__main__":
    """Test NAT manager."""
    logging.basicConfig(level=logging.INFO)
    
    manager = NATManager()
    
    # Test adding rule
    print("Adding test NAT rule...")
    success = manager.add_nat_rule(
        allocated_ip="10.0.160.129",
        target_ip="10.210.1.156",
        protocol="ssh"
    )
    print(f"Add rule success: {success}")
    
    # List rules
    print(f"\nActive rules: {manager.list_active_rules()}")
    
    # Note: Cleanup would be done when IP is released
    # manager.remove_nat_rule("10.0.160.129", "10.210.1.156", "ssh")
