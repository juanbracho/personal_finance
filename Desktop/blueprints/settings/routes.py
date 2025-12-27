from flask import Blueprint, render_template, send_file, request, flash, redirect, url_for, jsonify
import os
import sys
import shutil
import zipfile
import json
import hashlib
import tempfile
import subprocess
from datetime import datetime
from werkzeug.utils import secure_filename
from config import get_app_version

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

# Database file path
DB_PATH = 'data/personal_finance.db'
BACKUP_FOLDER = 'data/backups'

# Ensure backup folder exists
os.makedirs(BACKUP_FOLDER, exist_ok=True)

@settings_bp.route('/')
def index():
    """Settings page with backup/restore options"""

    # Get database file info
    db_exists = os.path.exists(DB_PATH)
    db_size = 0
    db_modified = None

    if db_exists:
        db_size = os.path.getsize(DB_PATH)
        db_modified = datetime.fromtimestamp(os.path.getmtime(DB_PATH))

    # Get list of existing backups
    backups = []
    if os.path.exists(BACKUP_FOLDER):
        for filename in os.listdir(BACKUP_FOLDER):
            if filename.endswith('.db'):
                backup_path = os.path.join(BACKUP_FOLDER, filename)
                backups.append({
                    'filename': filename,
                    'size': os.path.getsize(backup_path),
                    'created': datetime.fromtimestamp(os.path.getctime(backup_path))
                })
        backups.sort(key=lambda x: x['created'], reverse=True)

    # Get app version info
    version_info = get_app_version()

    return render_template('settings.html',
                         db_exists=db_exists,
                         db_size=db_size,
                         db_modified=db_modified,
                         backups=backups,
                         version=version_info['version'],
                         build_date=version_info['build_date'],
                         build_number=version_info['build_number'])

@settings_bp.route('/download-database')
def download_database():
    """Download current database as backup"""

    if not os.path.exists(DB_PATH):
        flash('Database file not found!', 'error')
        return redirect(url_for('settings.index'))

    try:
        # Create filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        download_name = f'finance_dashboard_backup_{timestamp}.db'

        return send_file(
            DB_PATH,
            as_attachment=True,
            download_name=download_name,
            mimetype='application/octet-stream'
        )
    except Exception as e:
        flash(f'Error downloading database: {str(e)}', 'error')
        return redirect(url_for('settings.index'))

@settings_bp.route('/create-backup', methods=['POST'])
def create_backup():
    """Create a backup of the current database in the backups folder"""

    if not os.path.exists(DB_PATH):
        flash('Database file not found!', 'error')
        return redirect(url_for('settings.index'))

    try:
        # Create backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'backup_{timestamp}.db'
        backup_path = os.path.join(BACKUP_FOLDER, backup_filename)

        # Copy database to backup folder
        shutil.copy2(DB_PATH, backup_path)

        flash(f'Backup created successfully: {backup_filename}', 'success')
    except Exception as e:
        flash(f'Error creating backup: {str(e)}', 'error')

    return redirect(url_for('settings.index'))

@settings_bp.route('/restore-backup/<filename>', methods=['POST'])
def restore_backup(filename):
    """Restore database from a backup file"""

    # Secure the filename
    filename = secure_filename(filename)
    backup_path = os.path.join(BACKUP_FOLDER, filename)

    if not os.path.exists(backup_path):
        flash('Backup file not found!', 'error')
        return redirect(url_for('settings.index'))

    try:
        # Create a backup of current database before restoring
        if os.path.exists(DB_PATH):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            pre_restore_backup = os.path.join(BACKUP_FOLDER, f'pre_restore_{timestamp}.db')
            shutil.copy2(DB_PATH, pre_restore_backup)

        # Restore the backup
        shutil.copy2(backup_path, DB_PATH)

        flash(f'Database restored successfully from {filename}', 'success')
        flash('A backup of your previous database was saved before restoring.', 'info')
    except Exception as e:
        flash(f'Error restoring backup: {str(e)}', 'error')

    return redirect(url_for('settings.index'))

@settings_bp.route('/upload-database', methods=['POST'])
def upload_database():
    """Upload and restore database from file"""

    if 'database_file' not in request.files:
        flash('No file selected!', 'error')
        return redirect(url_for('settings.index'))

    file = request.files['database_file']

    if file.filename == '':
        flash('No file selected!', 'error')
        return redirect(url_for('settings.index'))

    if not file.filename.endswith('.db'):
        flash('Invalid file type! Please upload a .db file.', 'error')
        return redirect(url_for('settings.index'))

    try:
        # Create a backup of current database before uploading new one
        if os.path.exists(DB_PATH):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            pre_upload_backup = os.path.join(BACKUP_FOLDER, f'pre_upload_{timestamp}.db')
            shutil.copy2(DB_PATH, pre_upload_backup)

        # Save uploaded file as the new database
        file.save(DB_PATH)

        flash('Database uploaded and restored successfully!', 'success')
        flash('A backup of your previous database was saved before uploading.', 'info')
    except Exception as e:
        flash(f'Error uploading database: {str(e)}', 'error')

    return redirect(url_for('settings.index'))

