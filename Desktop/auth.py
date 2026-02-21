"""
API key authentication middleware for Finance Dashboard.

Used as a before_request hook on the /api blueprint.
All requests to /api/* must include:
    Authorization: Bearer <API_SECRET_KEY>

If API_SECRET_KEY is not configured (empty string), auth is skipped.
This allows the app to run without a key in local dev mode.
"""

from flask import request, jsonify, current_app


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
    if token != expected_key:
        return jsonify({
            'error': 'Unauthorized',
            'message': 'Invalid API key'
        }), 401

    return None  # Auth passed
