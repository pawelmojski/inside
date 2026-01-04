"""CLI Commands for New Flexible Access Control System."""
import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from typing import Optional, List
from datetime import datetime, timedelta

app = typer.Typer(help="JumpHost V2 Access Control CLI")
console = Console()

# Import core modules
import sys
sys.path.append('/opt/jumphost')
from src.core.database import (
    SessionLocal, User, Server, UserSourceIP, ServerGroup, 
    ServerGroupMember, AccessPolicy, PolicySSHLogin
)


# ============================================================================
# USER SOURCE IPs MANAGEMENT
# ============================================================================

@app.command()
def add_user_ip(
    username: str = typer.Argument(..., help="Username"),
    source_ip: str = typer.Argument(..., help="Source IP address"),
    label: str = typer.Option(None, help="Label for this IP (e.g., 'Home', 'Office')"),
):
    """Add a source IP to a user."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            console.print(f"[red]Error: User {username} not found[/red]")
            raise typer.Exit(1)
        
        # Check if IP already exists for this user
        existing = db.query(UserSourceIP).filter(
            UserSourceIP.user_id == user.id,
            UserSourceIP.source_ip == source_ip
        ).first()
        
        if existing:
            console.print(f"[yellow]Warning: IP {source_ip} already assigned to {username}[/yellow]")
            raise typer.Exit(0)
        
        user_ip = UserSourceIP(
            user_id=user.id,
            source_ip=source_ip,
            label=label,
            is_active=True
        )
        db.add(user_ip)
        db.commit()
        
        console.print(f"[green]✓ Added IP {source_ip} to user {username}[/green]")
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        db.rollback()
        raise typer.Exit(1)
    finally:
        db.close()


@app.command()
def list_user_ips(
    username: Optional[str] = typer.Argument(None, help="Username (optional, lists all if not provided)")
):
    """List user source IPs."""
    db = SessionLocal()
    try:
        if username:
            user = db.query(User).filter(User.username == username).first()
            if not user:
                console.print(f"[red]Error: User {username} not found[/red]")
                raise typer.Exit(1)
            user_ips = db.query(UserSourceIP).filter(UserSourceIP.user_id == user.id).all()
        else:
            user_ips = db.query(UserSourceIP).all()
        
        table = Table(title=f"User Source IPs{f' for {username}' if username else ''}")
        table.add_column("ID", style="cyan")
        table.add_column("Username", style="green")
        table.add_column("Source IP", style="yellow")
        table.add_column("Label", style="magenta")
        table.add_column("Active", style="blue")
        
        for user_ip in user_ips:
            user_obj = db.query(User).filter(User.id == user_ip.user_id).first()
            table.add_row(
                str(user_ip.id),
                user_obj.username if user_obj else "Unknown",
                user_ip.source_ip,
                user_ip.label or "N/A",
                "✓" if user_ip.is_active else "✗"
            )
        
        console.print(table)
    finally:
        db.close()


@app.command()
def remove_user_ip(
    ip_id: int = typer.Argument(..., help="User source IP ID")
):
    """Remove (deactivate) a user source IP."""
    db = SessionLocal()
    try:
        user_ip = db.query(UserSourceIP).filter(UserSourceIP.id == ip_id).first()
        if not user_ip:
            console.print(f"[red]Error: User IP ID {ip_id} not found[/red]")
            raise typer.Exit(1)
        
        user_ip.is_active = False
        db.commit()
        
        console.print(f"[green]✓ Deactivated user IP {user_ip.source_ip}[/green]")
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        db.rollback()
        raise typer.Exit(1)
    finally:
        db.close()


# ============================================================================
# SERVER GROUPS MANAGEMENT
# ============================================================================

@app.command()
def create_group(
    name: str = typer.Argument(..., help="Group name"),
    description: str = typer.Option(None, help="Group description"),
):
    """Create a new server group."""
    db = SessionLocal()
    try:
        # Check if group exists
        existing = db.query(ServerGroup).filter(ServerGroup.name == name).first()
        if existing:
            console.print(f"[red]Error: Group {name} already exists[/red]")
            raise typer.Exit(1)
        
        group = ServerGroup(
            name=name,
            description=description
        )
        db.add(group)
        db.commit()
        
        console.print(f"[green]✓ Created group '{name}' (ID: {group.id})[/green]")
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        db.rollback()
        raise typer.Exit(1)
    finally:
        db.close()


@app.command()
def list_groups():
    """List all server groups."""
    db = SessionLocal()
    try:
        groups = db.query(ServerGroup).all()
        
        table = Table(title="Server Groups")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Description", style="yellow")
        table.add_column("Servers", style="magenta")
        
        for group in groups:
            member_count = db.query(ServerGroupMember).filter(
                ServerGroupMember.group_id == group.id
            ).count()
            
            table.add_row(
                str(group.id),
                group.name,
                group.description or "N/A",
                str(member_count)
            )
        
        console.print(table)
    finally:
        db.close()


@app.command()
def add_to_group(
    server_name: str = typer.Argument(..., help="Server name"),
    group_name: str = typer.Argument(..., help="Group name"),
):
    """Add a server to a group."""
    db = SessionLocal()
    try:
        server = db.query(Server).filter(Server.name == server_name).first()
        if not server:
            console.print(f"[red]Error: Server {server_name} not found[/red]")
            raise typer.Exit(1)
        
        group = db.query(ServerGroup).filter(ServerGroup.name == group_name).first()
        if not group:
            console.print(f"[red]Error: Group {group_name} not found[/red]")
            raise typer.Exit(1)
        
        # Check if already member
        existing = db.query(ServerGroupMember).filter(
            ServerGroupMember.server_id == server.id,
            ServerGroupMember.group_id == group.id
        ).first()
        
        if existing:
            console.print(f"[yellow]Warning: {server_name} already in group {group_name}[/yellow]")
            raise typer.Exit(0)
        
        member = ServerGroupMember(
            server_id=server.id,
            group_id=group.id
        )
        db.add(member)
        db.commit()
        
        console.print(f"[green]✓ Added {server_name} to group {group_name}[/green]")
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        db.rollback()
        raise typer.Exit(1)
    finally:
        db.close()


@app.command()
def remove_from_group(
    server_name: str = typer.Argument(..., help="Server name"),
    group_name: str = typer.Argument(..., help="Group name"),
):
    """Remove a server from a group."""
    db = SessionLocal()
    try:
        server = db.query(Server).filter(Server.name == server_name).first()
        if not server:
            console.print(f"[red]Error: Server {server_name} not found[/red]")
            raise typer.Exit(1)
        
        group = db.query(ServerGroup).filter(ServerGroup.name == group_name).first()
        if not group:
            console.print(f"[red]Error: Group {group_name} not found[/red]")
            raise typer.Exit(1)
        
        member = db.query(ServerGroupMember).filter(
            ServerGroupMember.server_id == server.id,
            ServerGroupMember.group_id == group.id
        ).first()
        
        if not member:
            console.print(f"[yellow]Warning: {server_name} not in group {group_name}[/yellow]")
            raise typer.Exit(0)
        
        db.delete(member)
        db.commit()
        
        console.print(f"[green]✓ Removed {server_name} from group {group_name}[/green]")
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        db.rollback()
        raise typer.Exit(1)
    finally:
        db.close()


@app.command()
def show_group(
    group_name: str = typer.Argument(..., help="Group name")
):
    """Show detailed information about a server group."""
    db = SessionLocal()
    try:
        group = db.query(ServerGroup).filter(ServerGroup.name == group_name).first()
        if not group:
            console.print(f"[red]Error: Group {group_name} not found[/red]")
            raise typer.Exit(1)
        
        members = db.query(ServerGroupMember).filter(
            ServerGroupMember.group_id == group.id
        ).all()
        
        console.print(f"\n[bold cyan]Group: {group.name}[/bold cyan]")
        console.print(f"Description: {group.description or 'N/A'}")
        console.print(f"Created: {group.created_at}")
        console.print(f"\n[bold]Servers in this group:[/bold]")
        
        if not members:
            console.print("  (none)")
        else:
            for member in members:
                server = db.query(Server).filter(Server.id == member.server_id).first()
                if server:
                    console.print(f"  - {server.name} ({server.ip_address})")
    finally:
        db.close()


# ============================================================================
# ACCESS POLICIES MANAGEMENT
# ============================================================================

@app.command()
def grant_policy(
    username: str = typer.Argument(..., help="Username"),
    scope: str = typer.Argument(..., help="Scope: 'group', 'server', or 'service'"),
    target: str = typer.Argument(..., help="Target group or server name"),
    duration_hours: int = typer.Option(8, help="Access duration in hours"),
    protocol: Optional[str] = typer.Option(None, help="Protocol: 'ssh', 'rdp', or None (all)"),
    source_ip: Optional[str] = typer.Option(None, help="Restrict to specific source IP (optional)"),
    ssh_logins: Optional[List[str]] = typer.Option(None, help="Allowed SSH logins (can specify multiple times)"),
    reason: Optional[str] = typer.Option(None, help="Reason for access"),
):
    """Grant access policy to a user.
    
    Examples:
        # Full group access (SSH + RDP)
        grant-policy john group "Production Servers" --duration-hours 8
        
        # Group SSH only, specific login
        grant-policy mary group "Database Servers" --protocol ssh --ssh-logins root
        
        # Single server, multiple logins
        grant-policy bob server bastion-01 --protocol ssh --ssh-logins deploy --ssh-logins monitoring
        
        # RDP to specific server
        grant-policy alice service windows-app-01 --protocol rdp --duration-hours 24
    """
    db = SessionLocal()
    try:
        # Validate scope
        if scope not in ['group', 'server', 'service']:
            console.print(f"[red]Error: scope must be 'group', 'server', or 'service'[/red]")
            raise typer.Exit(1)
        
        # Validate protocol
        if protocol and protocol not in ['ssh', 'rdp']:
            console.print(f"[red]Error: protocol must be 'ssh', 'rdp', or None[/red]")
            raise typer.Exit(1)
        
        # Find user
        user = db.query(User).filter(User.username == username).first()
        if not user:
            console.print(f"[red]Error: User {username} not found[/red]")
            raise typer.Exit(1)
        
        # Find source_ip_id if specified
        source_ip_id = None
        if source_ip:
            user_ip = db.query(UserSourceIP).filter(
                UserSourceIP.user_id == user.id,
                UserSourceIP.source_ip == source_ip
            ).first()
            if not user_ip:
                console.print(f"[red]Error: Source IP {source_ip} not registered for {username}[/red]")
                raise typer.Exit(1)
            source_ip_id = user_ip.id
        
        # Find target (group or server)
        target_group_id = None
        target_server_id = None
        
        if scope == 'group':
            group = db.query(ServerGroup).filter(ServerGroup.name == target).first()
            if not group:
                console.print(f"[red]Error: Group {target} not found[/red]")
                raise typer.Exit(1)
            target_group_id = group.id
        else:  # server or service
            server = db.query(Server).filter(Server.name == target).first()
            if not server:
                console.print(f"[red]Error: Server {target} not found[/red]")
                raise typer.Exit(1)
            target_server_id = server.id
        
        # Create policy
        now = datetime.utcnow()
        end_time = now + timedelta(hours=duration_hours)
        
        policy = AccessPolicy(
            user_id=user.id,
            source_ip_id=source_ip_id,
            scope_type=scope,
            target_group_id=target_group_id,
            target_server_id=target_server_id,
            protocol=protocol,
            start_time=now,
            end_time=end_time,
            is_active=True,
            reason=reason
        )
        db.add(policy)
        db.flush()  # Get policy.id
        
        # Add SSH login restrictions if specified
        if ssh_logins:
            for login in ssh_logins:
                ssh_login = PolicySSHLogin(
                    policy_id=policy.id,
                    allowed_login=login
                )
                db.add(ssh_login)
        
        db.commit()
        
        console.print(f"[green]✓ Granted policy #{policy.id} to {username}[/green]")
        console.print(f"  Scope: {scope} → {target}")
        console.print(f"  Protocol: {protocol or 'ALL'}")
        console.print(f"  Duration: {duration_hours}h (expires: {end_time})")
        if source_ip:
            console.print(f"  Source IP: {source_ip}")
        if ssh_logins:
            console.print(f"  SSH Logins: {', '.join(ssh_logins)}")
        
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        db.rollback()
        raise typer.Exit(1)
    finally:
        db.close()


@app.command()
def list_policies(
    username: Optional[str] = typer.Argument(None, help="Username (optional)"),
    active_only: bool = typer.Option(True, help="Show only active policies"),
):
    """List access policies."""
    db = SessionLocal()
    try:
        query = db.query(AccessPolicy)
        
        if username:
            user = db.query(User).filter(User.username == username).first()
            if not user:
                console.print(f"[red]Error: User {username} not found[/red]")
                raise typer.Exit(1)
            query = query.filter(AccessPolicy.user_id == user.id)
        
        if active_only:
            now = datetime.utcnow()
            query = query.filter(
                AccessPolicy.is_active == True,
                AccessPolicy.start_time <= now,
                AccessPolicy.end_time >= now
            )
        
        policies = query.all()
        
        table = Table(title=f"Access Policies{f' for {username}' if username else ''}")
        table.add_column("ID", style="cyan")
        table.add_column("User", style="green")
        table.add_column("Scope", style="yellow")
        table.add_column("Target", style="magenta")
        table.add_column("Protocol", style="blue")
        table.add_column("Expires", style="red")
        table.add_column("SSH Logins", style="white")
        
        for policy in policies:
            user_obj = db.query(User).filter(User.id == policy.user_id).first()
            
            # Get target name
            if policy.scope_type == 'group':
                group = db.query(ServerGroup).filter(ServerGroup.id == policy.target_group_id).first()
                target_name = group.name if group else "Unknown"
            else:
                server = db.query(Server).filter(Server.id == policy.target_server_id).first()
                target_name = server.name if server else "Unknown"
            
            # Get SSH logins
            ssh_logins_list = db.query(PolicySSHLogin).filter(PolicySSHLogin.policy_id == policy.id).all()
            ssh_logins_str = ", ".join([l.allowed_login for l in ssh_logins_list]) if ssh_logins_list else "ALL"
            
            # Expiry status
            now = datetime.utcnow()
            if policy.end_time < now:
                expiry = f"EXPIRED ({policy.end_time})"
            else:
                remaining = policy.end_time - now
                hours = int(remaining.total_seconds() / 3600)
                expiry = f"{hours}h remaining"
            
            table.add_row(
                str(policy.id),
                user_obj.username if user_obj else "Unknown",
                policy.scope_type,
                target_name,
                policy.protocol or "ALL",
                expiry,
                ssh_logins_str if policy.protocol in ('ssh', None) else "N/A"
            )
        
        console.print(table)
        
        if not policies:
            console.print("[yellow]No policies found[/yellow]")
        
    finally:
        db.close()


@app.command()
def revoke_policy(
    policy_id: int = typer.Argument(..., help="Policy ID to revoke")
):
    """Revoke (deactivate) an access policy."""
    db = SessionLocal()
    try:
        policy = db.query(AccessPolicy).filter(AccessPolicy.id == policy_id).first()
        if not policy:
            console.print(f"[red]Error: Policy ID {policy_id} not found[/red]")
            raise typer.Exit(1)
        
        policy.is_active = False
        db.commit()
        
        console.print(f"[green]✓ Revoked policy #{policy_id}[/green]")
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        db.rollback()
        raise typer.Exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    app()
