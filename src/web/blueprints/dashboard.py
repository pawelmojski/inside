"""
Dashboard Blueprint - Main overview page
"""
import os
import sys
# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from flask import Blueprint, render_template, g, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func, and_
import psutil
import subprocess

from src.core.database import SessionLocal, User, Server, AccessPolicy, AuditLog, UserSourceIP, ServerGroup, IPAllocation, Session, Stay, AccessGrant

# Import helper function from sessions blueprint
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    """Main dashboard page"""
    db = g.db
    
    # Check permission level for filtering
    is_regular_user = current_user.permission_level >= 900
    user_id_filter = current_user.id if is_regular_user else None
    
    # Service status (admin only)
    services_status = get_services_status() if not is_regular_user else {}
    
    # Statistics
    stats = get_statistics(db, user_id_filter=user_id_filter)
    
    # Active sessions
    active_sessions = get_active_sessions(user_id_filter=user_id_filter)
    
    # Recent closed sessions
    recent_sessions = get_recent_sessions(limit=10, user_id_filter=user_id_filter)
    
    # Servers with IP allocations (admin only - exclude deleted servers)
    server_allocations = []
    if not is_regular_user:
        servers = db.query(Server).filter(Server.deleted == False).order_by(Server.name).all()
        
        # Get IP allocations for each server
        for server in servers:
            allocation = db.query(IPAllocation).filter(
                IPAllocation.server_id == server.id,
                IPAllocation.is_active == True,
                IPAllocation.expires_at == None  # Permanent allocation
            ).first()
            
            server_allocations.append({
                'server': server,
                'allocation': allocation
            })
    
    # Active Stays with timeline data (active + recently ended for timeline)
    from datetime import timedelta
    two_hours_ago = datetime.utcnow() - timedelta(hours=2)
    
    # Build query for stays
    stays_query = db.query(Stay).filter(
        (Stay.is_active == True) | 
        ((Stay.is_active == False) & (Stay.ended_at >= two_hours_ago))
    )
    
    # Filter by user for regular users
    if is_regular_user:
        stays_query = stays_query.filter(Stay.user_id == current_user.id)
    
    active_stays = stays_query.order_by(Stay.started_at.desc()).all()
    
    return render_template('dashboard/index.html',
                         services=services_status,
                         stats=stats,
                         active_sessions=active_sessions,
                         recent_sessions=recent_sessions,
                         server_allocations=server_allocations,
                         active_stays=active_stays,
                         now=datetime.utcnow(),
                         is_regular_user=is_regular_user)

@dashboard_bp.route('/api/stats')
@login_required
def api_stats():
    """API endpoint for dashboard statistics (for AJAX updates)"""
    db = g.db
    # Check permission level for filtering
    is_regular_user = current_user.permission_level >= 900
    user_id_filter = current_user.id if is_regular_user else None
    stats = get_statistics(db, user_id_filter=user_id_filter)
    return jsonify(stats)

@dashboard_bp.route('/api/active-sessions')
@login_required
def api_active_sessions():
    """API endpoint for active sessions list"""
    db = g.db
    active = db.query(Session).filter(
        Session.is_active == True
    ).order_by(Session.started_at.desc()).limit(10).all()
    
    sessions = []
    for sess in active:
        # Build server display
        if sess.protocol == 'ssh' and sess.ssh_username:
            server_display = f"{sess.ssh_username}@{sess.server.name if sess.server else sess.backend_ip}"
            if sess.subsystem_name:
                server_display += f" ({sess.subsystem_name})"
        else:
            server_display = sess.server.name if sess.server else sess.backend_ip
        
        sessions.append({
            'id': sess.id,
            'protocol': sess.protocol.upper(),
            'user': sess.user.username if sess.user else 'Unknown',
            'server': server_display,
            'backend_ip': sess.backend_ip,
            'source_ip': sess.source_ip,
            'ssh_agent': sess.ssh_agent_used if sess.protocol == 'ssh' else None,
            'started': sess.started_at.isoformat() if sess.started_at else None
        })
    
    return jsonify({'sessions': sessions})

