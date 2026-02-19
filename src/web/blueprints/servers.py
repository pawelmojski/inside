"""
Servers Blueprint - Server management
"""
from flask import Blueprint, render_template, g, request, redirect, url_for, flash, abort, jsonify
from flask_login import login_required
import requests
from datetime import datetime

from src.core.database import Server, IPAllocation, ServerGroupMember, User, AccessPolicy, AccessGrant, SessionRecording, Stay, Session
from sqlalchemy import text
from src.core.ip_pool import IPPoolManager
from src.web.permissions import admin_required

servers_bp = Blueprint('servers', __name__)

@servers_bp.route('/')
@login_required
@admin_required
def index():
    """List all servers (active + deleted)"""
    db = g.db
    
    # Separate active and deleted servers
    active_servers = db.query(Server).filter(
        Server.deleted == False
    ).order_by(Server.name).all()
    
    deleted_servers = db.query(Server).filter(
        Server.deleted == True
    ).order_by(Server.deleted_at.desc()).all()
    
    users = db.query(User).filter(User.is_active == True).order_by(User.full_name).all()
    
    return render_template(
        'servers/index.html', 
        active_servers=active_servers, 
        deleted_servers=deleted_servers,
        users=users
    )

@servers_bp.route('/view/<int:server_id>')
@login_required
@admin_required
def view(server_id):
    """View server details"""
    db = g.db
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        abort(404)
    
    # Get permanent IP allocation for this server
    allocation = db.query(IPAllocation).filter(
        IPAllocation.server_id == server.id,
        IPAllocation.is_active == True,
        IPAllocation.expires_at == None  # Permanent allocation
    ).first()
    
    return render_template('servers/view.html', server=server, allocation=allocation)