@settings_bp.route('/delete-backup/<filename>', methods=['POST'])
def delete_backup(filename):
    """Delete a backup file"""

    filename = secure_filename(filename)
    backup_path = os.path.join(BACKUP_FOLDER, filename)

    if not os.path.exists(backup_path):
        flash('Backup file not found!', 'error')
        return redirect(url_for('settings.index'))

    try:
        os.remove(backup_path)
        flash(f'Backup {filename} deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting backup: {str(e)}', 'error')

    return redirect(url_for('settings.index'))

@settings_bp.route('/delete-all-data', methods=['POST'])
def delete_all_data():
    """Delete all data from the database - DANGER ZONE"""

    # Verify confirmation
    confirmation = request.form.get('confirmation', '')
    if confirmation != 'DELETE ALL DATA':
        flash('Incorrect confirmation text. Data was NOT deleted.', 'error')
        return redirect(url_for('settings.index'))

    if not os.path.exists(DB_PATH):
        flash('No database found to delete.', 'warning')
        return redirect(url_for('settings.index'))

    try:
        # Create a backup before deleting
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pre_delete_backup = os.path.join(BACKUP_FOLDER, f'pre_delete_{timestamp}.db')
        shutil.copy2(DB_PATH, pre_delete_backup)

        # Delete the database file
        os.remove(DB_PATH)

        flash('All data has been deleted successfully!', 'warning')
        flash(f'A backup was saved before deletion: pre_delete_{timestamp}.db', 'info')
        flash('The app will create a fresh database on next use.', 'info')
    except Exception as e:
        flash(f'Error deleting data: {str(e)}', 'error')

    return redirect(url_for('settings.index'))

# ==================== UPDATE SYSTEM ====================

def compare_versions(current, new):
    """Compare version strings (format: major.minor.patch)"""
    try:
        current_parts = [int(x) for x in current.split('.')]
        new_parts = [int(x) for x in new.split('.')]

        # Pad to same length
        while len(current_parts) < len(new_parts):
            current_parts.append(0)
        while len(new_parts) < len(current_parts):
            new_parts.append(0)

        # Compare each part
        for i in range(len(current_parts)):
            if new_parts[i] > current_parts[i]:
                return 1  # New is newer
            elif new_parts[i] < current_parts[i]:
                return -1  # New is older

        return 0  # Same version
    except Exception as e:
        print(f"Version comparison error: {e}")
        return 0

def calculate_file_checksum(filepath):
    """Calculate SHA256 checksum of a file"""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