@dashboard_bp.route('/api/stays')
@login_required
def api_stays():
    """API endpoint for recent stays (active + recently ended)"""
    db = g.db
    from datetime import datetime, timedelta
    
    # Check permission level for filtering
    is_regular_user = current_user.permission_level >= 900
    
    # Get active stays and recently ended stays (last 2 hours)
    two_hours_ago = datetime.utcnow() - timedelta(hours=2)
    stays_query = db.query(Stay).filter(
        (Stay.is_active == True) | 
        ((Stay.is_active == False) & (Stay.ended_at >= two_hours_ago))
    )
    
    # Filter by user for regular users
    if is_regular_user:
        stays_query = stays_query.filter(Stay.user_id == current_user.id)
    
    stays_query = stays_query.order_by(Stay.started_at.desc()).limit(10).all()
    
    stays_list = []
    now = datetime.utcnow()
    
    for stay in stays_query:
        stay_duration = (now - stay.started_at).total_seconds() if stay.is_active else stay.duration_seconds or 0
        
        sessions_data = []
        for session in stay.sessions:
            session_start_offset = (session.started_at - stay.started_at).total_seconds()
            if session.ended_at:
                session_duration = (session.ended_at - session.started_at).total_seconds()
            else:
                session_duration = (now - session.started_at).total_seconds()
            
            sessions_data.append({
                'id': session.id,
                'session_id': session.session_id,
                'protocol': session.protocol,
                'ssh_username': session.ssh_username,
                'server_id': session.server.id if session.server else None,
                'server_name': session.server.name if session.server else None,
                'backend_ip': session.backend_ip,
                'source_ip': session.source_ip,
                'subsystem_name': session.subsystem_name,
                'port_forwards_count': session.port_forwards_count if hasattr(session, 'port_forwards_count') else 0,
                'started_at': session.started_at.isoformat(),
                'ended_at': session.ended_at.isoformat() if session.ended_at else None,
                'is_active': session.is_active,
                'start_offset': session_start_offset,
                'duration': session_duration
            })
        
        stays_list.append({
            'id': stay.id,
            'user_id': stay.user.id if stay.user else None,
            'user_name': stay.user.full_name or stay.user.username if stay.user else 'Unknown',
            'started_at': stay.started_at.isoformat(),
            'ended_at': stay.ended_at.isoformat() if stay.ended_at else None,
            'is_active': stay.is_active,
            'duration': stay_duration,
            'sessions': sessions_data
        })
    
    return jsonify({'stays': stays_list, 'now': now.isoformat()})

@dashboard_bp.route('/api/stays-chart')
@login_required
def api_stays_chart():
    """API endpoint for stays/sessions chart data"""
    db = g.db
    
    # Check permission level for filtering
    is_regular_user = current_user.permission_level >= 900
    
    # Get only active stays
    stays_query = db.query(Stay).filter(Stay.is_active == True)
    
    # Filter by user for regular users
    if is_regular_user:
        stays_query = stays_query.filter(Stay.user_id == current_user.id)
    
    active_stays = stays_query.all()
    
    chart_data = []
    for stay in active_stays:
        # Count active sessions for this stay
        active_sessions_count = sum(1 for s in stay.sessions if s.is_active)
        
        chart_data.append({
            'stay_id': stay.id,
            'user_name': stay.user.full_name or stay.user.username if stay.user else 'Unknown',
            'sessions_count': active_sessions_count,
            'total_sessions': len(stay.sessions)
        })
    
    return jsonify({'stays': chart_data})

