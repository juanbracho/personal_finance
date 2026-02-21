"""
Authentication for Finance Dashboard.

Two auth mechanisms:
  1. Bearer token  — /api/* routes (Flutter / programmatic clients)
  2. Session login — all web UI routes (browser)

Session auth is only enforced when DASHBOARD_USERNAME env var is set,
so local desktop mode stays auth-free.
"""

import hmac
from flask import (
    Blueprint, request, jsonify, current_app,
    session, redirect, url_for, render_template
)

auth_bp = Blueprint('auth', __name__)

# ---------------------------------------------------------------------------
# Bearer token auth (API routes)
# ---------------------------------------------------------------------------

def check_api_key():
    """
    Validate Bearer token on incoming requests.
    Register this with api_bp.before_request(check_api_key).
    Returns None on success (Flask continues), or a 401 response tuple.
    """
    expected_key = current_app.config.get('API_SECRET_KEY', '')

    # No key configured → running in local dev mode, allow all requests
    if not expected_key:
        return None

    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({
            'error': 'Unauthorized',
            'message': 'Missing or malformed Authorization header. Expected: Bearer <token>'
        }), 401

    token = auth_header[7:]  # Strip "Bearer " prefix
    if not hmac.compare_digest(token, expected_key):
        return jsonify({
            'error': 'Unauthorized',
            'message': 'Invalid API key'
        }), 401

    return None


# ---------------------------------------------------------------------------
# Session auth (web UI routes)
# ---------------------------------------------------------------------------

_SKIP_PATHS = ('/static/', '/api/')
_SKIP_ENDPOINTS = ('auth.login', 'auth.logout')


def check_web_session():
    """
    Enforce session login on all web routes.
    Register this with app.before_request(check_web_session).
    No-op when DASHBOARD_USERNAME is not set (local desktop mode).
    """
    username = current_app.config.get('DASHBOARD_USERNAME', '')
    if not username:
        return None  # Auth not configured — allow everything

    if request.endpoint in _SKIP_ENDPOINTS:
        return None
    if any(request.path.startswith(p) for p in _SKIP_PATHS):
        return None

    if not session.get('logged_in'):
        return redirect(url_for('auth.login', next=request.path))

    return None


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('dashboards.dashboard'))

    error = None
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        expected_user = current_app.config.get('DASHBOARD_USERNAME', '')
        expected_pass = current_app.config.get('DASHBOARD_PASSWORD', '')

        user_ok = hmac.compare_digest(username, expected_user)
        pass_ok = hmac.compare_digest(password, expected_pass)

        if user_ok and pass_ok:
            session['logged_in'] = True
            next_url = request.args.get('next') or url_for('dashboards.dashboard')
            return redirect(next_url)

        error = 'Invalid username or password.'

    return render_template('login.html', error=error)


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
