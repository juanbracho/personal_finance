import os
import json

def get_app_version():
    """Load version information from version.json"""
    try:
        version_file = os.path.join(os.path.dirname(__file__), 'version.json')
        with open(version_file, 'r') as f:
            version_data = json.load(f)
        return version_data
    except Exception:
        return {
            'version': '1.0.0',
            'build_date': 'Unknown',
            'build_number': 0,
            'min_db_version': '1.0.0'
        }

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-for-local-development'

    # PostgreSQL on Neon (or SQLite fallback for local dev without DATABASE_URL)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///personal_finance.db'

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    # File upload settings for update packages
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB max upload size for updates

    # JWT authentication (Phase 2 auth overhaul)
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'dev-jwt-secret')

    # Allowed CORS origins for the web frontend.
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS') or '*'

    # IANA timezone name used by local_now() to pick the correct default month/year.
    # Set APP_TIMEZONE on Railway to match the owner's timezone, e.g. America/Chicago.
    APP_TIMEZONE = os.environ.get('APP_TIMEZONE', 'UTC')


class ProductionConfig(Config):
    """Configuration for Railway cloud deployment.

    Environment variables required on Railway:
      - DATABASE_URL     → Neon PostgreSQL connection string
      - SECRET_KEY       → Flask session secret
      - JWT_SECRET_KEY   → JWT signing secret (openssl rand -hex 32)
      - CORS_ORIGINS     → comma-separated allowed origins,
                           e.g. https://finance.juanbracho.com
    """
    SQLALCHEMY_ECHO = False
    DEBUG = False
    ENV = 'production'
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('DATABASE_URL') or 'sqlite:////data/personal_finance.db'
    )
    # Secure cookie settings
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'
