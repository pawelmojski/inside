"""CLI Management Tool for JumpHost."""
import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from typing import Optional
from datetime import datetime

app = typer.Typer(help="JumpHost Management CLI")
console = Console()

# Import core modules
import sys
sys.path.append('/opt/jumphost')
from src.core.database import SessionLocal, User, Server, AccessGrant, IPAllocation
from src.core.ip_pool import ip_pool_manager
from src.core.access_control import access_control


@app.command()
def pool_status():
    """Show IP pool status."""
    db = SessionLocal()
    try:
        status = ip_pool_manager.get_pool_status(db)
        
        table = Table(title="IP Pool Status")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        for key, value in status.items():
            table.add_row(key.replace("_", " ").title(), str(value))
        
        console.print(table)
    finally:
        db.close()


@app.command()
def add_user(
    username: str = typer.Argument(..., help="Username"),
    email: str = typer.Option(None, help="Email address"),
    full_name: str = typer.Option(None, help="Full name")
):
    """Add a new user to the database."""
    db = SessionLocal()
    try:
        # Check if user exists
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            console.print(f"[red]Error: User {username} already exists[/red]")
            raise typer.Exit(1)
        
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            is_active=True
        )
        db.add(user)
        db.commit()
        
        console.print(f"[green]✓ User {username} added successfully[/green]")
    except Exception as e:
        console.print(f"[red]Error adding user: {str(e)}[/red]")
        db.rollback()
        raise typer.Exit(1)
    finally:
        db.close()


@app.command()
def list_users():
    """List all users."""
    db = SessionLocal()
    try:
        users = db.query(User).all()
        
        table = Table(title="Users")
        table.add_column("ID", style="cyan")
        table.add_column("Username", style="green")
        table.add_column("Email", style="yellow")
        table.add_column("Full Name", style="magenta")
        table.add_column("Active", style="blue")
        
        for user in users:
            table.add_row(
                str(user.id),
                user.username,
                user.email or "N/A",
                user.full_name or "N/A",
                "✓" if user.is_active else "✗"
            )
        
        console.print(table)
    finally:
        db.close()


@app.command()
def add_server(
    name: str = typer.Argument(..., help="Server name"),
    ip_address: str = typer.Argument(..., help="Server IP address"),
    os_type: str = typer.Option("linux", help="OS type (linux/windows)"),
    description: str = typer.Option(None, help="Server description")
):
    """Add a new server to the database."""
    db = SessionLocal()
    try:
        # Check if server exists
        existing = db.query(Server).filter(Server.ip_address == ip_address).first()
        if existing:
            console.print(f"[red]Error: Server with IP {ip_address} already exists[/red]")
            raise typer.Exit(1)
        
        server = Server(
            name=name,
            ip_address=ip_address,
            os_type=os_type,
            description=description,
            is_active=True
        )
        db.add(server)
        db.commit()
        
        console.print(f"[green]✓ Server {name} ({ip_address}) added successfully[/green]")
    except Exception as e:
        console.print(f"[red]Error adding server: {str(e)}[/red]")
        db.rollback()
        raise typer.Exit(1)
    finally:
        db.close()


@app.command()
def list_servers():
    """List all servers."""
    db = SessionLocal()
    try:
        servers = db.query(Server).all()
        
        table = Table(title="Servers")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("IP Address", style="yellow")
        table.add_column("OS Type", style="magenta")
        table.add_column("Active", style="blue")
        
        for server in servers:
            table.add_row(
                str(server.id),
                server.name,
                server.ip_address,
                server.os_type or "N/A",
                "✓" if server.is_active else "✗"
            )
        
        console.print(table)
    finally:
        db.close()


