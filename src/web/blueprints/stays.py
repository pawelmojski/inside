"""Stays blueprint - Person presence tracking with session tree view."""

from flask import Blueprint, render_template, request, abort
from flask_login import login_required, current_user
from src.core.database import get_db, Stay, Session
from datetime import datetime
from sqlalchemy import desc

stays_bp = Blueprint('stays', __name__, url_prefix='/stays')


@stays_bp.route('/')
@login_required
def list():
    """List all stays with expandable session tree (filtered for regular users)."""
    db = next(get_db())
    
    # Check permission level for filtering
    is_regular_user = current_user.permission_level >= 900
    
    # Filters
    person_filter = request.args.get('person', '').strip()
    status_filter = request.args.get('status', 'all')  # all, active, ended
    
    # Base query
    query = db.query(Stay)
    
    # Filter by user for regular users
    if is_regular_user:
        query = query.filter(Stay.user_id == current_user.id)
    else:
        # Apply optional person filter for admins
        if person_filter:
            query = query.join(Stay.user).filter(Stay.user.has(username=person_filter))
    
    if status_filter == 'active':
        query = query.filter(Stay.is_active == True)
    elif status_filter == 'ended':
        query = query.filter(Stay.is_active == False)
    
    # Order by most recent first
    stays = query.order_by(desc(Stay.started_at)).limit(100).all()
    
    # Calculate stats
    if is_regular_user:
        total_stays = db.query(Stay).filter(Stay.user_id == current_user.id).count()
        active_stays = db.query(Stay).filter(Stay.user_id == current_user.id, Stay.is_active == True).count()
    else:
        total_stays = db.query(Stay).count()
        active_stays = db.query(Stay).filter(Stay.is_active == True).count()
    
    return render_template(
        'stays/list.html',
        stays=stays,
        person_filter=person_filter,
        status_filter=status_filter,
        total_stays=total_stays,
        active_stays=active_stays,
        is_regular_user=is_regular_user
    )


@stays_bp.route('/<int:stay_id>')
@login_required
def detail(stay_id):
    """Stay detail view with all sessions (permission-checked)."""
    db = next(get_db())
    
    stay = db.query(Stay).filter(Stay.id == stay_id).first()
    if not stay:
        abort(404)
    
    # Check permission: level 900 can only view own stays
    if current_user.permission_level >= 900 and stay.user_id != current_user.id:
        abort(403)  # Forbidden
    
    # Get all sessions for this stay (ordered by start time)
    sessions = db.query(Session).filter(
        Session.stay_id == stay_id
    ).order_by(Session.started_at).all()
    
    return render_template(
        'stays/detail.html',
        stay=stay,
        sessions=sessions
    )
