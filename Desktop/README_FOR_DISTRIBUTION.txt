================================
FINANCE DASHBOARD - Desktop App
================================

INSTALLATION INSTRUCTIONS
=========================

For macOS:
----------
1. Drag "FinanceDashboard.app" to your Applications folder (or anywhere you like)

2. FIRST TIME OPENING:
   - Right-click on "FinanceDashboard.app"
   - Click "Open"
   - Click "Open" again when macOS asks for confirmation

   (This is required because the app isn't from the Mac App Store)

3. AFTER FIRST TIME:
   - Just double-click the app like any other application!


For Windows:
------------
NOTE: This version is currently built for macOS only.

To create a Windows version:
1. The developer needs to build the app on a Windows machine
2. The process is identical, just run the build script on Windows
3. You'll get a .exe file instead of a .app file

If you need a Windows version, please contact the person who shared this app.


REQUIREMENTS
============
✅ NONE! Everything is included.

You DO NOT need to install:
- Python
- Flask
- Any programming tools
- Any dependencies

The app is completely self-contained and works offline.


WHAT THIS APP DOES
==================
Finance Dashboard helps you:
- Track income and expenses
- Manage budgets by category
- Monitor debt accounts
- View spending analytics and charts
- Export and import your financial data
- Create backups before updates
- All data is stored locally on YOUR computer


YOUR DATA & BACKUPS
===================
- All data is stored locally inside the app on YOUR computer
- No internet connection needed
- No data is sent anywhere
- Each user has their own separate database

BACKUP & RESTORE FEATURE:
- Click "Settings" (⚙️) in the navigation bar
- **EXPORT**: Download your database before updates (saves to Downloads folder)
- **IMPORT**: Upload/restore a backup database file
- **LOCAL BACKUP**: Create backup stored in app's backup folder
- **DANGER ZONE**: Option to delete all data (creates backup first)


BEFORE UPDATING TO A NEW VERSION
=================================
🚨 IMPORTANT: Always backup your data before updating! 🚨

1. Open the CURRENT version of the app
2. Click "Settings" (⚙️ gear icon) in the top navigation
3. Click "Export Database (Download)" button
4. Your database will be saved to your Downloads folder with a timestamp
5. KEEP THIS FILE SAFE!
6. Now you can install the new version

AFTER INSTALLING THE NEW VERSION
=================================
1. Open the NEW version of the app
2. Click "Settings" (⚙️ gear icon)
3. Click "Import Database" section
4. Select the database file you exported earlier
5. Click "Import Database (Upload & Restore)"
6. Your data is now restored!


TROUBLESHOOTING
===============

macOS Issues:
-------------
Problem: "App is damaged" or won't open
Solution:
  1. Right-click the app → "Open" (don't double-click)
  2. Or open Terminal and run:
     xattr -cr /path/to/FinanceDashboard.app
     (Replace /path/to/ with actual path, or drag app into Terminal)

Problem: App won't start
Solution: Make sure you're on macOS 10.15 (Catalina) or newer

Problem: Lost my data after update
Solution:
  - Go to Settings → Import Database
  - Select your exported backup file
  - If you didn't export, check Settings → Backup History for local backups


Windows Issues:
---------------
Problem: I need a Windows version
Solution: This build is macOS only. Contact the developer for a Windows build.


DATA SAFETY
===========
- Always export before updates
- Create local backups regularly (Settings → Create Local Backup)
- Local backups are stored inside the app at: data/backups/
- Exported files go to your Downloads folder
- A backup is automatically created before any import or delete operation


FEATURES
========

📊 Dashboard
- Overview of income, expenses, and budget performance
- Visual charts and graphs
- Filter by date, category, and owner

💳 Debt Management
- Track credit cards, loans, and mortgages
- Monitor payment history
- See debt payoff progress

📝 Transactions
- Add, edit, and categorize transactions
- Multi-account support
- Search and filter

💰 Budgets
- Set category budgets
- Track spending vs budget
- Get budget recommendations

📊 Analytics
- Detailed spending analysis
- Interactive charts with Plotly
- Compare time periods

⚙️ Settings
- Export database (before updates)
- Import database (restore from backup)
- Create local backups
- View backup history
- Delete all data (danger zone)


UPDATES
=======
This app does not auto-update. When a new version is available:

1. EXPORT your data first (Settings → Export Database) 🚨
2. You'll receive a new FinanceDashboard.app file
3. Replace the old app with the new one
4. Open the new app
5. IMPORT your data (Settings → Import Database)


PRIVACY & SECURITY
==================
✅ 100% Local - No internet connection required or used
✅ No Account - No login, no registration
✅ Your Data Only - Each installation has its own database
✅ No Tracking - No analytics, no telemetry
✅ Open Source - You can inspect the code


SUPPORT
=======
If you have issues, contact the person who shared this app with you.

Common Questions:
- "Where is my data stored?" → Inside the app at data/personal_finance.db
- "Can I use this on multiple computers?" → Yes, export from one and import to another
- "Is my data safe?" → Yes, it's stored only on your computer
- "Do I need internet?" → No, completely offline
- "How do I backup?" → Settings → Export Database or Create Local Backup


VERSION INFORMATION
===================
Application: Finance Dashboard Desktop
Platform: macOS (Apple Silicon & Intel compatible)
          Windows (requires separate build)
Database: SQLite (included, no setup needed)
Runtime: Standalone (no Python installation required)

Features:
- Transactions tracking
- Budget management
- Debt/credit tracking
- Analytics & charts
- Data export/import
- Automatic backups
- Danger zone (delete all data)


================================
Enjoy managing your finances! 💰
================================

Questions? Contact the person who shared this app with you.
