"""Gates management blueprint."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, g
from flask_login import login_required
from src.core.database import Gate
from datetime import datetime, timedelta
import ipaddress

gates_bp = Blueprint('gates', __name__, url_prefix='/gates')


@gates_bp.route('/')
@login_required
def list():
    """List all gates with their IP pool configurations."""
    db = g.db
    gates = db.query(Gate).order_by(Gate.name).all()
    
    # Get all active users for maintenance personnel selection
    from src.core.database import User
    users = db.query(User).filter(User.is_active == True).order_by(User.username).all()
    
    # Calculate IP pool stats and heartbeat status for each gate
    now = datetime.utcnow()
    heartbeat_warning_threshold = timedelta(minutes=2)  # 4 heartbeats at 30s interval
    
    for gate in gates:
        from src.core.ip_pool import IPPoolManager
        pool_mgr = IPPoolManager(gate=gate)
        available_ips = pool_mgr.get_available_ips(db, gate_id=gate.id)
        
        # Calculate total IPs in range
        try:
            start_ip = ipaddress.IPv4Address(gate.ip_pool_start)
            end_ip = ipaddress.IPv4Address(gate.ip_pool_end)
            total_ips = int(end_ip) - int(start_ip) + 1
        except:
            total_ips = 0
        
        gate.pool_total = total_ips
        gate.pool_available = len(available_ips)
        gate.pool_allocated = total_ips - len(available_ips)
        
        # Check heartbeat freshness
        if gate.is_active and gate.last_heartbeat:
            time_since_heartbeat = now - gate.last_heartbeat
            gate.heartbeat_warning = time_since_heartbeat > heartbeat_warning_threshold
        else:
            gate.heartbeat_warning = gate.is_active  # Warn if active but no heartbeat
    
    return render_template('gates/list.html', gates=gates, users=users)


@gates_bp.route('/data')
@login_required
def data():
    """Return gates data as JSON for AJAX refresh."""
    from flask import jsonify
    db = g.db
    gates = db.query(Gate).order_by(Gate.name).all()
    
    # Calculate IP pool stats and heartbeat status for each gate
    now = datetime.utcnow()
    heartbeat_warning_threshold = timedelta(minutes=2)
    
    gates_data = []
    for gate in gates:
        from src.core.ip_pool import IPPoolManager
        pool_mgr = IPPoolManager(gate=gate)
        available_ips = pool_mgr.get_available_ips(db, gate_id=gate.id)
        
        # Calculate total IPs in range
        try:
            start_ip = ipaddress.IPv4Address(gate.ip_pool_start)
            end_ip = ipaddress.IPv4Address(gate.ip_pool_end)
            total_ips = int(end_ip) - int(start_ip) + 1
        except:
            total_ips = 0
        
        pool_allocated = total_ips - len(available_ips)
        
        # Check heartbeat freshness
        heartbeat_warning = False
        if gate.is_active and gate.last_heartbeat:
            time_since_heartbeat = now - gate.last_heartbeat
            heartbeat_warning = time_since_heartbeat > heartbeat_warning_threshold
        elif gate.is_active:
            heartbeat_warning = True
        
        gates_data.append({
            'id': gate.id,
            'name': gate.name,
            'hostname': gate.hostname,
            'location': gate.location,
            'status': gate.status,
            'ip_pool_start': gate.ip_pool_start,
            'ip_pool_end': gate.ip_pool_end,
            'ip_pool_network': gate.ip_pool_network,
            'pool_total': total_ips,
            'pool_allocated': pool_allocated,
            'pool_available': len(available_ips),
            'last_heartbeat': gate.last_heartbeat.strftime('%Y-%m-%d %H:%M:%S') if gate.last_heartbeat else None,
            'heartbeat_warning': heartbeat_warning,
            'is_active': gate.is_active,
            'in_maintenance': gate.in_maintenance,
            'maintenance_scheduled_at': gate.maintenance_scheduled_at.strftime('%Y-%m-%d %H:%M') if gate.maintenance_scheduled_at else None,
            'maintenance_reason': gate.maintenance_reason
        })
    
    return jsonify(gates_data)


@gates_bp.route('/view/<int:gate_id>')
@login_required
def view(gate_id):
    """View gate details with IP allocations."""
    db = g.db
    gate = db.query(Gate).filter(Gate.id == gate_id).first()
    if not gate:
        abort(404)
    
    # Get IP allocations for this gate
    from src.core.database import IPAllocation, Server
    allocations = db.query(IPAllocation, Server).join(
        Server, IPAllocation.server_id == Server.id
    ).filter(
        IPAllocation.gate_id == gate_id,
        IPAllocation.is_active == True
    ).order_by(IPAllocation.allocated_ip).all()
    
    # Get available IPs
    from src.core.ip_pool import IPPoolManager
    pool_mgr = IPPoolManager(gate=gate)
    available_ips = pool_mgr.get_available_ips(db, gate_id=gate.id)
    
    return render_template('gates/view.html', 
                         gate=gate, 
                         allocations=allocations,
                         available_ips=available_ips[:20])  # Show first 20


@gates_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """Add new gate."""
    if request.method == 'POST':
        db = g.db
        try:
            # Validate IP pool configuration
            ip_pool_start = request.form['ip_pool_start']
            ip_pool_end = request.form['ip_pool_end']
            ip_pool_network = request.form['ip_pool_network']
            
            # Validate IP addresses
            try:
                start_ip = ipaddress.IPv4Address(ip_pool_start)
                end_ip = ipaddress.IPv4Address(ip_pool_end)
                network = ipaddress.IPv4Network(ip_pool_network)
                
                if start_ip >= end_ip:
                    flash('Start IP must be less than End IP!', 'danger')
                    return render_template('gates/add.html')
                    
            except ValueError as e:
                flash(f'Invalid IP configuration: {e}', 'danger')
                return render_template('gates/add.html')
            
            # Generate API token
            import secrets
            api_token = secrets.token_urlsafe(32)
            
            gate = Gate(
                name=request.form['name'],
                hostname=request.form['hostname'],
                api_token=api_token,
                location=request.form.get('location'),
                description=request.form.get('description'),
                ip_pool_network=ip_pool_network,
                ip_pool_start=ip_pool_start,
                ip_pool_end=ip_pool_end,
                is_active=request.form.get('is_active') == 'on'
            )
            db.add(gate)
            db.commit()
            
            flash(f'Gate {gate.name} added successfully! API Token: {api_token}', 'success')
            flash('IMPORTANT: Save the API token - it won\'t be shown again!', 'warning')
            return redirect(url_for('gates.view', gate_id=gate.id))
        except Exception as e:
            db.rollback()
            flash(f'Error adding gate: {str(e)}', 'danger')
    
    # Default values for new gate
    defaults = {
        'ip_pool_network': '10.0.160.128/25',
        'ip_pool_start': '10.0.160.129',
        'ip_pool_end': '10.0.160.254'
    }
    return render_template('gates/add.html', defaults=defaults)


@gates_bp.route('/edit/<int:gate_id>', methods=['GET', 'POST'])
@login_required
def edit(gate_id):
    """Edit gate configuration including IP pool."""
    db = g.db
    gate = db.query(Gate).filter(Gate.id == gate_id).first()
    if not gate:
        abort(404)
    
    if request.method == 'POST':
        try:
            # Validate IP pool configuration
            ip_pool_start = request.form['ip_pool_start']
            ip_pool_end = request.form['ip_pool_end']
            ip_pool_network = request.form['ip_pool_network']
            
            try:
                start_ip = ipaddress.IPv4Address(ip_pool_start)
                end_ip = ipaddress.IPv4Address(ip_pool_end)
                network = ipaddress.IPv4Network(ip_pool_network)
                
                if start_ip >= end_ip:
                    flash('Start IP must be less than End IP!', 'danger')
                    return render_template('gates/edit.html', gate=gate)
                    
            except ValueError as e:
                flash(f'Invalid IP configuration: {e}', 'danger')
                return render_template('gates/edit.html', gate=gate)
            
            # Update gate
            gate.name = request.form['name']
            gate.hostname = request.form['hostname']
            gate.location = request.form.get('location')
            gate.description = request.form.get('description')
            gate.ip_pool_network = ip_pool_network
            gate.ip_pool_start = ip_pool_start
            gate.ip_pool_end = ip_pool_end
            gate.is_active = request.form.get('is_active') == 'on'
            
            # Update custom messages (optional fields)
            gate.msg_no_person = request.form.get('msg_no_person') or None
            gate.msg_no_backend = request.form.get('msg_no_backend') or None
            gate.msg_no_grant = request.form.get('msg_no_grant') or None
            gate.msg_maintenance = request.form.get('msg_maintenance') or None
            gate.msg_time_window = request.form.get('msg_time_window') or None
            gate.msg_welcome_banner = request.form.get('msg_welcome_banner') or None
            
            gate.updated_at = datetime.utcnow()
            
            db.commit()
            flash(f'Gate {gate.name} updated successfully!', 'success')
            return redirect(url_for('gates.view', gate_id=gate.id))
        except Exception as e:
            db.rollback()
            flash(f'Error updating gate: {str(e)}', 'danger')
    
    return render_template('gates/edit.html', gate=gate)


@gates_bp.route('/delete/<int:gate_id>', methods=['POST'])
@login_required
def delete(gate_id):
    """Delete gate (only if no active allocations)."""
    db = g.db
    gate = db.query(Gate).filter(Gate.id == gate_id).first()
    if not gate:
        abort(404)
    
    # Check for active IP allocations
    from src.core.database import IPAllocation
    active_allocations = db.query(IPAllocation).filter(
        IPAllocation.gate_id == gate_id,
        IPAllocation.is_active == True
    ).count()
    
    if active_allocations > 0:
        flash(f'Cannot delete gate with {active_allocations} active IP allocations!', 'danger')
        return redirect(url_for('gates.view', gate_id=gate_id))
    
    try:
        gate_name = gate.name
        db.delete(gate)
        db.commit()
        flash(f'Gate {gate_name} deleted successfully!', 'success')
        return redirect(url_for('gates.list'))
    except Exception as e:
        db.rollback()
        flash(f'Error deleting gate: {str(e)}', 'danger')
        return redirect(url_for('gates.view', gate_id=gate_id))


@gates_bp.route('/<int:gate_id>/maintenance', methods=['POST'])
@login_required
def enter_maintenance(gate_id):
    """Proxy endpoint to call Tower API maintenance mode.
    
    Used by gates/list.html maintenance button.
    """
    from flask import jsonify
    db = g.db
    
    gate = db.query(Gate).filter(Gate.id == gate_id).first()
    if not gate:
        return jsonify({'error': 'gate_not_found', 'message': 'Gate not found'}), 404
    
    data = request.get_json()
    scheduled_at = data.get('scheduled_at')  # ISO timestamp
    grace_minutes = data.get('grace_minutes', 15)
    reason = data.get('reason', 'Scheduled gate maintenance')
    personnel_ids = data.get('personnel_ids', [])
    
    if not scheduled_at:
        return jsonify({'error': 'missing_scheduled_at', 'message': 'scheduled_at is required'}), 400
    
    # Call Tower API maintenance endpoint
    import requests
    try:
        response = requests.post(
            f'http://localhost:5000/api/v1/gates/{gate_id}/maintenance',
            headers={'Authorization': f'Bearer {gate.api_token}'},
            json={
                'scheduled_at': scheduled_at,
                'grace_minutes': grace_minutes,
                'reason': reason,
                'personnel_ids': personnel_ids
            },
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            personnel_str = ', '.join(result.get('maintenance_personnel', []))
            personnel_info = f" Maintenance personnel: {personnel_str}" if personnel_str else ""
            flash(f"Maintenance scheduled for {gate.name}. "
                  f"Grace period starts at {result['grace_starts_at']}, "
                  f"maintenance at {result['scheduled_at']}. "
                  f"{result['affected_sessions']} sessions will be disconnected.{personnel_info}", 
                  'success')
            return jsonify(result), 200
        else:
            error_data = response.json() if response.content else {}
            return jsonify(error_data), response.status_code
            
    except Exception as e:
        return jsonify({'error': 'api_error', 'message': str(e)}), 500


@gates_bp.route('/<int:gate_id>/maintenance', methods=['DELETE'])
@login_required
def exit_maintenance(gate_id):
    """Proxy endpoint to exit maintenance mode.
    
    Used by gates/list.html Exit Maintenance button.
    """
    from flask import jsonify
    db = g.db
    
    gate = db.query(Gate).filter(Gate.id == gate_id).first()
    if not gate:
        return jsonify({'error': 'gate_not_found', 'message': 'Gate not found'}), 404
    
    # Call Tower API exit maintenance endpoint
    import requests
    try:
        response = requests.delete(
            f'http://localhost:5000/api/v1/gates/{gate_id}/maintenance',
            headers={'Authorization': f'Bearer {gate.api_token}'},
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            flash(f"Maintenance mode ended for {gate.name}.", 'success')
            return jsonify(result), 200
        else:
            error_data = response.json() if response.content else {}
            return jsonify(error_data), response.status_code
            
    except Exception as e:
        return jsonify({'error': 'api_error', 'message': str(e)}), 500
