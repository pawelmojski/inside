"""
Access Policies Blueprint - Policy management
"""
from flask import Blueprint, render_template, g, request, redirect, url_for, flash, abort
from flask_login import login_required
from datetime import datetime, timedelta, time
import json

from src.core.database import AccessPolicy, User, UserSourceIP, Server, ServerGroup, PolicySSHLogin, UserGroup, PolicySchedule
from src.core.duration_parser import parse_duration, format_duration
from src.core.schedule_checker import format_schedule_description

policies_bp = Blueprint('policies', __name__)

def format_policy_schedules_summary(policy):
    """Format policy schedules as summary + tooltip.
    
    Returns:
        tuple: (summary_text, tooltip_text)
        - summary_text: Short display (e.g. "Mon-Fri 8-16" or "3 rules")
        - tooltip_text: Full description of all schedules
    """
    if not policy.use_schedules or not policy.schedules:
        return ("-", "No schedule restrictions")
    
    active_schedules = [s for s in policy.schedules if s.is_active]
    
    if not active_schedules:
        return ("(disabled)", "Schedule checking enabled but no active rules")
    
    # Format all schedules for tooltip
    tooltip_lines = []
    for i, schedule in enumerate(active_schedules, 1):
        schedule_dict = {
            'weekdays': schedule.weekdays,
            'time_start': schedule.time_start,
            'time_end': schedule.time_end,
            'months': schedule.months,
            'days_of_month': schedule.days_of_month,
            'timezone': schedule.timezone
        }
        desc = format_schedule_description(schedule_dict)
        name = schedule.name or f"Rule {i}"
        tooltip_lines.append(f"{name}: {desc}")
    
    tooltip_text = "\n".join(tooltip_lines)
    
    # Summary text
    if len(active_schedules) == 1:
        # Single schedule - show full description
        schedule_dict = {
            'weekdays': active_schedules[0].weekdays,
            'time_start': active_schedules[0].time_start,
            'time_end': active_schedules[0].time_end,
            'months': active_schedules[0].months,
            'days_of_month': active_schedules[0].days_of_month,
            'timezone': active_schedules[0].timezone
        }
        summary = format_schedule_description(schedule_dict)
    else:
        # Multiple schedules - show count
        first_schedule_dict = {
            'weekdays': active_schedules[0].weekdays,
            'time_start': active_schedules[0].time_start,
            'time_end': active_schedules[0].time_end,
            'months': active_schedules[0].months,
            'days_of_month': active_schedules[0].days_of_month,
            'timezone': active_schedules[0].timezone
        }
        first_desc = format_schedule_description(first_schedule_dict)
        summary = f"{first_desc} (+{len(active_schedules)-1} more)"
    
    return (summary, tooltip_text)

@policies_bp.route('/')
@login_required
def index():
    """List all policies"""
    db = g.db
    
    # Filter parameters
    show_expired = request.args.get('show_expired', 'false') == 'true'
    user_filter = request.args.get('user')
    group_filter = request.args.get('group')
    
    query = db.query(AccessPolicy).filter(AccessPolicy.is_active == True)
    
    if not show_expired:
        now = datetime.utcnow()
        # Show policies that haven't expired yet (end_time > now OR end_time IS NULL)
        # This includes future grants (start_time > now) - they will be shown as "scheduled"
        query = query.filter(
            (AccessPolicy.end_time == None) | (AccessPolicy.end_time > now)
        )
    
    if user_filter:
        query = query.filter(AccessPolicy.user_id == int(user_filter))
    
    if group_filter:
        query = query.filter(AccessPolicy.user_group_id == int(group_filter))
    
    policies = query.order_by(AccessPolicy.created_at.desc()).all()
    users = db.query(User).order_by(User.username).all()
    user_groups = db.query(UserGroup).order_by(UserGroup.name).all()
    
    return render_template('policies/index.html', policies=policies, users=users,
                         user_groups=user_groups, show_expired=show_expired, 
                         user_filter=user_filter, group_filter=group_filter,
                         now=datetime.utcnow(), 
                         format_schedules=format_policy_schedules_summary)