def get_services_status():
    """Get status of SSH and RDP proxy services"""
    services = []
    
    # Check SSH Proxy
    ssh_running = False
    try:
        result = subprocess.run(['pgrep', '-f', 'ssh_proxy.py'], 
                              capture_output=True, text=True, timeout=1)
        ssh_running = result.returncode == 0
    except:
        pass
    
    services.append({
        'name': 'SSH Proxy',
        'port': 22,
        'status': 'running' if ssh_running else 'stopped',
        'uptime': get_process_uptime('ssh_proxy.py') if ssh_running else None
    })
    
    # Check RDP Proxy
    rdp_running = False
    try:
        result = subprocess.run(['pgrep', '-f', 'pyrdp-mitm'], 
                              capture_output=True, text=True, timeout=1)
        rdp_running = result.returncode == 0
    except:
        pass
    
    services.append({
        'name': 'RDP Proxy',
        'port': 3389,
        'status': 'running' if rdp_running else 'stopped',
        'uptime': get_process_uptime('pyrdp-mitm') if rdp_running else None
    })
    
    # Check PostgreSQL
    pg_running = False
    try:
        result = subprocess.run(['systemctl', 'is-active', 'postgresql'], 
                              capture_output=True, text=True, timeout=1)
        pg_running = result.stdout.strip() == 'active'
    except:
        pass
    
    services.append({
        'name': 'PostgreSQL',
        'port': 5432,
        'status': 'running' if pg_running else 'stopped',
        'uptime': None
    })
    
    return services

