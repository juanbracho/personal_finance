#!/bin/bash

# Personal Finance Dashboard Server Startup Script for macOS/iOS
# This script starts the Flask server and opens the dashboard in the browser

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
    if command -v open &> /dev/null; then
        # macOS
        open "http://127.0.0.1:5001/"
    elif command -v xdg-open &> /dev/null; then
        # Linux
        xdg-open "http://127.0.0.1:5001/"
    else
        echo "⚠️  Please manually open: http://127.0.0.1:5001/"
    fi
    
    echo ""
    echo "⚠️  KEEP THIS TERMINAL OPEN while using the dashboard"
    echo "❌ Press Ctrl+C to stop the server"
    echo ""
    echo "========================================="
    
    # Wait for user to stop the server
    trap 'echo ""; echo "🛑 Stopping server..."; kill $SERVER_PID; echo "✅ Server stopped"; exit 0' INT
    wait $SERVER_PID
else
    echo "❌ Failed to start server"
    exit 1
fi