@policies_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """Add new policy (grant wizard)"""
    db = g.db
    
    if request.method == 'POST':
        try:
            # Parse form data
            grant_type = request.form.get('grant_type', 'user')
            user_id = request.form.get('user_id')
            user_group_id = request.form.get('user_group_id')
            scope_type = request.form['scope_type']
            protocol = request.form.get('protocol') or None
            source_ip_id = request.form.get('source_ip_id')
            port_forwarding_allowed = request.form.get('port_forwarding_allowed') == 'on'
            
            # Validate: either user_id or user_group_id must be provided
            if grant_type == 'user' and not user_id:
                flash('User is required', 'danger')
                return redirect(url_for('policies.add'))
            if grant_type == 'group' and not user_group_id:
                flash('User group is required', 'danger')
                return redirect(url_for('policies.add'))
            
            # Parse start_time (optional, default to now)
            start_time_str = request.form.get('start_time')
            if start_time_str:
                # Parse HTML5 datetime-local format (YYYY-MM-DDTHH:MM)
                start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            else:
                start_time = datetime.utcnow()
            
            # Calculate end_time based on duration_type
            duration_type = request.form.get('duration_type', 'duration')
            end_time = None
            
            if duration_type == 'duration':
                # Parse human-readable duration
                duration_text = request.form.get('duration_text', '').strip()
                
                if not duration_text:
                    flash('Duration is required. Use "1h" for 1 hour, or "permanent" for no expiration.', 'danger')
                    return redirect(url_for('policies.add'))
                
                total_minutes = parse_duration(duration_text)
                
                if total_minutes is None:
                    flash(f'Invalid duration format: "{duration_text}". Examples: 30m, 2h, 1d, 1.5h, 2d12h, permanent', 'danger')
                    return redirect(url_for('policies.add'))
                
                if total_minutes > 0:
                    end_time = start_time + timedelta(minutes=total_minutes)
                # else: total_minutes == 0 means permanent (end_time = None)
                
            elif duration_type == 'absolute':
                # Specific start and end date/time
                absolute_start_time_str = request.form.get('absolute_start_time')
                if absolute_start_time_str:
                    start_time = datetime.strptime(absolute_start_time_str, '%Y-%m-%dT%H:%M')
                # else: start_time already set to utcnow() or from form
                
                end_time_str = request.form.get('end_time')
                if end_time_str:
                    end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')
                else:
                    flash('End time is required when using absolute date/time', 'danger')
                    return redirect(url_for('policies.add'))
            
            # duration_type == 'permanent': end_time remains None
            
            # Get inactivity timeout (default 60 minutes)
            inactivity_timeout = request.form.get('inactivity_timeout_minutes', '60').strip()
            try:
                inactivity_timeout_minutes = int(inactivity_timeout) if inactivity_timeout else 60
                if inactivity_timeout_minutes < 0:
                    inactivity_timeout_minutes = 0  # Treat negative as disabled
            except ValueError:
                flash('Invalid inactivity timeout. Using default: 60 minutes', 'warning')
                inactivity_timeout_minutes = 60
            
            # Create policy
            policy = AccessPolicy(
                user_id=int(user_id) if user_id else None,
                user_group_id=int(user_group_id) if user_group_id else None,
                source_ip_id=int(source_ip_id) if source_ip_id else None,
                scope_type=scope_type,
                protocol=protocol,
                port_forwarding_allowed=port_forwarding_allowed,
                is_active=True,
                start_time=start_time,
                end_time=end_time,
                inactivity_timeout_minutes=inactivity_timeout_minutes
            )
            
            # Set target based on scope
            if scope_type == 'group':
                policy.target_group_id = int(request.form['target_group_id'])
            elif scope_type in ['server', 'service']:
                policy.target_server_id = int(request.form['target_server_id'])
            
            db.add(policy)
            db.flush()  # Get policy ID
            
            # Add SSH logins if specified
            ssh_logins = request.form.get('ssh_logins', '').strip()
            if ssh_logins:
                for login in ssh_logins.split(','):
                    login = login.strip()
                    if login:
                        ssh_login = PolicySSHLogin(
                            policy_id=policy.id,
                            allowed_login=login
                        )
                        db.add(ssh_login)
            
            # Add schedules if enabled
            use_schedules = request.form.get('use_schedules') == 'on'
            if use_schedules:
                policy.use_schedules = True
                schedules_json = request.form.get('schedules_json')
                if schedules_json:
                    try:
                        schedules = json.loads(schedules_json)
                        for schedule_data in schedules:
                            schedule = PolicySchedule(
                                policy_id=policy.id,
                                name=schedule_data['name'],
                                weekdays=schedule_data.get('weekdays'),
                                time_start=datetime.strptime(schedule_data['time_start'], '%H:%M').time() if schedule_data.get('time_start') else None,
                                time_end=datetime.strptime(schedule_data['time_end'], '%H:%M').time() if schedule_data.get('time_end') else None,
                                months=schedule_data.get('months'),
                                days_of_month=schedule_data.get('days_of_month'),
                                timezone=schedule_data.get('timezone', 'Europe/Warsaw'),
                                is_active=True
                            )
                            db.add(schedule)
                    except Exception as e:
                        db.rollback()
                        flash(f'Error parsing schedules: {str(e)}', 'danger')
                        return redirect(url_for('policies.add'))
            
            db.commit()
            flash('Access policy created successfully!', 'success')
            return redirect(url_for('policies.index'))
            
        except Exception as e:
            db.rollback()
            flash(f'Error creating policy: {str(e)}', 'danger')
    
    # GET request - show form
    users = db.query(User).order_by(User.username).all()
    user_groups = db.query(UserGroup).order_by(UserGroup.name).all()
    servers = db.query(Server).order_by(Server.name).all()
    groups = db.query(ServerGroup).order_by(ServerGroup.name).all()
    
    return render_template('policies/add.html', users=users, user_groups=user_groups, 
                         servers=servers, groups=groups)

