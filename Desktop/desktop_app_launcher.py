#!/usr/bin/env python3
"""
Finance Dashboard Desktop Application Launcher
Handles Flask server startup and PyWebView window management
"""

import os
import sys
import time
import threading
import atexit
import signal
import shutil
from pathlib import Path

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

def initialize_app():
    """Initialize database and Flask app"""
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

    # Create Flask app
    app = create_app()
    print("\nFlask application created successfully")
    return True

def run_flask_server():
    """Run Flask server in background thread"""
    global app
    if app:
        # Suppress Flask startup banner
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

def start_server():
    """Start Flask server in background"""
    global server_thread
    server_thread = threading.Thread(target=run_flask_server, daemon=True)
    server_thread.start()

    print("\nStarting Flask server on port 5000...")

    # Wait for server to be ready (check port availability)
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

def open_window():
    """Open PyWebView window"""
    try:
        import webview

        print("Opening application window...")

        # Create window
        window = webview.create_window(
            'Finance Dashboard',
            'http://127.0.0.1:5000/',
            width=1200,
            height=800,
            min_size=(800, 600)
        )

        # Show window (blocks until closed)
        webview.start()

    except Exception as e:
        print(f"ERROR opening window: {e}")
        import traceback
        traceback.print_exc()
        shutdown_app()

def shutdown_app():
    """Gracefully shutdown Flask server and exit"""
    print("\nShutting down...")
    # Server thread is daemon, so it will be killed when main thread exits
    sys.exit(0)

def signal_handler(sig, frame):
    """Handle Ctrl+C"""
    shutdown_app()

def main():
    """Main application entry point"""
    try:
        # Initialize database and app
        if not initialize_app():
            print("\nFailed to initialize application!")
            input("Press Enter to exit...")
            sys.exit(1)

        # Start Flask server
        if not start_server():
            print("\nERROR: Failed to start Flask server")
            input("Press Enter to exit...")
            sys.exit(1)

        # Register shutdown handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        atexit.register(shutdown_app)

        # Open window (blocks until closed)
        open_window()

    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == '__main__':
    main()
