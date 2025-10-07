#!/bin/bash

# Personal Finance Dashboard Server Startup Script for macOS
# Double-click this file to start the server and open browser

echo ""
echo "========================================="
echo "  💰 PERSONAL FINANCE DASHBOARD 💰"
echo "========================================="
echo ""
echo "Starting server..."
echo ""

# Change to the script's directory (where app.py is located)
cd "$(dirname "$0")"

# Check if Python 3 is available
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Error: Python is not installed or not in PATH"
    echo "Please install Python 3 and try again"
    echo ""
    echo "Press any key to exit..."
    read -n 1
    exit 1
fi

# Start the Flask server in background
echo "🚀 Starting Flask server..."
$PYTHON_CMD app.py &
SERVER_PID=$!

# Wait for server to start (3 seconds)
echo "⏳ Waiting for server to initialize..."
sleep 3

# Check if server is running
if ps -p $SERVER_PID > /dev/null; then
    echo "✅ Server started successfully!"
    echo "✅ Server PID: $SERVER_PID"
    echo ""
    echo "📋 Server is running at: http://127.0.0.1:5001/"
    echo ""
    
    # Open the dashboard in the default browser
    echo "🌐 Opening dashboard in browser..."
    open "http://127.0.0.1:5001/"
    echo "✅ Dashboard opened in browser"
    
    echo ""
    echo "⚠️  KEEP THIS WINDOW OPEN while using the dashboard"
    echo "❌ Close this window to stop the server"
    echo ""
    echo "========================================="
    
    # Wait for user to close the window
    echo "Press any key to stop the server..."
    read -n 1
    
    echo ""
    echo "🛑 Stopping server..."
    kill $SERVER_PID
    echo "✅ Server stopped"
    echo "Press any key to exit..."
    read -n 1
else
    echo "❌ Failed to start server"
    echo "Press any key to exit..."
    read -n 1
    exit 1
fi

