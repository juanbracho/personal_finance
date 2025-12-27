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
from pathlib import Path

# Ensure data directory exists
data_dir = Path(__file__).parent / 'data'
data_dir.mkdir(parents=True, exist_ok=True)

# Set up working directory (important for relative paths)
os.chdir(Path(__file__).parent)

# Initialize Flask app
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
