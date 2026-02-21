#!/usr/bin/env python3
"""
Finance Dashboard Desktop Application Launcher

Modes of operation
------------------
1. Local desktop (default):
   Starts a local Flask server on 127.0.0.1:5000, then opens a PyWebView
   window pointing at http://127.0.0.1:5000/.

2. Cloud desktop (FINANCE_API_URL is set):
   Skips the local Flask server entirely and opens a PyWebView window
   pointing at the cloud URL (e.g. https://finance.juanbracho.com).
   The local API key is read from ~/.financed/config.json and injected
   into the PyWebView window via JavaScript so all fetch() calls are
   authenticated against the remote API.

3. Railway cloud server (RAILWAY_ENVIRONMENT is set):
   Runs Flask as a plain HTTP server on 0.0.0.0:$PORT with no PyWebView.
   This is the mode used when the app is deployed to Railway.

Environment variables
---------------------
FINANCE_API_URL       URL of the cloud backend (enables mode 2)
RAILWAY_ENVIRONMENT   Set automatically by Railway (enables mode 3)
PORT                  Port for Railway server (default 8080)
"""

import os
import sys
import time
import threading
import atexit
import signal
import shutil
from pathlib import Path


# ---------------------------------------------------------------------------
# Detect run mode early — before any heavy imports
# ---------------------------------------------------------------------------
RAILWAY_MODE = os.environ.get('RAILWAY_ENVIRONMENT') is not None
FINANCE_API_URL = os.environ.get('FINANCE_API_URL', '').rstrip('/')

def get_bundle_path():
    """Get the path where bundled resources are located"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    else:
        return Path(__file__).parent

def get_user_data_path():
    """Get writable user data path for the application"""
    if sys.platform == 'darwin':
        # macOS: ~/Library/Application Support/FinanceDashboard
        user_data = Path.home() / 'Library' / 'Application Support' / 'FinanceDashboard'
    elif sys.platform == 'win32':
        # Windows: %APPDATA%/FinanceDashboard
        user_data = Path(os.environ.get('APPDATA', Path.home())) / 'FinanceDashboard'
    else:
        # Linux: ~/.local/share/FinanceDashboard
        user_data = Path.home() / '.local' / 'share' / 'FinanceDashboard'

    return user_data

def setup_data_directory():
    """Setup writable data directory, copying from bundle if needed"""
    bundle_path = get_bundle_path()

    if getattr(sys, 'frozen', False):
        # Running as packaged app - use user data directory
        user_data_path = get_user_data_path()
        user_data_path.mkdir(parents=True, exist_ok=True)

        # Create data subdirectory
        data_dir = user_data_path / 'data'
        data_dir.mkdir(parents=True, exist_ok=True)

        # Create backups subdirectory
        backups_dir = data_dir / 'backups'
        backups_dir.mkdir(parents=True, exist_ok=True)

        # Copy database from bundle if user doesn't have one yet
        bundle_db = bundle_path / 'data' / 'personal_finance.db'
        user_db = data_dir / 'personal_finance.db'

        if bundle_db.exists() and not user_db.exists():
            print(f"Copying database to user data directory...")
            shutil.copy2(bundle_db, user_db)
            print(f"Database copied to: {user_db}")

        # Copy templates, static, and other resources to user directory
        for resource in ['templates', 'static', 'version.json']:
            bundle_resource = bundle_path / resource
            user_resource = user_data_path / resource

            if bundle_resource.exists():
                if bundle_resource.is_dir():
                    if user_resource.exists():
                        shutil.rmtree(user_resource)
                    shutil.copytree(bundle_resource, user_resource)
                else:
                    shutil.copy2(bundle_resource, user_resource)

        # Copy blueprints
        bundle_blueprints = bundle_path / 'blueprints'
        if bundle_blueprints.exists():
            # We need blueprints in the path, so add bundle_path to sys.path
            if str(bundle_path) not in sys.path:
                sys.path.insert(0, str(bundle_path))

        # Set working directory to user data path
        os.chdir(user_data_path)
        print(f"[APP] User data directory: {user_data_path}")
        print(f"[APP] Working directory: {os.getcwd()}")

        return user_data_path
    else:
        # Running from source - use source directory
        data_dir = bundle_path / 'data'
        data_dir.mkdir(parents=True, exist_ok=True)
        os.chdir(bundle_path)
        print(f"[DEV] Source directory: {bundle_path}")
        print(f"[DEV] Working directory: {os.getcwd()}")

        return bundle_path

# Setup data directory before importing app
WORKING_PATH = setup_data_directory()

# Now import Flask app (after working directory is set)
from app import create_app, initialize_personal_finance_database, test_database_connection

app = None
server_thread = None


# ---------------------------------------------------------------------------
# Local config helper (~/.financed/config.json) — used in cloud desktop mode
# ---------------------------------------------------------------------------

def get_local_api_key():
    """Read API key from ~/.financed/config.json (cloud desktop mode)."""
    config_path = Path.home() / '.financed' / 'config.json'
    try:
        import json
        with open(config_path) as f:
            data = json.load(f)
        return data.get('api_key', '')
    except Exception:
        return ''


def ensure_local_config_dir():
    """Create ~/.financed/ directory if it doesn't exist."""
    config_dir = Path.home() / '.financed'
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / 'config.json'
    if not config_path.exists():
        import json
        config_path.write_text(json.dumps({
            'api_key': '',
            'api_url': ''
        }, indent=2))
        print(f"[CONFIG] Created config template at {config_path}")
        print(f"[CONFIG] Fill in api_key and api_url to enable cloud desktop mode")


