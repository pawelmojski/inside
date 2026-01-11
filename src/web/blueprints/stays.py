"""Stays blueprint - Person presence tracking with session tree view."""

from flask import Blueprint, render_template, request
from src.core.database import get_db, Stay, Session
from datetime import datetime
from sqlalchemy import desc

stays_bp = Blueprint('stays', __name__, url_prefix='/stays')


@stays_bp.route('/')
def list():
    """List all stays with expandable session tree."""
    db = next(get_db())
    
    # Filters
    person_filter = request.args.get('person', '').strip()
    status_filter = request.args.get('status', 'all')  # all, active, ended
    
    # Base query
    query = db.query(Stay)
    
    # Apply filters
    if person_filter:
        query = query.join(Stay.user).filter(Stay.user.has(username=person_filter))
    
    if status_filter == 'active':
        query = query.filter(Stay.is_active == True)
    elif status_filter == 'ended':
        query = query.filter(Stay.is_active == False)
    
    # Order by most recent first
    stays = query.order_by(desc(Stay.started_at)).limit(100).all()
    
    # Calculate stats
    total_stays = db.query(Stay).count()
    active_stays = db.query(Stay).filter(Stay.is_active == True).count()
    
    return render_template(
        'stays/list.html',
        stays=stays,
        person_filter=person_filter,
        status_filter=status_filter,
        total_stays=total_stays,
        active_stays=active_stays
    )


@stays_bp.route('/<int:stay_id>')
def detail(stay_id):
    """Stay detail view with all sessions."""
    db = next(get_db())
    
    stay = db.query(Stay).filter(Stay.id == stay_id).first()
    if not stay:
        return "Stay not found", 404
    
    # Get all sessions for this stay (ordered by start time)
    sessions = db.query(Session).filter(
        Session.stay_id == stay_id
    ).order_by(Session.started_at).all()
    
    return render_template(
        'stays/detail.html',
        stay=stay,
        sessions=sessions
    )