@settings_bp.route('/install-update', methods=['POST'])
def install_update():
    """Handle update package upload and installation"""

    try:
        # Check if file was uploaded
        if 'update_file' not in request.files:
            return jsonify({'success': False, 'message': 'No file uploaded'}), 400

        file = request.files['update_file']

        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400

        if not file.filename.endswith('.zip'):
            return jsonify({'success': False, 'message': 'Invalid file type. Must be a .zip file'}), 400

        # Save uploaded file to temporary location
        temp_upload_dir = tempfile.mkdtemp(prefix='finance_update_')
        upload_path = os.path.join(temp_upload_dir, 'update.zip')
        file.save(upload_path)

        print(f"\n{'='*60}")
        print("UPDATE INSTALLATION STARTED")
        print(f"{'='*60}")
        print(f"Upload saved to: {upload_path}")

        # Validate ZIP file
        if not zipfile.is_zipfile(upload_path):
            shutil.rmtree(temp_upload_dir)
            return jsonify({'success': False, 'message': 'Invalid ZIP file'}), 400

        print("✓ ZIP file validated")

        # Extract ZIP to temporary directory
        extract_dir = os.path.join(temp_upload_dir, 'extracted')
        os.makedirs(extract_dir, exist_ok=True)

        with zipfile.ZipFile(upload_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

        print(f"✓ Extracted to: {extract_dir}")

        # Look for app_bundle directory
        app_bundle_path = os.path.join(extract_dir, 'app_bundle')
        if not os.path.exists(app_bundle_path):
            shutil.rmtree(temp_upload_dir)
            return jsonify({'success': False, 'message': 'Invalid update package structure (missing app_bundle)'}), 400

        print("✓ Found app_bundle directory")

        # Validate version.json exists in update
        update_version_path = os.path.join(app_bundle_path, 'version.json')
        if not os.path.exists(update_version_path):
            shutil.rmtree(temp_upload_dir)
            return jsonify({'success': False, 'message': 'Invalid update package (missing version.json)'}), 400

        # Read new version info
        with open(update_version_path, 'r') as f:
            new_version_info = json.load(f)

        new_version = new_version_info.get('version', 'unknown')
        print(f"✓ Update version: {new_version}")

        # Get current version
        current_version_info = get_app_version()
        current_version = current_version_info.get('version', '1.0.0')
        print(f"  Current version: {current_version}")

        # Compare versions
        version_comparison = compare_versions(current_version, new_version)

        if version_comparison == 0:
            shutil.rmtree(temp_upload_dir)
            return jsonify({
                'success': False,
                'message': f'Update package is the same version as current ({current_version})'
            }), 400

        if version_comparison > 0:
            shutil.rmtree(temp_upload_dir)
            return jsonify({
                'success': False,
                'message': f'Update package version ({new_version}) is older than current version ({current_version})'
            }), 400

        print(f"✓ Version check passed: {current_version} -> {new_version}")

        # Validate required files exist in update
        required_files = ['app.py', 'config.py', 'blueprints', 'templates', 'static']
        missing_files = []

        for required in required_files:
            check_path = os.path.join(app_bundle_path, required)
            if not os.path.exists(check_path):
                missing_files.append(required)

        if missing_files:
            shutil.rmtree(temp_upload_dir)
            return jsonify({
                'success': False,
                'message': f'Update package missing required files: {", ".join(missing_files)}'
            }), 400

        print("✓ All required files present")

        # Create backup of current application
        current_app_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        backup_dir = tempfile.mkdtemp(prefix='finance_backup_')
        backup_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        print(f"\n{'='*60}")
        print("CREATING BACKUP")
        print(f"{'='*60}")
        print(f"Current app directory: {current_app_dir}")
        print(f"Backup directory: {backup_dir}")

        # Create database backup first (extra safety)
        if os.path.exists(DB_PATH):
            db_backup_path = os.path.join(BACKUP_FOLDER, f'pre_update_{backup_timestamp}.db')
            shutil.copy2(DB_PATH, db_backup_path)
            print(f"✓ Database backed up to: {db_backup_path}")

        print(f"\n{'='*60}")
        print("UPDATE READY TO INSTALL")
        print(f"{'='*60}")
        print(f"Update package validated successfully")
        print(f"Version: {current_version} -> {new_version}")
        print(f"Extracted files: {app_bundle_path}")

        # Determine app paths
        current_app_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        executor_script = os.path.join(current_app_dir, 'update_executor.sh')

        # Check if we're running from a .app bundle or development
        app_executable = None
        if sys.platform == 'darwin':  # macOS
            # Try to find the .app bundle
            app_parts = current_app_dir.split('/')
            for i in range(len(app_parts) - 1, -1, -1):
                if app_parts[i].endswith('.app'):
                    app_path = '/'.join(app_parts[:i+1])
                    app_executable = app_path
                    break

        if not app_executable:
            # Development mode - just use the current directory
            app_executable = current_app_dir

        print(f"\n{'='*60}")
        print("TRIGGERING UPDATE EXECUTOR")
        print(f"{'='*60}")
        print(f"Executor script: {executor_script}")
        print(f"Update source: {app_bundle_path}")
        print(f"Target app: {current_app_dir}")
        print(f"App executable: {app_executable}")

        # Check if executor script exists
        if not os.path.exists(executor_script):
            print(f"⚠️  Executor script not found at: {executor_script}")
            print("   Update validated but cannot auto-install")
            return jsonify({
                'success': True,
                'message': f'Update to version {new_version} validated (manual installation required)',
                'current_version': current_version,
                'new_version': new_version,
                'restarting': False
            }), 200

        # Launch update executor in background
        try:
            # Make executor script executable (just in case)
            os.chmod(executor_script, 0o755)

            # Launch the executor script
            # Format: update_executor.sh <update_source> <target_app> <app_executable>
            subprocess.Popen(
                [executor_script, app_bundle_path, current_app_dir, app_executable],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True  # Detach from parent process
            )

            print("✓ Update executor launched successfully")
            print("✓ App will now shut down and update")

            # Schedule Flask shutdown after response is sent
            def shutdown_flask():
                import time
                time.sleep(1)  # Wait for response to be sent
                print("\n{'='*60}")
                print("SHUTTING DOWN FOR UPDATE")
                print("{'='*60}")
                os._exit(0)  # Force exit

            # Start shutdown in background thread
            import threading
            shutdown_thread = threading.Thread(target=shutdown_flask)
            shutdown_thread.daemon = True
            shutdown_thread.start()

            return jsonify({
                'success': True,
                'message': f'Update to version {new_version} installed successfully! App is restarting...',
                'current_version': current_version,
                'new_version': new_version,
                'restarting': True
            }), 200

        except Exception as executor_error:
            print(f"❌ Failed to launch executor: {str(executor_error)}")
            return jsonify({
                'success': False,
                'message': f'Failed to launch update executor: {str(executor_error)}'
            }), 500

    except Exception as e:
        print(f"\n❌ UPDATE FAILED: {str(e)}")
        import traceback
        traceback.print_exc()

        # Clean up
        if 'temp_upload_dir' in locals() and os.path.exists(temp_upload_dir):
            shutil.rmtree(temp_upload_dir)

        return jsonify({
            'success': False,
            'message': f'Update failed: {str(e)}'
        }), 500
