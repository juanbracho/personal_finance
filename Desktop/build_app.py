#!/usr/bin/env python3
"""
Finance Dashboard - App Builder Script
Run this script to build a new version of the desktop app.

Usage:
    python3 build_app.py           # Build app only
    python3 build_app.py --update  # Build app + create update package
"""

import os
import sys
import subprocess
import shutil
from datetime import datetime
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
DIST_DIR = SCRIPT_DIR / 'dist'
APP_NAME = 'FinanceDashboard.app'
SPEC_FILE = 'build_desktop.spec'

def run_command(cmd, description):
    """Run a command and return success status"""
    print(f"\n{'='*60}")
    print(f"  {description}")
    print(f"{'='*60}")

    result = subprocess.run(cmd, shell=True, cwd=SCRIPT_DIR)
    return result.returncode == 0

def get_version():
    """Read current version from version.json"""
    import json
    version_file = SCRIPT_DIR / 'version.json'
    with open(version_file, 'r') as f:
        data = json.load(f)
    return data.get('version', 'unknown')

def build_app():
    """Build the desktop application"""
    print("\n" + "="*60)
    print("  FINANCE DASHBOARD - APP BUILDER")
    print("="*60)

    version = get_version()
    print(f"\nBuilding version: {version}")
    print(f"Build time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Clean and build
    success = run_command(
        f'pyinstaller --clean -y {SPEC_FILE}',
        'Building application with PyInstaller...'
    )

    if not success:
        print("\n❌ Build FAILED!")
        return False

    # Check output
    app_path = DIST_DIR / APP_NAME
    if app_path.exists():
        print(f"\n✅ Build SUCCESSFUL!")
        print(f"\n📦 App location: {app_path}")
        print(f"\nTo test the app, run:")
        print(f'   open "{app_path}"')
        return True
    else:
        print("\n❌ Build completed but app not found!")
        return False

def build_update_package():
    """Build update package"""
    success = run_command(
        'python3 build_update_package.py',
        'Creating update package...'
    )

    if success:
        version = get_version()
        print(f"\n✅ Update package created!")
        print(f"   Location: updates/FinanceDashboard-Update-v{version}.zip")

    return success

def main():
    os.chdir(SCRIPT_DIR)

    # Parse arguments
    build_update = '--update' in sys.argv

    # Build app
    if not build_app():
        sys.exit(1)

    # Optionally build update package
    if build_update:
        if not build_update_package():
            print("\n⚠️  Update package creation failed")
            sys.exit(1)

    print("\n" + "="*60)
    print("  BUILD COMPLETE!")
    print("="*60)
    print(f"\n📱 Test app: {DIST_DIR / APP_NAME}")
    if build_update:
        print(f"📦 Update package: updates/")
    print()

if __name__ == '__main__':
    main()