@app.command()
def grant_access(
    username: str = typer.Argument(..., help="Username to grant access"),
    server_ip: str = typer.Argument(..., help="Target server IP"),
    protocol: str = typer.Option("ssh", help="Protocol (ssh/rdp)"),
    duration: int = typer.Option(60, help="Duration in minutes"),
    granted_by: str = typer.Option("admin", help="Who is granting access"),
    reason: str = typer.Option(None, help="Reason for granting access")
):
    """Grant access to a user for a server."""
    db = SessionLocal()
    try:
        success, message = access_control.grant_access(
            db=db,
            username=username,
            server_ip=server_ip,
            protocol=protocol,
            duration_minutes=duration,
            granted_by=granted_by,
            reason=reason
        )
        
        if success:
            console.print(f"[green]✓ {message}[/green]")
        else:
            console.print(f"[red]✗ {message}[/red]")
            raise typer.Exit(1)
    finally:
        db.close()


@app.command()
def revoke_access(
    username: str = typer.Argument(..., help="Username to revoke access"),
    server_ip: str = typer.Argument(..., help="Target server IP"),
    protocol: str = typer.Option("ssh", help="Protocol (ssh/rdp)"),
    revoked_by: str = typer.Option("admin", help="Who is revoking access")
):
    """Revoke access from a user for a server."""
    db = SessionLocal()
    try:
        success, message = access_control.revoke_access(
            db=db,
            username=username,
            server_ip=server_ip,
            protocol=protocol,
            revoked_by=revoked_by
        )
        
        if success:
            console.print(f"[green]✓ {message}[/green]")
        else:
            console.print(f"[red]✗ {message}[/red]")
            raise typer.Exit(1)
    finally:
        db.close()


@app.command()
def list_grants(active_only: bool = typer.Option(True, help="Show only active grants")):
    """List access grants."""
    db = SessionLocal()
    try:
        query = db.query(AccessGrant).join(User).join(Server)
        
        if active_only:
            now = datetime.utcnow()
            query = query.filter(
                AccessGrant.is_active == True,
                AccessGrant.end_time >= now
            )
        
        grants = query.all()
        
        table = Table(title="Access Grants")
        table.add_column("ID", style="cyan")
        table.add_column("User", style="green")
        table.add_column("Server", style="yellow")
        table.add_column("Protocol", style="magenta")
        table.add_column("Expires", style="red")
        table.add_column("Active", style="blue")
        
        for grant in grants:
            table.add_row(
                str(grant.id),
                grant.user.username,
                f"{grant.server.name} ({grant.server.ip_address})",
                grant.protocol,
                grant.end_time.strftime("%Y-%m-%d %H:%M"),
                "✓" if grant.is_active else "✗"
            )
        
        console.print(table)
    finally:
        db.close()


@app.command()
def list_allocations():
    """List active IP allocations."""
    db = SessionLocal()
    try:
        allocations = db.query(IPAllocation).filter(
            IPAllocation.is_active == True
        ).all()
        
        table = Table(title="IP Allocations")
        table.add_column("Allocated IP", style="cyan")
        table.add_column("Source IP", style="green")
        table.add_column("Server ID", style="yellow")
        table.add_column("User ID", style="magenta")
        table.add_column("Expires", style="red")
        
        for alloc in allocations:
            table.add_row(
                alloc.allocated_ip,
                alloc.source_ip or "-",
                str(alloc.server_id),
                str(alloc.user_id) if alloc.user_id else "-",
                alloc.expires_at.strftime("%Y-%m-%d %H:%M") if alloc.expires_at else "Never (Permanent)"
            )
        
        console.print(table)
    finally:
        db.close()


@app.command()
def cleanup_expired():
    """Cleanup expired IP allocations."""
    db = SessionLocal()
    try:
        count = ip_pool_manager.cleanup_expired(db)
        console.print(f"[green]✓ Cleaned up {count} expired allocation(s)[/green]")
    finally:
        db.close()