@policies_bp.route('/edit/<int:policy_id>', methods=['GET', 'POST'])
@login_required
def edit(policy_id):
    """Edit existing policy with full audit trail"""
    from flask_login import current_user
    from src.core.database import PolicyAuditLog
    import json as json_lib
    
    db = g.db
    policy = db.query(AccessPolicy).filter(AccessPolicy.id == policy_id).first()
    
    if not policy:
        flash('Policy not found', 'danger')
        return redirect(url_for('policies.index'))
    
    if request.method == 'POST':
        try:
            # Capture old state for audit
            old_state = {
                'user_id': policy.user_id,
                'user_group_id': policy.user_group_id,
                'source_ip_id': policy.source_ip_id,
                'scope_type': policy.scope_type,
                'target_group_id': policy.target_group_id,
                'target_server_id': policy.target_server_id,
                'protocol': policy.protocol,
                'port_forwarding_allowed': policy.port_forwarding_allowed,
                'start_time': policy.start_time.isoformat() if policy.start_time else None,
                'end_time': policy.end_time.isoformat() if policy.end_time else None,
                'use_schedules': policy.use_schedules,
                'is_active': policy.is_active,
                'ssh_logins': [login.allowed_login for login in policy.ssh_logins],
                'schedules': [{
                    'id': s.id,
                    'name': s.name,
                    'weekdays': s.weekdays,
                    'time_start': s.time_start.strftime('%H:%M') if s.time_start else None,
                    'time_end': s.time_end.strftime('%H:%M') if s.time_end else None,
                    'months': s.months,
                    'days_of_month': s.days_of_month,
                    'timezone': s.timezone,
                    'is_active': s.is_active
                } for s in policy.schedules]
            }
            
            # Update basic fields
            protocol = request.form.get('protocol') or None
            source_ip_id = request.form.get('source_ip_id')
            port_forwarding_allowed = request.form.get('port_forwarding_allowed') == 'on'
            
            # Parse times
            start_time_str = request.form.get('start_time')
            if start_time_str:
                start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            else:
                start_time = policy.start_time
            
            end_time_str = request.form.get('end_time')
            if end_time_str:
                end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')
            else:
                end_time = policy.end_time
            
            # Parse inactivity timeout
            inactivity_timeout = request.form.get('inactivity_timeout_minutes', '60').strip()
            try:
                inactivity_timeout_minutes = int(inactivity_timeout) if inactivity_timeout else 60
                if inactivity_timeout_minutes < 0:
                    inactivity_timeout_minutes = 0
            except ValueError:
                flash('Invalid inactivity timeout. Keeping current value', 'warning')
                inactivity_timeout_minutes = policy.inactivity_timeout_minutes or 60
            
            # Update policy
            policy.protocol = protocol
            policy.source_ip_id = int(source_ip_id) if source_ip_id else None
            policy.port_forwarding_allowed = port_forwarding_allowed
            policy.start_time = start_time
            policy.end_time = end_time
            policy.inactivity_timeout_minutes = inactivity_timeout_minutes
            
            # Update SSH logins
            db.query(PolicySSHLogin).filter(PolicySSHLogin.policy_id == policy.id).delete()
            ssh_logins = request.form.get('ssh_logins', '').strip()
            if ssh_logins:
                for login in ssh_logins.split(','):
                    login = login.strip()
                    if login:
                        ssh_login = PolicySSHLogin(policy_id=policy.id, allowed_login=login)
                        db.add(ssh_login)
            
            # Update schedules
            use_schedules = request.form.get('use_schedules') == 'on'
            policy.use_schedules = use_schedules
            
            if use_schedules:
                # Get existing schedule IDs
                existing_ids = {s.id for s in policy.schedules}
                
                schedules_json = request.form.get('schedules_json')
                if schedules_json:
                    schedules_data = json_lib.loads(schedules_json)
                    updated_ids = set()
                    
                    for schedule_data in schedules_data:
                        schedule_id = schedule_data.get('id')
                        
                        if schedule_id and int(schedule_id) in existing_ids:
                            # Update existing schedule
                            schedule = db.query(PolicySchedule).get(int(schedule_id))
                            if schedule:
                                schedule.name = schedule_data.get('name')
                                schedule.weekdays = schedule_data.get('weekdays')
                                schedule.time_start = datetime.strptime(schedule_data['time_start'], '%H:%M').time()
                                schedule.time_end = datetime.strptime(schedule_data['time_end'], '%H:%M').time()
                                schedule.months = schedule_data.get('months')
                                schedule.days_of_month = schedule_data.get('days_of_month')
                                schedule.timezone = schedule_data.get('timezone', 'Europe/Warsaw')
                                schedule.is_active = schedule_data.get('is_active', True)
                                updated_ids.add(int(schedule_id))
                        else:
                            # Create new schedule
                            schedule = PolicySchedule(
                                policy_id=policy.id,
                                name=schedule_data.get('name'),
                                weekdays=schedule_data.get('weekdays'),
                                time_start=datetime.strptime(schedule_data['time_start'], '%H:%M').time(),
                                time_end=datetime.strptime(schedule_data['time_end'], '%H:%M').time(),
                                months=schedule_data.get('months'),
                                days_of_month=schedule_data.get('days_of_month'),
                                timezone=schedule_data.get('timezone', 'Europe/Warsaw'),
                                is_active=schedule_data.get('is_active', True)
                            )
                            db.add(schedule)
                    
                    # Delete schedules that weren't in the update
                    for sid in existing_ids - updated_ids:
                        db.query(PolicySchedule).filter(PolicySchedule.id == sid).delete()
            
            # Capture new state
            db.flush()  # Ensure policy.schedules is refreshed
            db.refresh(policy)
            
            new_state = {
                'user_id': policy.user_id,
                'user_group_id': policy.user_group_id,
                'source_ip_id': policy.source_ip_id,
                'scope_type': policy.scope_type,
                'target_group_id': policy.target_group_id,
                'target_server_id': policy.target_server_id,
                'protocol': policy.protocol,
                'port_forwarding_allowed': policy.port_forwarding_allowed,
                'start_time': policy.start_time.isoformat() if policy.start_time else None,
                'end_time': policy.end_time.isoformat() if policy.end_time else None,
                'use_schedules': policy.use_schedules,
                'is_active': policy.is_active,
                'ssh_logins': [login.allowed_login for login in policy.ssh_logins],
                'schedules': [{
                    'id': s.id,
                    'name': s.name,
                    'weekdays': s.weekdays,
                    'time_start': s.time_start.strftime('%H:%M') if s.time_start else None,
                    'time_end': s.time_end.strftime('%H:%M') if s.time_end else None,
                    'months': s.months,
                    'days_of_month': s.days_of_month,
                    'timezone': s.timezone,
                    'is_active': s.is_active
                } for s in policy.schedules]
            }
            
            # Log to audit trail
            audit_log = PolicyAuditLog(
                policy_id=policy.id,
                changed_by_user_id=current_user.id if current_user and hasattr(current_user, 'id') else None,
                change_type='policy_updated',
                full_old_state=old_state,
                full_new_state=new_state
            )
            db.add(audit_log)
            
            db.commit()
            flash('Policy updated successfully!', 'success')
            return redirect(url_for('policies.index'))
            
        except Exception as e:
            db.rollback()
            flash(f'Error updating policy: {str(e)}', 'danger')
            import traceback
            traceback.print_exc()
    
    # GET request - show edit form
    users = db.query(User).order_by(User.username).all()
    user_groups = db.query(UserGroup).order_by(UserGroup.name).all()
    servers = db.query(Server).order_by(Server.name).all()
    groups = db.query(ServerGroup).order_by(ServerGroup.name).all()
    
    # Prepare schedules JSON for JavaScript
    schedules_json = json.dumps([{
        'id': s.id,
        'name': s.name,
        'weekdays': s.weekdays or [],
        'time_start': s.time_start.strftime('%H:%M') if s.time_start else '00:00',
        'time_end': s.time_end.strftime('%H:%M') if s.time_end else '23:59',
        'months': s.months or [],
        'days_of_month': s.days_of_month or [],
        'timezone': s.timezone or 'Europe/Warsaw',
        'is_active': s.is_active
    } for s in policy.schedules])
    
    return render_template('policies/edit.html', 
                         policy=policy,
                         users=users, 
                         user_groups=user_groups,
                         servers=servers, 
                         groups=groups,
                         schedules_json=schedules_json)

