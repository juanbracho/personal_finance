#!/usr/bin/env python3
"""
Migration script for Phase 3: Debt-as-Account
Run this to add debt_charges and accounts tables
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = 'data/personal_finance.db'

def run_migration():
    """Execute the migration SQL file"""

    print("="*60)
    print("Phase 3: Debt-as-Account Migration")
    print("="*60)

    # Check if database exists
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        return False

    # Backup database first
    backup_path = f"{DB_PATH}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"\n📦 Creating backup: {backup_path}")

    try:
        import shutil
        shutil.copy2(DB_PATH, backup_path)
        print(f"✅ Backup created successfully")
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return False

    # Read SQL file
    sql_file = 'migrations/add_debt_charges.sql'
    print(f"\n📄 Reading SQL file: {sql_file}")

    try:
        with open(sql_file, 'r') as f:
            sql_script = f.read()
    except Exception as e:
        print(f"❌ Failed to read SQL file: {e}")
        return False

    # Execute migration
    print(f"\n🔧 Executing migration...")

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Execute all statements
        cursor.executescript(sql_script)

        conn.commit()

        # Verify tables created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]

        print(f"\n✅ Migration completed successfully!")
        print(f"\n📊 Current tables in database:")
        for table in tables:
            print(f"   - {table}")

        # Check if new tables exist
        if 'debt_charges' in tables and 'accounts' in tables:
            print(f"\n✅ New tables created:")
            print(f"   - debt_charges")
            print(f"   - accounts")

            # Check debt_payments for new column
            cursor.execute("PRAGMA table_info(debt_payments)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'debt_charge_id' in columns:
                print(f"   - debt_payments.debt_charge_id (added)")
        else:
            print(f"\n⚠️ Warning: Some tables may not have been created")

        conn.close()

        print(f"\n{'='*60}")
        print(f"✅ Migration successful!")
        print(f"{'='*60}")
        print(f"\nNext steps:")
        print(f"1. Add your bank/cash accounts to the 'accounts' table")
        print(f"2. Your debt accounts will be linked automatically")
        print(f"3. Restart the Flask app to use new features")
        print(f"\nBackup saved at: {backup_path}")
        print(f"{'='*60}\n")

        return True

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print(f"\nYou can restore from backup: {backup_path}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = run_migration()
    exit(0 if success else 1)
