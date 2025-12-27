#!/bin/bash
################################################################################
# Finance Dashboard - Update Executor Script
# This script handles the actual file replacement during app updates
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored messages
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required arguments are provided
if [ "$#" -ne 3 ]; then
    log_error "Usage: $0 <update_source_path> <target_app_path> <app_executable>"
    exit 1
fi

UPDATE_SOURCE="$1"
TARGET_APP="$2"
APP_EXECUTABLE="$3"

log_info "==============================================="
log_info "Finance Dashboard Update Executor"
log_info "==============================================="
log_info "Update Source: $UPDATE_SOURCE"
log_info "Target App: $TARGET_APP"
log_info "Executable: $APP_EXECUTABLE"
log_info ""

# Verify paths exist
if [ ! -d "$UPDATE_SOURCE" ]; then
    log_error "Update source directory not found: $UPDATE_SOURCE"
    exit 1
fi

if [ ! -d "$TARGET_APP" ]; then
    log_error "Target app directory not found: $TARGET_APP"
    exit 1
fi

# Wait for app to quit
log_info "Waiting for app to quit..."
sleep 3

# Create backup directory
BACKUP_DIR="/tmp/finance_dashboard_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
log_info "Created backup directory: $BACKUP_DIR"

# Backup current application files (excluding data)
log_info "Backing up current application..."
rsync -av \
    --exclude='data/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.DS_Store' \
    "$TARGET_APP/" "$BACKUP_DIR/" > /dev/null 2>&1

log_success "Backup completed"

# Replace files with update (excluding data directory)
log_info "Installing update files..."

# Copy new files, preserving data directory
rsync -av \
    --exclude='data/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.DS_Store' \
    --delete \
    "$UPDATE_SOURCE/" "$TARGET_APP/"

if [ $? -eq 0 ]; then
    log_success "Update files installed successfully"
else
    log_error "Failed to install update files"
    log_warning "Attempting to restore from backup..."

    # Restore from backup
    rsync -av --delete "$BACKUP_DIR/" "$TARGET_APP/"

    if [ $? -eq 0 ]; then
        log_success "Restored from backup"
    else
        log_error "Failed to restore from backup - manual intervention required"
        exit 1
    fi

    exit 1
fi

# Verify critical files exist after update
log_info "Verifying installation..."

CRITICAL_FILES=("app.py" "config.py" "version.json")
CRITICAL_DIRS=("blueprints" "templates" "static" "data")

ALL_OK=true

for file in "${CRITICAL_FILES[@]}"; do
    if [ ! -f "$TARGET_APP/$file" ]; then
        log_error "Critical file missing: $file"
        ALL_OK=false
    fi
done

for dir in "${CRITICAL_DIRS[@]}"; do
    if [ ! -d "$TARGET_APP/$dir" ]; then
        log_error "Critical directory missing: $dir"
        ALL_OK=false
    fi
done

if [ "$ALL_OK" = false ]; then
    log_error "Installation verification failed!"
    log_warning "Restoring from backup..."

    # Restore from backup
    rsync -av --exclude='data/' --delete "$BACKUP_DIR/" "$TARGET_APP/"

    log_error "Update failed - app restored to previous version"
    exit 1
fi

log_success "Installation verified"

# Read new version
if [ -f "$TARGET_APP/version.json" ]; then
    NEW_VERSION=$(python3 -c "import json; print(json.load(open('$TARGET_APP/version.json'))['version'])" 2>/dev/null || echo "unknown")
    log_success "Updated to version: $NEW_VERSION"
fi

# Clean up update source directory
log_info "Cleaning up temporary files..."
if [ -d "$UPDATE_SOURCE" ]; then
    rm -rf "$UPDATE_SOURCE"
fi

# Keep backup for 7 days (optional cleanup in the future)
log_info "Backup saved to: $BACKUP_DIR"
log_info "(Backup will be kept for manual rollback if needed)"

log_info ""
log_success "==============================================="
log_success "Update completed successfully!"
log_success "==============================================="
log_info ""
log_info "Relaunching application..."

# Relaunch the app
if [ -f "$APP_EXECUTABLE" ]; then
    open "$APP_EXECUTABLE" &
    log_success "Application relaunched"
else
    log_warning "Could not find executable: $APP_EXECUTABLE"
    log_info "Please manually restart the application"
fi

log_info "Update executor finished"
exit 0
