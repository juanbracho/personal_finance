"""
Authentication for Finance Dashboard.

Two auth mechanisms:
  1. Bearer JWT  — /api/* routes (Flutter / programmatic clients)
  2. Session     — all web UI routes (browser)

Auth is bypassed when JWT_SECRET_KEY == 'dev-jwt-secret' (the config default).
Railway always sets a real key → auth is always enforced in production.
Local dev without a .env file → auth-free.
"""

import time
import uuid
import datetime

import jwt
from werkzeug.security import check_password_hash
from flask import (
    Blueprint, request, jsonify, current_app,
    session, redirect, url_for, render_template
)

SESSION_LIFETIME_SECONDS = 3600  # 1 hour

auth_bp = Blueprint('auth', __name__)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_DEV_JWT_SECRET = 'dev-jwt-secret'

_API_PUBLIC_ENDPOINTS = {'api.api_login'}


def _auth_disabled():
    """Return True when running in local dev mode (no real JWT secret configured)."""
    return current_app.config.get('JWT_SECRET_KEY', _DEV_JWT_SECRET) == _DEV_JWT_SECRET


def _log_audit(action, user_id=None, extra=None):
    """Append a row to audit_logs. Swallows errors so auth never breaks."""
    try:
        from models import db, AuditLog
        entry = AuditLog(
            user_id=user_id,
            action=action,
            ip_address=request.remote_addr,
            extra_data=extra or {},
        )
        db.session.add(entry)
        db.session.commit()
    except Exception as exc:
        current_app.logger.warning("audit_log write failed: %s", exc)


def _issue_jwt(user):
    """Return a signed JWT string for *user* (a User model instance)."""
    now = datetime.datetime.utcnow()
    payload = {
        'user_id': user.id,
        'username': user.username,
        'role': user.role,
        'exp': now + datetime.timedelta(seconds=SESSION_LIFETIME_SECONDS),
        'jti': uuid.uuid4().hex,
    }
    return jwt.encode(
        payload,
        current_app.config['JWT_SECRET_KEY'],
        algorithm='HS256',
    )


# ---------------------------------------------------------------------------
# Bearer JWT auth (API routes)
# ---------------------------------------------------------------------------

def check_jwt():
    """
    Validate Bearer JWT on incoming API requests.
    Register with: api_bp.before_request(check_jwt)
    Returns None on success; 401 JSON response on failure.
    """
    if request.endpoint in _API_PUBLIC_ENDPOINTS:
        return None

    if _auth_disabled():
        return None

    # Web-session users accessing API endpoints — still valid
    if session.get('user_id') and _session_valid():
        return None

    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({
            'error': 'Unauthorized',
            'message': 'Missing or malformed Authorization header. Expected: Bearer <token>',
        }), 401

    token = auth_header[7:]
    try:
        payload = jwt.decode(
            token,
            current_app.config['JWT_SECRET_KEY'],
            algorithms=['HS256'],
        )
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Unauthorized', 'message': 'Token has expired.'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Unauthorized', 'message': 'Invalid token.'}), 401

    # Check revocation list
    jti = payload.get('jti')
    if jti:
        try:
            from models import db, RevokedToken
            revoked = db.session.query(RevokedToken).filter_by(jti=jti).first()
            if revoked:
                return jsonify({'error': 'Unauthorized', 'message': 'Token has been revoked.'}), 401
        except Exception as exc:
            current_app.logger.warning("revoked_tokens check failed: %s", exc)

    return None


# ---------------------------------------------------------------------------
# Session auth (web UI routes)
# ---------------------------------------------------------------------------

_SKIP_PATHS = ('/static/', '/api/')
_SKIP_ENDPOINTS = ('auth.login', 'auth.logout', 'onboarding.onboarding', 'onboarding.onboarding_complete')


def _session_valid():
    login_time = session.get('login_time', 0)
    return time.time() - login_time <= SESSION_LIFETIME_SECONDS


def check_web_session():
    """
    Enforce session login on all web routes.
    Register with: app.before_request(check_web_session)
    No-op when JWT_SECRET_KEY is the dev default.
    """
    if _auth_disabled():
        return None

    if request.endpoint in _SKIP_ENDPOINTS:
        return None
    if any(request.path.startswith(p) for p in _SKIP_PATHS):
        return None

    if not session.get('user_id'):
        return redirect(url_for('auth.login', next=request.path))

    if not _session_valid():
        session.clear()
        return redirect(url_for('auth.login', next=request.path))

    return None


# ---------------------------------------------------------------------------
# Login / Logout routes
# ---------------------------------------------------------------------------

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if _auth_disabled():
        return redirect(url_for('dashboards.dashboard'))

    if session.get('user_id') and _session_valid():
        return redirect(url_for('dashboards.dashboard'))

    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = _lookup_user(username)

        if user and user.is_active and user.password_hash and check_password_hash(user.password_hash, password):
            session.clear()
            session['user_id'] = user.id
            session['login_time'] = time.time()
            session['role'] = user.role
            _log_audit('login_success', user_id=user.id, extra={'username': username})
            if not user.onboarded:
                return redirect(url_for('onboarding.onboarding'))
            next_url = request.args.get('next') or url_for('dashboards.dashboard')
            return redirect(next_url)

        _log_audit('login_failure', extra={'username': username, 'ip': request.remote_addr})
        error = 'Invalid username or password.'

    return render_template('login.html', error=error)


@auth_bp.route('/logout')
def logout():
    user_id = session.get('user_id')

    # Revoke Bearer token if the client also sent one
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer ') and not _auth_disabled():
        token = auth_header[7:]
        try:
            payload = jwt.decode(
                token,
                current_app.config['JWT_SECRET_KEY'],
                algorithms=['HS256'],
            )
            jti = payload.get('jti')
            if jti:
                from models import db, RevokedToken
                db.session.add(RevokedToken(jti=jti, user_id=user_id))
                db.session.commit()
        except jwt.InvalidTokenError:
            pass  # Expired or invalid — no need to revoke

    _log_audit('logout', user_id=user_id)
    session.clear()
    return redirect(url_for('auth.login'))


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def require_admin():
    """
    Returns None if the current session user has role='admin' (proceed).
    Returns a redirect response otherwise (403 flash → dashboard).
    Bypassed in dev mode.
    """
    if _auth_disabled():
        return None
    if session.get('role') != 'admin':
        flash('Admin access required.', 'error')
        return redirect(url_for('dashboards.dashboard'))
    return None


def _lookup_user(username):
    """Return the User ORM object for *username*, or None."""
    try:
        from models import db, User
        return db.session.query(User).filter_by(username=username).first()
    except Exception as exc:
        current_app.logger.error("User lookup failed: %s", exc)
        return None
