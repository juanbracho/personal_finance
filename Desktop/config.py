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

class DesktopConfig(Config):
    """Configuration for desktop application"""
    SQLALCHEMY_ECHO = False  # Disable SQL logging in desktop mode for cleaner output
    DEBUG = False  # Disable Flask debug mode in standalone app
    ENV = 'production'