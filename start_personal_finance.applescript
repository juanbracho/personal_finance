-- Personal Finance Dashboard Launcher for macOS
-- This creates a double-clickable application

tell application "Terminal"
    activate
    do script "cd \"$(dirname \"$0\")\" && chmod +x start_personal_finance.sh && ./start_personal_finance.sh"
end tell

