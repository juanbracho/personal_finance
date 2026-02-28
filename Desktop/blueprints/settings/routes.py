from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, Response
import os
import sys
import shutil
import zipfile
import json
import tempfile
import subprocess
from datetime import datetime
from config import get_app_version
from models import db
from sqlalchemy import text

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')


@settings_bp.route('/')
def index():
    """Settings page"""
    version_info = get_app_version()
    return render_template('settings.html',
                         db_exists=True,
                         db_size=None,
                         db_modified=None,
                         backups=[],
                         version=version_info['version'],
                         build_date=version_info['build_date'],
                         build_number=version_info['build_number'])


@settings_bp.route('/download-database')
def download_database():
    """Export all data as JSON"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        data = {}
        tables = [
            'transactions', 'budget_templates', 'budget_subcategory_templates',
            'monthly_budgets', 'unexpected_expenses', 'debt_accounts',
            'debt_payments', 'budget_commitments'
        ]
        with db.engine.connect() as conn:
            for table in tables:
                try:
                    rows = conn.execute(text(f"SELECT * FROM {table}")).mappings().all()
                    data[table] = [dict(row) for row in rows]
                except Exception:
                    data[table] = []

        def _serial(obj):
            if hasattr(obj, 'isoformat'):
                return obj.isoformat()
            return str(obj)

        json_str = json.dumps(data, default=_serial, indent=2)
        return Response(
            json_str,
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment;filename=finance_export_{timestamp}.json'}
        )
    except Exception as e:
        flash(f'Error exporting data: {str(e)}', 'error')
        return redirect(url_for('settings.index'))


@settings_bp.route('/upload-database', methods=['POST'])
def upload_database():
    """Database import — deferred to Phase 4."""
    flash('Database import is not yet available. Coming in a future release.', 'info')
    return redirect(url_for('settings.index'))


@settings_bp.route('/delete-all-data', methods=['POST'])
def delete_all_data():
    """Delete all data from the database — DANGER ZONE"""
    confirmation = request.form.get('confirmation', '')
    if confirmation != 'DELETE ALL DATA':
        flash('Incorrect confirmation text. Data was NOT deleted.', 'error')
        return redirect(url_for('settings.index'))

    try:
        # Delete in FK-safe order
        tables = [
            'debt_payments', 'debt_accounts', 'budget_commitments',
            'budget_subcategory_templates', 'monthly_budgets', 'unexpected_expenses',
            'budget_templates', 'transactions'
        ]
        with db.engine.begin() as conn:
            for table in tables:
                conn.execute(text(f"DELETE FROM {table}"))

        flash('All data has been deleted successfully!', 'warning')
        flash('The database schema is preserved — you can start adding data again.', 'info')
    except Exception as e:
        flash(f'Error deleting data: {str(e)}', 'error')

    return redirect(url_for('settings.index'))


# ==================== UPDATE SYSTEM ====================

def compare_versions(current, new):
    """Compare version strings (format: major.minor.patch)"""
    try:
        current_parts = [int(x) for x in current.split('.')]
        new_parts = [int(x) for x in new.split('.')]
        while len(current_parts) < len(new_parts):
            current_parts.append(0)
        while len(new_parts) < len(current_parts):
            new_parts.append(0)
        for i in range(len(current_parts)):
            if new_parts[i] > current_parts[i]:
                return 1
            elif new_parts[i] < current_parts[i]:
                return -1
        return 0
    except Exception as e:
        print(f"Version comparison error: {e}")
        return 0


def log_update(message):
    """Log update messages to file for debugging"""
    log_path = os.path.join('data', 'update_log.txt')
    os.makedirs('data', exist_ok=True)
    with open(log_path, 'a') as f:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        f.write(f"[{timestamp}] {message}\n")


@settings_bp.route('/install-update', methods=['POST'])
def install_update():
    """Handle update package upload and installation"""
    log_update("=" * 50)
    log_update("UPDATE INSTALLATION STARTED")

    try:
        if 'update_file' not in request.files:
            log_update("ERROR: No file in request.files")
            return jsonify({'success': False, 'message': 'No file uploaded'}), 400

        file = request.files['update_file']
        log_update(f"File received: {file.filename}")

        if file.filename == '':
            log_update("ERROR: Empty filename")
            return jsonify({'success': False, 'message': 'No file selected'}), 400

        if not file.filename.endswith('.zip'):
            log_update(f"ERROR: Invalid file type: {file.filename}")
            return jsonify({'success': False, 'message': 'Invalid file type. Must be a .zip file'}), 400

        temp_upload_dir = tempfile.mkdtemp(prefix='finance_update_')
        upload_path = os.path.join(temp_upload_dir, 'update.zip')
        file.save(upload_path)

        print(f"\n{'='*60}")
        print("UPDATE INSTALLATION STARTED")
        print(f"{'='*60}")
        print(f"Upload saved to: {upload_path}")

        if not zipfile.is_zipfile(upload_path):
            shutil.rmtree(temp_upload_dir)
            return jsonify({'success': False, 'message': 'Invalid ZIP file'}), 400

        print("✓ ZIP file validated")

        extract_dir = os.path.join(temp_upload_dir, 'extracted')
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(upload_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        print(f"✓ Extracted to: {extract_dir}")

        app_bundle_path = os.path.join(extract_dir, 'app_bundle')
        if not os.path.exists(app_bundle_path):
            shutil.rmtree(temp_upload_dir)
            return jsonify({'success': False, 'message': 'Invalid update package structure (missing app_bundle)'}), 400

        update_version_path = os.path.join(app_bundle_path, 'version.json')
        if not os.path.exists(update_version_path):
            shutil.rmtree(temp_upload_dir)
            return jsonify({'success': False, 'message': 'Invalid update package (missing version.json)'}), 400

        with open(update_version_path, 'r') as f:
            new_version_info = json.load(f)

        new_version = new_version_info.get('version', 'unknown')
        log_update(f"Update version: {new_version}")
        print(f"✓ Update version: {new_version}")

        current_version_info = get_app_version()
        current_version = current_version_info.get('version', '1.0.0')
        log_update(f"Current version: {current_version}")
        print(f"  Current version: {current_version}")

        version_comparison = compare_versions(current_version, new_version)
        if version_comparison == 0:
            shutil.rmtree(temp_upload_dir)
            return jsonify({
                'success': False,
                'message': f'Update package is the same version as current ({current_version})'
            }), 400

        if version_comparison < 0:
            shutil.rmtree(temp_upload_dir)
            return jsonify({
                'success': False,
                'message': f'Update package version ({new_version}) is older than current version ({current_version})'
            }), 400

        print(f"✓ Version check passed: {current_version} -> {new_version}")

        required_files = ['app.py', 'config.py', 'blueprints', 'templates', 'static']
        missing_files = [r for r in required_files if not os.path.exists(os.path.join(app_bundle_path, r))]
        if missing_files:
            shutil.rmtree(temp_upload_dir)
            return jsonify({
                'success': False,
                'message': f'Update package missing required files: {", ".join(missing_files)}'
            }), 400

        print("✓ All required files present")

        current_app_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        executor_script = os.path.join(current_app_dir, 'update_executor.sh')

        app_executable = current_app_dir
        if sys.platform == 'darwin':
            app_parts = current_app_dir.split('/')
            for i in range(len(app_parts) - 1, -1, -1):
                if app_parts[i].endswith('.app'):
                    app_executable = '/'.join(app_parts[:i+1])
                    break

        if not os.path.exists(executor_script):
            print(f"⚠️  Executor script not found at: {executor_script}")
            return jsonify({
                'success': True,
                'message': f'Update to version {new_version} validated (manual installation required)',
                'current_version': current_version,
                'new_version': new_version,
                'restarting': False
            }), 200

        try:
            os.chmod(executor_script, 0o755)
            subprocess.Popen(
                [executor_script, app_bundle_path, current_app_dir, app_executable],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True
            )
            print("✓ Update executor launched successfully")

            def shutdown_flask():
                import time
                time.sleep(1)
                os._exit(0)

            import threading
            threading.Thread(target=shutdown_flask, daemon=True).start()

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
        if 'temp_upload_dir' in locals() and os.path.exists(temp_upload_dir):
            shutil.rmtree(temp_upload_dir)
        return jsonify({
            'success': False,
            'message': f'Update failed: {str(e)}'
        }), 500