@policies_bp.route('/revoke/<int:policy_id>', methods=['POST'])
@login_required
def revoke(policy_id):
    """Revoke policy - set end_time to now (immediate expiry)"""
    db = g.db
    policy = db.query(AccessPolicy).filter(AccessPolicy.id == policy_id).first()
    if not policy:
        abort(404)
    
    try:
        # Set end_time to now - policy expires immediately
        # Keep is_active=True (temporal expiry, not soft delete)
        policy.end_time = datetime.utcnow()
        db.commit()
        flash('Policy revoked successfully! Access expired immediately.', 'success')
    except Exception as e:
        db.rollback()
        flash(f'Error revoking policy: {str(e)}', 'danger')
    
    # Redirect back to referer if available, otherwise to policies list
    return redirect(request.referrer or url_for('policies.index'))

@policies_bp.route('/renew/<int:policy_id>', methods=['POST'])
@login_required
def renew(policy_id):
    """Renew policy - extend end_time by 1 hour"""
    db = g.db
    policy = db.query(AccessPolicy).filter(AccessPolicy.id == policy_id).first()
    if not policy:
        abort(404)
    
    try:
        hours = int(request.form.get('hours', 1))
        now = datetime.utcnow()
        
        # Extend end_time
        if policy.end_time:
            # If policy already expired, extend from now
            if policy.end_time < now:
                policy.end_time = now + timedelta(hours=hours)
                flash(f'Policy reactivated and extended for {hours} hour(s) from now!', 'success')
            else:
                # If still active, extend from current end_time
                policy.end_time = policy.end_time + timedelta(hours=hours)
                flash(f'Policy extended for {hours} hour(s)!', 'success')
        else:
            # If NULL (permanent), set end_time from now
            policy.end_time = now + timedelta(hours=hours)
            flash(f'Permanent policy converted to {hours}-hour grant!', 'success')
        
        db.commit()
    except ValueError:
        db.rollback()
        flash('Invalid number of days', 'danger')
    except Exception as e:
        db.rollback()
        flash(f'Error renewing policy: {str(e)}', 'danger')
    
    return redirect(url_for('policies.index'))

# DELETE endpoint removed - policies cannot be deleted, only revoked
# Full audit trail preserved in policy_audit_log table

@policies_bp.route('/api/user/<int:user_id>/ips')
@login_required
def api_user_ips(user_id):
    """API endpoint to get user's source IPs"""
    db = g.db
    ips = db.query(UserSourceIP).filter(UserSourceIP.user_id == user_id).all()
    return {
        'ips': [{'id': ip.id, 'ip': ip.source_ip, 'label': ip.label} for ip in ips]
    }
