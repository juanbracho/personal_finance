#!/usr/bin/env python3
"""
Build Update Package Script
Creates a distributable update package for the Finance Dashboard app.
"""

import os
import json
import shutil
import hashlib
import zipfile
from datetime import datetime

# Files and folders to include in the update package
INCLUDE_PATTERNS = [
    'app.py',
    'config.py',
    'models.py',
    'utils.py',
    'budget_recommender.py',
    'version.json',
    'blueprints/',
    'templates/',
    'static/',
]

# Files and folders to NEVER include
EXCLUDE_PATTERNS = [
    'data/',  # NEVER include user data
    'venv/',
    '__pycache__/',
    '.pyc',
    '.DS_Store',
    'build/',
    'dist/',
    'build_update_package.py',  # Don't include this script
    'update_executor.sh',  # Don't include the executor in the package
]

def get_version():
    """Read version from version.json"""
    with open('version.json', 'r') as f:
        return json.load(f)

def calculate_checksum(filepath):
    """Calculate SHA256 checksum of a file"""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def should_include(path, root_path):
    """Check if a file should be included in the package"""
    relative_path = os.path.relpath(path, root_path)

    # Check exclude patterns
    for exclude in EXCLUDE_PATTERNS:
        if exclude in relative_path or relative_path.startswith(exclude):
            return False

    return True

def copy_files_to_temp(temp_dir):
    """Copy necessary files to temporary directory"""
    print("\nCopying files to temporary directory...")

    root_dir = os.getcwd()
    app_bundle_dir = os.path.join(temp_dir, 'app_bundle')
    os.makedirs(app_bundle_dir, exist_ok=True)

    files_copied = 0

    for pattern in INCLUDE_PATTERNS:
        source_path = os.path.join(root_dir, pattern)

        if not os.path.exists(source_path):
            print(f"  ⚠️  Warning: {pattern} not found, skipping...")
            continue

        if os.path.isfile(source_path):
            # Copy single file
            dest_path = os.path.join(app_bundle_dir, pattern)
            shutil.copy2(source_path, dest_path)
            print(f"  ✓ Copied: {pattern}")
            files_copied += 1

        elif os.path.isdir(source_path):
            # Copy entire directory
            dest_path = os.path.join(app_bundle_dir, pattern)

            # Walk through directory and copy files that pass the filter
            for dirpath, dirnames, filenames in os.walk(source_path):
                # Filter out excluded directories
                dirnames[:] = [d for d in dirnames if should_include(os.path.join(dirpath, d), root_dir)]

                for filename in filenames:
                    src_file = os.path.join(dirpath, filename)
                    if should_include(src_file, root_dir):
                        # Calculate relative path
                        rel_path = os.path.relpath(src_file, source_path)
                        dest_file = os.path.join(dest_path, rel_path)

                        # Create directory if needed
                        os.makedirs(os.path.dirname(dest_file), exist_ok=True)

                        # Copy file
                        shutil.copy2(src_file, dest_file)
                        files_copied += 1

            print(f"  ✓ Copied directory: {pattern}")

    print(f"\n  Total files copied: {files_copied}")
    return app_bundle_dir

def create_manifest(version_info, zip_checksum):
    """Create manifest file with version and checksum info"""
    manifest = {
        'version': version_info['version'],
        'build_date': version_info['build_date'],
        'build_number': version_info['build_number'],
        'min_db_version': version_info.get('min_db_version', '1.0.0'),
        'package_checksum': zip_checksum,
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    return manifest

def create_zip_package(temp_dir, version):
    """Create ZIP file from temporary directory"""
    zip_filename = f'FinanceDashboard-Update-v{version}.zip'

    print(f"\nCreating ZIP package: {zip_filename}")

    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        app_bundle_dir = os.path.join(temp_dir, 'app_bundle')

        for root, dirs, files in os.walk(app_bundle_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, temp_dir)
                zipf.write(file_path, arcname)
                print(f"  Added: {arcname}")

    return zip_filename

def main():
    """Main build process"""
    print("=" * 60)
    print("Finance Dashboard - Update Package Builder")
    print("=" * 60)

    # Check if we're in the right directory
    if not os.path.exists('version.json'):
        print("\n❌ Error: version.json not found!")
        print("   Make sure you're running this from the Desktop/ directory")
        return

    # Get version info
    version_info = get_version()
    version = version_info['version']

    print(f"\nBuilding update package for version: v{version}")
    print(f"Build date: {version_info['build_date']}")
    print(f"Build number: {version_info['build_number']}")

    # Create temporary directory
    temp_dir = os.path.join(os.getcwd(), 'temp_update_build')
    if os.path.exists(temp_dir):
        print("\nCleaning up old temporary files...")
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

    try:
        # Copy files to temp directory
        app_bundle_dir = copy_files_to_temp(temp_dir)

        # Create ZIP package
        zip_filename = create_zip_package(temp_dir, version)

        # Calculate checksum of ZIP file
        print("\nCalculating package checksum...")
        zip_checksum = calculate_checksum(zip_filename)
        print(f"  SHA256: {zip_checksum}")

        # Create manifest file
        manifest = create_manifest(version_info, zip_checksum)
        manifest_filename = f'FinanceDashboard-Update-v{version}-manifest.json'

        with open(manifest_filename, 'w') as f:
            json.dump(manifest, f, indent=2)

        print(f"\nCreated manifest: {manifest_filename}")

        # Get file size
        zip_size = os.path.getsize(zip_filename) / (1024 * 1024)  # Convert to MB

        print("\n" + "=" * 60)
        print("✅ Update package created successfully!")
        print("=" * 60)
        print(f"\nPackage: {zip_filename}")
        print(f"Size: {zip_size:.2f} MB")
        print(f"Checksum: {zip_checksum}")
        print(f"Manifest: {manifest_filename}")
        print("\n📦 Distribution Instructions:")
        print(f"   1. Send {zip_filename} to users")
        print(f"   2. Keep {manifest_filename} for your records")
        print(f"   3. Users can install via Settings > Install Update")
        print("=" * 60)

    finally:
        # Clean up temporary directory
        print("\nCleaning up temporary files...")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        print("✓ Cleanup complete")

if __name__ == '__main__':
    main()