def get_process_uptime(process_name):
    """Get uptime of a process"""
    try:
        result = subprocess.run(['pgrep', '-f', process_name], 
                              capture_output=True, text=True, timeout=1)
        if result.returncode == 0:
            pid = int(result.stdout.strip().split('\n')[0])
            process = psutil.Process(pid)
            create_time = datetime.fromtimestamp(process.create_time())
            uptime = datetime.now() - create_time
            
            hours = int(uptime.total_seconds() // 3600)
            minutes = int((uptime.total_seconds() % 3600) // 60)
            return f"{hours}h {minutes}m"
    except:
        pass
    return None

def get_statistics(db, user_id_filter=None):
    """Get dashboard statistics (filtered for regular users)"""
    now = datetime.now()
    today_start = datetime(now.year, now.month, now.day)
    today_end = datetime(now.year, now.month, now.day, 23, 59, 59)
    
    if user_id_filter:
        # For regular users - show only their own stats
        # Total counts (their own)
        total_users = 1  # Just themselves
        total_servers = db.query(func.count(func.distinct(Stay.server_id))).filter(
            Stay.user_id == user_id_filter
        ).scalar() or 0
        total_groups = 0  # Don't show groups
        active_grants = 0  # Shown separately in grants page
        people_inside = 0  # Not relevant for regular users (only see themselves)
        
        # Today's connections: sessions started today OR ended today OR still active
        today_connections = db.query(func.count(Session.id)).filter(
            Session.user_id == user_id_filter,
            (
                (Session.started_at >= today_start) |  # Started today
                (and_(Session.ended_at != None, Session.ended_at >= today_start, Session.ended_at <= today_end)) |  # Ended today
                (Session.is_active == True)  # Still active
            )
        ).scalar() or 0
        
        today_denied = db.query(func.count(AuditLog.id)).filter(
            AuditLog.timestamp >= today_start,
            AuditLog.action.in_(['ssh_access_denied', 'rdp_access_denied']),
            AuditLog.user_id == user_id_filter
        ).scalar()
        
        # Recent trends (last 7 days - their own)
        week_ago = now - timedelta(days=7)
        week_connections = db.query(func.count(AuditLog.id)).filter(
            AuditLog.timestamp >= week_ago,
            AuditLog.action.in_(['ssh_access_granted', 'rdp_access_granted']),
            AuditLog.user_id == user_id_filter
        ).scalar()
    else:
        # For admins - show all stats
        # Total counts (only active users and non-deleted servers)
        total_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
        total_servers = db.query(func.count(Server.id)).filter(Server.deleted == False).scalar()
        total_groups = db.query(func.count(ServerGroup.id)).scalar()
        
        # Active Grants - count active policies with valid end_time
        active_grants = db.query(func.count(AccessPolicy.id)).filter(
            AccessPolicy.is_active == True,
            (AccessPolicy.end_time == None) | (AccessPolicy.end_time > now)
        ).scalar()
        
        # People Inside - count unique users from active stays
        people_inside = db.query(func.count(func.distinct(Stay.user_id))).filter(
            Stay.is_active == True
        ).scalar() or 0
        
        # Today's connections: sessions started today OR ended today OR still active
        today_connections = db.query(func.count(Session.id)).filter(
            (
                (Session.started_at >= today_start) |  # Started today
                (and_(Session.ended_at != None, Session.ended_at >= today_start, Session.ended_at <= today_end)) |  # Ended today
                (Session.is_active == True)  # Still active
            )
        ).scalar() or 0
        
        today_denied = db.query(func.count(AuditLog.id)).filter(
            AuditLog.timestamp >= today_start,
            AuditLog.action.in_(['ssh_access_denied', 'rdp_access_denied'])
        ).scalar()
        
        # Recent trends (last 7 days)
        week_ago = now - timedelta(days=7)
        week_connections = db.query(func.count(AuditLog.id)).filter(
            AuditLog.timestamp >= week_ago,
            AuditLog.action.in_(['ssh_access_granted', 'rdp_access_granted'])
        ).scalar()
    
    return {
        'total_users': total_users,
        'total_servers': total_servers,
        'total_groups': total_groups,
        'active_grants': active_grants,
        'people_inside': people_inside,
        'today_connections': today_connections,
        'today_denied': today_denied,
        'week_connections': week_connections,
        'success_rate': round((today_connections / (today_connections + today_denied) * 100) 
                             if (today_connections + today_denied) > 0 else 100, 1)
    }

def get_active_sessions(user_id_filter=None):
    """Get currently active sessions from database (filtered for regular users)"""
    db = g.db
    
    # Build query
    query = db.query(Session).filter(Session.is_active == True)
    
    # Filter by user for regular users
    if user_id_filter:
        query = query.join(Stay).filter(Stay.user_id == user_id_filter)
    
    active = query.order_by(Session.started_at.desc()).limit(10).all()
    
    sessions = []
    for sess in active:
        # Build server display: ssh_username@servername for SSH, just servername for RDP
        if sess.protocol == 'ssh' and sess.ssh_username:
            server_display = f"{sess.ssh_username}@{sess.server.name if sess.server else sess.backend_ip}"
            if sess.subsystem_name:
                server_display += f" ({sess.subsystem_name})"
        else:
            server_display = sess.server.name if sess.server else sess.backend_ip
        
        sessions.append({
            'protocol': sess.protocol.upper(),
            'user': sess.user.username if sess.user else 'Unknown',
            'source_ip': sess.source_ip,
            'server': server_display,
            'backend_ip': sess.backend_ip,
            'ssh_agent': sess.ssh_agent_used if sess.protocol == 'ssh' else None,
            'started': sess.started_at
        })
    
    return sessions


def get_recent_sessions(limit=10, user_id_filter=None):
    """Get recently closed sessions from database (filtered for regular users)"""
    # Import here to avoid circular dependency
    from blueprints.sessions import recording_exists
    
    db = g.db
    
    # Build query
    query = db.query(Session).filter(Session.is_active == False)
    
    # Filter by user for regular users
    if user_id_filter:
        query = query.join(Stay).filter(Stay.user_id == user_id_filter)
    
    recent = query.order_by(Session.ended_at.desc()).limit(limit).all()
    
    sessions = []
    for sess in recent:
        # Build server display
        if sess.protocol == 'ssh' and sess.ssh_username:
            server_display = f"{sess.ssh_username}@{sess.server.name if sess.server else sess.backend_ip}"
            if sess.subsystem_name:
                server_display += f" ({sess.subsystem_name})"
        else:
            server_display = sess.server.name if sess.server else sess.backend_ip
        
        # Format duration
        if sess.duration_seconds:
            hours = int(sess.duration_seconds // 3600)
            minutes = int((sess.duration_seconds % 3600) // 60)
            seconds = int(sess.duration_seconds % 60)
            if hours > 0:
                duration = f"{hours}h {minutes}m"
            elif minutes > 0:
                duration = f"{minutes}m {seconds}s"
            else:
                duration = f"{seconds}s"
        else:
            duration = "N/A"
        
        sessions.append({
            'session_id': sess.session_id,
            'protocol': sess.protocol.upper(),
            'user': sess.user.username if sess.user else 'Unknown',
            'server': server_display,
            'started': sess.started_at,
            'duration': duration,
            'ended': sess.ended_at,
            'has_recording': recording_exists(sess)
        })
    
    return sessions