@servers_bp.route('/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add():
    """Add new server (Admin only)"""
    if request.method == 'POST':
        db = g.db
        try:
            # Get port and determine protocol defaults
            port = int(request.form.get('port', 22))
            ssh_enabled = request.form.get('ssh_enabled') == 'on'
            rdp_enabled = request.form.get('rdp_enabled') == 'on'
            is_active = request.form.get('is_active', 'on') == 'on'
            
            # Set default ports based on enabled protocols
            ssh_port = port if ssh_enabled else 22
            rdp_port = port if rdp_enabled else 3389
            
            server = Server(
                name=request.form['name'],
                ip_address=request.form['address'],  # Template uses 'address', not 'ip_address'
                description=request.form.get('description'),
                os_type=None,  # Can be added to form later
                ssh_port=ssh_port,
                rdp_port=rdp_port,
                is_active=is_active
            )
            db.add(server)
            db.commit()
            db.refresh(server)
            
            # Optionally allocate proxy IP
            if request.form.get('allocate_ip') == 'on':
                pool_manager = IPPoolManager()
                proxy_ip = pool_manager.allocate_permanent_ip(db, server.id)
                if proxy_ip:
                    flash(f'Server {server.name} added with proxy IP {proxy_ip}!', 'success')
                else:
                    flash(f'Server {server.name} added but IP pool exhausted!', 'warning')
            else:
                flash(f'Server {server.name} added successfully!', 'success')
            
            return redirect(url_for('servers.view', server_id=server.id))
        except Exception as e:
            db.rollback()
            flash(f'Error adding server: {str(e)}', 'danger')
    
    return render_template('servers/add.html')

@servers_bp.route('/edit/<int:server_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit(server_id):
    """Edit server (Admin only)"""
    db = g.db
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        abort(404)
    
    if request.method == 'POST':
        try:
            # Get port and determine protocol defaults
            port = int(request.form.get('port', 22))
            ssh_enabled = request.form.get('ssh_enabled') == 'on'
            rdp_enabled = request.form.get('rdp_enabled') == 'on'
            is_active = request.form.get('is_active', 'on') == 'on'
            
            # Set default ports based on enabled protocols
            ssh_port = port if ssh_enabled else 22
            rdp_port = port if rdp_enabled else 3389
            
            server.name = request.form['name']
            server.ip_address = request.form['address']  # Template uses 'address'
            server.description = request.form.get('description')
            server.ssh_port = ssh_port
            server.rdp_port = rdp_port
            server.is_active = is_active
            
            db.commit()
            flash(f'Server {server.name} updated successfully!', 'success')
            return redirect(url_for('servers.view', server_id=server.id))
        except Exception as e:
            db.rollback()
            flash(f'Error updating server: {str(e)}', 'danger')
    
    return render_template('servers/edit.html', server=server)

@servers_bp.route('/delete/<int:server_id>', methods=['POST'])
@login_required
@admin_required
def delete(server_id):
    """Delete server - Hybrid: soft-delete if has history, hard-delete if clean (Admin only)"""
    from flask_login import current_user
    db = g.db
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        abort(404)
    
    try:
        name = server.name
        
        # Check if server has history (stays, sessions, recordings)
        has_stays = db.query(Stay).filter(Stay.server_id == server_id).count() > 0
        has_sessions = db.query(Session).filter(Session.server_id == server_id).count() > 0
        has_recordings = db.query(SessionRecording).filter(
            SessionRecording.server_id == server_id
        ).count() > 0
        
        if has_stays or has_sessions or has_recordings:
            # SOFT DELETE - server has history, preserve it
            server.deleted = True
            server.deleted_at = datetime.utcnow()
            server.deleted_by_user_id = current_user.id
            server.is_active = False
            
            # Release IP allocations (allow reuse)
            ips_released = db.query(IPAllocation).filter(
                IPAllocation.server_id == server_id
            ).delete(synchronize_session=False)
            
            # Deactivate policies (don't delete - preserve history)
            policies_deactivated = db.query(AccessPolicy).filter(
                AccessPolicy.target_server_id == server_id,
                AccessPolicy.is_active == True
            ).update({'is_active': False}, synchronize_session=False)
            
            # Deactivate grants (don't delete - preserve history)
            grants_deactivated = db.query(AccessGrant).filter(
                AccessGrant.server_id == server_id,
                AccessGrant.is_active == True
            ).update({'is_active': False}, synchronize_session=False)
            
            db.commit()
            
            flash(
                f'Server "{name}" archived (soft-deleted). '
                f'History preserved: {has_stays} stays, {has_sessions} sessions, {has_recordings} recordings. '
                f'Released {ips_released} IPs, deactivated {policies_deactivated} policies, {grants_deactivated} grants.',
                'warning'
            )
        else:
            # HARD DELETE - clean server without history
            # Delete dependencies that block deletion
            
            # 1. Delete access policies
            policies_deleted = db.query(AccessPolicy).filter(
                AccessPolicy.target_server_id == server_id
            ).delete(synchronize_session=False)
            
            # 2. Delete access grants
            grants_deleted = db.query(AccessGrant).filter(
                AccessGrant.server_id == server_id
            ).delete(synchronize_session=False)
            
            # 3. Delete IP allocations
            ips_deleted = db.query(IPAllocation).filter(
                IPAllocation.server_id == server_id
            ).delete(synchronize_session=False)
            
            # 4. server_group_members cascade automatically
            
            # 5. Delete the server
            db.delete(server)
            db.commit()
            
            flash(
                f'Server "{name}" deleted completely (no history). '
                f'Cleaned up: {policies_deleted} policies, {grants_deleted} grants, {ips_deleted} IPs.',
                'success'
            )
    except Exception as e:
        db.rollback()
        flash(f'Error deleting server: {str(e)}', 'danger')
    
    return redirect(url_for('servers.index'))

@servers_bp.route('/<int:server_id>/maintenance', methods=['POST'])
@login_required
@admin_required
def enter_maintenance(server_id):
    """Schedule server maintenance via Tower API (Admin only)"""
    db = g.db
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        return jsonify({'success': False, 'error': 'Server not found'}), 404
    
    try:
        data = request.json
        scheduled_at = data.get('scheduled_at')
        grace_minutes = data.get('grace_minutes', 15)
        reason = data.get('reason', 'Scheduled maintenance')
        personnel_ids = data.get('personnel_ids', [])
        
        if not scheduled_at:
            return jsonify({'success': False, 'error': 'scheduled_at is required'}), 400
        
        # Find the gate this server belongs to (Tower API uses gate token)
        from src.core.database import Gate
        gate = db.query(Gate).filter(Gate.is_active == True).first()
        if not gate or not gate.api_token:
            return jsonify({'success': False, 'error': 'No active gate with API token found'}), 500
        
        # Proxy to Tower API
        response = requests.post(
            f'http://localhost:5000/api/v1/backends/{server_id}/maintenance',
            headers={'Authorization': f'Bearer {gate.api_token}'},
            json={
                'scheduled_at': scheduled_at,
                'grace_minutes': grace_minutes,
                'reason': reason,
                'personnel_ids': personnel_ids
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            return jsonify({
                'success': True,
                'message': 'Maintenance scheduled successfully',
                'scheduled_at': result.get('scheduled_at'),
                'grace_starts_at': result.get('grace_starts_at'),
                'affected_sessions': result.get('affected_sessions', 0),
                'maintenance_personnel': result.get('maintenance_personnel', [])
            })
        else:
            error = response.json().get('error', 'Unknown error')
            return jsonify({'success': False, 'error': error}), response.status_code
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@servers_bp.route('/<int:server_id>/maintenance', methods=['DELETE'])
@login_required
@admin_required
def exit_maintenance(server_id):
    """Exit server maintenance via Tower API (Admin only)"""
    db = g.db
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        return jsonify({'success': False, 'error': 'Server not found'}), 404
    
    try:
        # Find the gate for API token
        from src.core.database import Gate
        gate = db.query(Gate).filter(Gate.is_active == True).first()
        if not gate or not gate.api_token:
            return jsonify({'success': False, 'error': 'No active gate with API token found'}), 500
        
        # Proxy to Tower API
        response = requests.delete(
            f'http://localhost:5000/api/v1/backends/{server_id}/maintenance',
            headers={'Authorization': f'Bearer {gate.api_token}'}
        )
        
        if response.status_code == 200:
            result = response.json()
            return jsonify({
                'success': True,
                'message': 'Maintenance mode ended',
                'affected_sessions': result.get('affected_sessions', 0)
            })
        else:
            error = response.json().get('error', 'Unknown error')
            return jsonify({'success': False, 'error': error}), response.status_code
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