@app.command()
def assign_proxy_ip(
    server_name: str = typer.Argument(..., help="Server name or IP"),
    proxy_ip: str = typer.Option(None, help="Specific proxy IP to assign (or auto-allocate)")
):
    """
    Assign a proxy IP to a server from the IP pool.
    
    This allocates an IP from the pool (10.0.160.128/25) and configures it
    on the network interface so clients can connect to it.
    """
    import subprocess
    db = SessionLocal()
    try:
        # Find server by name or IP
        server = db.query(Server).filter(
            (Server.name == server_name) | (Server.ip_address == server_name)
        ).first()
        
        if not server:
            console.print(f"[red]Error: Server '{server_name}' not found[/red]")
            raise typer.Exit(1)
        
        # Check if already has proxy IP
        existing = db.query(IPAllocation).filter(
            IPAllocation.server_id == server.id,
            IPAllocation.is_active == True
        ).first()
        
        if existing:
            console.print(f"[yellow]Warning: Server already has proxy IP {existing.allocated_ip}[/yellow]")
            console.print(f"Use remove-proxy-ip first to deallocate")
            raise typer.Exit(1)
        
        # Allocate IP (permanent assignment for server)
        allocated_ip = ip_pool_manager.allocate_permanent_ip(
            db=db,
            server_id=server.id,
            specific_ip=proxy_ip  # None for auto-allocate, or specific IP
        )
        
        if not allocated_ip:
            if proxy_ip:
                console.print(f"[red]Error: IP {proxy_ip} is not available (already allocated or out of pool range)[/red]")
            else:
                console.print(f"[red]Error: No available IPs in pool[/red]")
            raise typer.Exit(1)
        
        # Configure IP on network interface
        interface = 'ens18'  # Adjust if needed
        try:
            subprocess.run(
                ['ip', 'addr', 'add', f'{allocated_ip}/32', 'dev', interface],
                check=True,
                capture_output=True
            )
            console.print(f"[green]✓ Configured IP {allocated_ip} on interface {interface}[/green]")
        except subprocess.CalledProcessError as e:
            if b'File exists' in e.stderr:
                console.print(f"[yellow]IP {allocated_ip} already configured on interface[/yellow]")
            else:
                console.print(f"[red]Warning: Failed to configure IP: {e.stderr.decode()}[/red]")
                console.print(f"[yellow]Manual config needed: sudo ip addr add {allocated_ip}/32 dev {interface}[/yellow]")
        
        console.print(f"[green]✓ Proxy IP {allocated_ip} assigned to server {server.name} ({server.ip_address})[/green]")
        console.print(f"[cyan]Clients can now connect to: {allocated_ip}:22 (SSH) or {allocated_ip}:3389 (RDP)[/cyan]")
        
    finally:
        db.close()


@app.command()
def remove_proxy_ip(
    server_name: str = typer.Argument(..., help="Server name or IP")
):
    """
    Remove proxy IP allocation from a server.
    
    This deallocates the IP and removes it from the network interface.
    """
    import subprocess
    db = SessionLocal()
    try:
        # Find server
        server = db.query(Server).filter(
            (Server.name == server_name) | (Server.ip_address == server_name)
        ).first()
        
        if not server:
            console.print(f"[red]Error: Server '{server_name}' not found[/red]")
            raise typer.Exit(1)
        
        # Find allocation
        allocation = db.query(IPAllocation).filter(
            IPAllocation.server_id == server.id,
            IPAllocation.is_active == True
        ).first()
        
        if not allocation:
            console.print(f"[yellow]Server has no active proxy IP allocation[/yellow]")
            raise typer.Exit(0)
        
        proxy_ip = allocation.allocated_ip
        
        # Remove IP from interface
        interface = 'ens18'  # Adjust if needed
        try:
            subprocess.run(
                ['ip', 'addr', 'del', f'{proxy_ip}/32', 'dev', interface],
                check=True,
                capture_output=True
            )
            console.print(f"[green]✓ Removed IP {proxy_ip} from interface {interface}[/green]")
        except subprocess.CalledProcessError as e:
            console.print(f"[yellow]Warning: Failed to remove IP: {e.stderr.decode()}[/yellow]")
        
        # Deactivate allocation
        allocation.is_active = False
        db.commit()
        
        console.print(f"[green]✓ Proxy IP {proxy_ip} deallocated from server {server.name}[/green]")
        
    finally:
        db.close()




if __name__ == "__main__":
    app()