# ---------------------------------------------------------------------------
# App initialisation (local mode only)
# ---------------------------------------------------------------------------

def initialize_app():
    """Initialize database and Flask app (local / Railway mode)."""
    global app

    print("Finance Dashboard - Desktop Application")
    print("=" * 50)

    # Initialize database
    print("\nInitializing database...")
    if not initialize_personal_finance_database():
        print("ERROR: Database initialization failed")
        return False

    if not test_database_connection():
        print("ERROR: Database connection test failed")
        return False

    # Pick config class
    if RAILWAY_MODE:
        from config import ProductionConfig
        app = create_app(ProductionConfig)
        print("\nFlask application created (Railway/production mode)")
    else:
        from config import DesktopConfig
        app = create_app(DesktopConfig)
        print("\nFlask application created (local desktop mode)")

    return True


# ---------------------------------------------------------------------------
# Flask server helpers
# ---------------------------------------------------------------------------

def run_flask_server():
    """Run Flask server in background thread (local desktop mode)."""
    global app
    if app:
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)

        app.run(
            debug=False,
            host='127.0.0.1',
            port=5000,
            use_reloader=False,
            threaded=True
        )


def run_flask_server_railway():
    """Run Flask server for Railway (foreground, 0.0.0.0, dynamic port)."""
    global app
    if app:
        port = int(os.environ.get('PORT', 8080))
        print(f"\nStarting Flask server on 0.0.0.0:{port} (Railway mode)...")
        app.run(
            debug=False,
            host='0.0.0.0',
            port=port,
            use_reloader=False,
            threaded=True
        )


def start_server():
    """Start local Flask server in background thread, wait until ready."""
    global server_thread
    server_thread = threading.Thread(target=run_flask_server, daemon=True)
    server_thread.start()

    print("\nStarting Flask server on port 5000...")

    for attempt in range(30):
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', 5000))
            sock.close()
            if result == 0:
                print("Flask server is ready!")
                return True
        except Exception:
            pass
        time.sleep(0.5)

    print("ERROR: Flask server failed to start")
    return False


# ---------------------------------------------------------------------------
# PyWebView window helpers
# ---------------------------------------------------------------------------

def _on_webview_loaded(window, api_key):
    """Inject FINANCE_API_KEY into the window after the page loads."""
    if api_key:
        window.evaluate_js(f'window.FINANCE_API_KEY = "{api_key}";')


def open_window(url='http://127.0.0.1:5000/', api_key=''):
    """Open PyWebView window pointing at url."""
    try:
        import webview

        print(f"Opening application window → {url}")

        window = webview.create_window(
            'Finance Dashboard',
            url,
            width=1200,
            height=800,
            min_size=(800, 600)
        )

        if api_key:
            # Inject key after every page load so it survives navigation
            window.events.loaded += lambda: _on_webview_loaded(window, api_key)

        webview.start()

    except Exception as e:
        print(f"ERROR opening window: {e}")
        import traceback
        traceback.print_exc()
        shutdown_app()


# ---------------------------------------------------------------------------
# Shutdown
# ---------------------------------------------------------------------------

def shutdown_app():
    """Gracefully shutdown Flask server and exit."""
    print("\nShutting down...")
    sys.exit(0)


def signal_handler(sig, frame):
    """Handle Ctrl+C / SIGTERM."""
    shutdown_app()


# ---------------------------------------------------------------------------
# Entry point — three modes
# ---------------------------------------------------------------------------

def main():
    """Main application entry point."""
    try:
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # ------------------------------------------------------------------
        # MODE 3: Railway cloud server
        # ------------------------------------------------------------------
        if RAILWAY_MODE:
            print("[MODE] Railway cloud server")
            if not initialize_app():
                print("ERROR: Application initialization failed")
                sys.exit(1)
            atexit.register(shutdown_app)
            run_flask_server_railway()  # blocks until process is killed
            return

        # ------------------------------------------------------------------
        # MODE 2: Cloud desktop (FINANCE_API_URL is set)
        # ------------------------------------------------------------------
        if FINANCE_API_URL:
            print(f"[MODE] Cloud desktop → {FINANCE_API_URL}")
            ensure_local_config_dir()
            api_key = get_local_api_key()
            if not api_key:
                print("[WARN] No api_key found in ~/.financed/config.json")
                print("[WARN] API calls will be unauthenticated")
            atexit.register(shutdown_app)
            open_window(url=FINANCE_API_URL, api_key=api_key)  # blocks
            return

        # ------------------------------------------------------------------
        # MODE 1: Local desktop (default)
        # ------------------------------------------------------------------
        print("[MODE] Local desktop")
        if not initialize_app():
            print("\nFailed to initialize application!")
            input("Press Enter to exit...")
            sys.exit(1)

        if not start_server():
            print("\nERROR: Failed to start Flask server")
            input("Press Enter to exit...")
            sys.exit(1)

        atexit.register(shutdown_app)
        open_window()  # blocks until window is closed

    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
        sys.exit(1)


if __name__ == '__main__':
    main()
