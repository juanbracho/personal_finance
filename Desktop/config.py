import os
import json

def get_app_version():
    """Load version information from version.json"""
    try:
        version_file = os.path.join(os.path.dirname(__file__), 'version.json')
        with open(version_file, 'r') as f:
            version_data = json.load(f)
        return version_data
    except Exception as e:
        # Fallback if version.json is missing
        return {
            'version': '1.0.0',
            'build_date': 'Unknown',
            'build_number': 0,
            'min_db_version': '1.0.0'
        }

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-for-local-development'

    # Personal Finance Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///personal_finance.db'

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = True  # Enable SQL logging for debugging

    # File upload settings for update packages
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB max upload size for updates

    # API authentication key (Bearer token).
    # Empty string = no auth enforced (local dev mode).
    # Set via API_SECRET_KEY environment variable in production.
    API_SECRET_KEY = os.environ.get('API_SECRET_KEY') or ''

    # Allowed CORS origins for the web frontend.
    # Restrict to your domain in production.
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS') or '*'

    # Web dashboard login credentials.
    # When empty, session auth is skipped (local desktop mode).
    DASHBOARD_USERNAME = os.environ.get('DASHBOARD_USERNAME') or ''
    DASHBOARD_PASSWORD = os.environ.get('DASHBOARD_PASSWORD') or ''


class DesktopConfig(Config):
    """Configuration for the macOS desktop application (PyWebView)."""
    SQLALCHEMY_ECHO = False
    DEBUG = False
    ENV = 'production'


class ProductionConfig(Config):
    """Configuration for Railway cloud deployment.

    Environment variables required on Railway:
      - API_SECRET_KEY   → long random secret shared with all clients
      - DATABASE_URL     → path to SQLite file on the persistent volume,
                           e.g. sqlite:////data/personal_finance.db
      - SECRET_KEY       → Flask session secret
      - CORS_ORIGINS     → comma-separated allowed origins,
                           e.g. https://finance.juanbracho.com
    """
    SQLALCHEMY_ECHO = False
    DEBUG = False
    ENV = 'production'
    # Railway volume mounts the DB at /data; override DATABASE_URL if set
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('DATABASE_URL') or 'sqlite:////data/personal_finance.db'
    )