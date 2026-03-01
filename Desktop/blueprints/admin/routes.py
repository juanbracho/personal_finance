from flask import Blueprint, render_template, request, flash, redirect, url_for
from werkzeug.security import generate_password_hash
from models import db, User
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from auth import require_admin, _log_audit
from utils import current_user_id

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.before_request
def gate():
    result = require_admin()
    if result is not None:
        return result


@admin_bp.route('/')
def admin_dashboard():
    return redirect(url_for('settings.index'))


@admin_bp.route('/users/create', methods=['POST'])
def create_user():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    email = request.form.get('email', '').strip() or None
    role = request.form.get('role', 'member')

    if not username or not password:
        flash('Username and password are required.', 'error')
        return redirect(url_for('settings.index'))

    if role not in ('member', 'admin'):
        role = 'member'

    new_user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        role=role,
        is_active=True,
    )
    try:
        db.session.add(new_user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash(f'Username "{username}" is already taken.', 'error')
        return redirect(url_for('settings.index'))

    _log_audit('user_created', current_user_id(), extra={'new_username': username})
    flash(f'User "{username}" created successfully.', 'success')
    return redirect(url_for('settings.index'))


@admin_bp.route('/users/<int:user_id>/deactivate', methods=['POST'])
def deactivate_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('settings.index'))

    if user.id == current_user_id():
        flash('You cannot deactivate your own account.', 'error')
        return redirect(url_for('settings.index'))

    user.is_active = False
    db.session.commit()
    _log_audit('user_deactivated', current_user_id(), extra={'target_user_id': user_id})
    flash(f'User "{user.username}" has been deactivated.', 'success')
    return redirect(url_for('settings.index'))


@admin_bp.route('/users/<int:user_id>/activate', methods=['POST'])
def activate_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('settings.index'))

    user.is_active = True
    db.session.commit()
    _log_audit('user_activated', current_user_id(), extra={'target_user_id': user_id})
    flash(f'User "{user.username}" has been activated.', 'success')
    return redirect(url_for('settings.index'))


@admin_bp.route('/audit-logs')
def audit_logs():
    filter_user_id = request.args.get('user_id', '').strip()
    filter_action = request.args.get('action', '').strip()

    where_clauses = []
    params = {}

    if filter_user_id:
        where_clauses.append('al.user_id = :user_id')
        params['user_id'] = filter_user_id

    if filter_action:
        where_clauses.append('al.action ILIKE :action')
        params['action'] = f'%{filter_action}%'

    where_sql = ('WHERE ' + ' AND '.join(where_clauses)) if where_clauses else ''

    sql = text(f"""
        SELECT al.id, al.action, al.ip_address, al.extra_data, al.created_at,
               u.username
        FROM audit_logs al
        LEFT JOIN users u ON u.id = al.user_id
        {where_sql}
        ORDER BY al.created_at DESC
        LIMIT 200
    """)

    with db.engine.connect() as conn:
        rows = conn.execute(sql, params).mappings().all()

    logs = [dict(r) for r in rows]
    return render_template(
        'admin_audit_logs.html',
        logs=logs,
        filter_user_id=filter_user_id,
        filter_action=filter_action,
    )
