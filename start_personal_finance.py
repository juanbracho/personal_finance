#!/usr/bin/env python3
"""
Personal Finance Dashboard Server Startup Script
Cross-platform Python script that works on Windows, macOS, and Linux
"""

import subprocess
import webbrowser
import time
import os
import sys
import signal
import threading
from pathlib import Path

def print_banner():
    """Print the startup banner"""
    print("")
    print("=" * 41)
    print("  💰 PERSONAL FINANCE DASHBOARD 💰")
    print("=" * 41)
    print("")
    print("Starting server...")
    print("")

def check_python():
    """Check if Python is available and return the command"""
    if sys.version_info >= (3, 6):
        return sys.executable
    else:
        print("❌ Error: Python 3.6+ is required")
        print(f"Current version: {sys.version}")
        sys.exit(1)

def start_server(python_cmd):
    """Start the Flask server"""
    print("🚀 Starting Flask server...")
    
    # Change to the script's directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    try:
        # Start the Flask server
        process = subprocess.Popen([python_cmd, 'app.py'], 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE)
        
        # Wait for server to start
        print("⏳ Waiting for server to initialize...")
        time.sleep(3)
        
        # Check if process is still running
        if process.poll() is None:
            print("✅ Server started successfully!")
            print(f"✅ Server PID: {process.pid}")
            print("")
            print("📋 Server is running at: http://127.0.0.1:5001/")
            print("")
            
            # Open browser
            print("🌐 Opening dashboard in browser...")
            try:
                webbrowser.open("http://127.0.0.1:5001/")
                print("✅ Dashboard opened in browser")
            except Exception as e:
                print(f"⚠️  Could not open browser automatically: {e}")
                print("⚠️  Please manually open: http://127.0.0.1:5001/")
            
            print("")
            print("⚠️  KEEP THIS TERMINAL OPEN while using the dashboard")
            print("❌ Press Ctrl+C to stop the server")
            print("")
            print("=" * 41)
            
            # Set up signal handler for graceful shutdown
            def signal_handler(sig, frame):
                print("")
                print("🛑 Stopping server...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                print("✅ Server stopped")
                sys.exit(0)
            
            signal.signal(signal.SIGINT, signal_handler)
            
            # Keep the script running and monitor the server
            try:
                process.wait()
            except KeyboardInterrupt:
                signal_handler(None, None)
        else:
            stdout, stderr = process.communicate()
            print("❌ Failed to start server")
            if stderr:
                print(f"Error: {stderr.decode()}")
            sys.exit(1)
            
    except FileNotFoundError:
        print("❌ Error: app.py not found in the current directory")
        print("Make sure you're running this script from the Personal Finance App folder")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

def main():
    """Main function"""
    print_banner()
    python_cmd = check_python()
    start_server(python_cmd)

if __name__ == "__main__":
    main()
