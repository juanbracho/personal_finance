#!/usr/bin/env python3
"""
migrate_to_postgres.py
One-time migration: SQLite → PostgreSQL (Neon)

Usage:
    cd Desktop/
    DATABASE_URL=postgresql://... python migrations/migrate_to_postgres.py
    DATABASE_URL=postgresql://... python migrations/migrate_to_postgres.py --dry-run
"""

import os
import sys
import sqlite3
import argparse
from datetime import datetime

from sqlalchemy import text

# ── path bootstrap ────────────────────────────────────────────────────────────
_HERE    = os.path.dirname(os.path.abspath(__file__))
_DESKTOP = os.path.dirname(_HERE)
sys.path.insert(0, _DESKTOP)

SQLITE_PATH = os.path.join(_DESKTOP, 'data', 'personal_finance.db')

# ── helpers ───────────────────────────────────────────────────────────────────

def _bool(val, default=True):
    """Convert SQLite 0/1/None to Python bool."""
    if val is None:
        return default
    return bool(val)


def _float(val):
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        print(f'  ⚠  bad numeric value {val!r} — stored as 0.0')
        return 0.0


def _open_sqlite():
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _make_minimal_app():
    """Minimal Flask app — just SQLAlchemy, no blueprints."""
    from flask import Flask
    from config import Config
    from models import db as _db
    app = Flask(__name__)
    app.config.from_object(Config)
    _db.init_app(app)
    return app, _db


# ── per-table migration functions ─────────────────────────────────────────────

def _migrate_transactions(rows, pg, user_id, dry_run):
    if dry_run:
        return len(rows)
    for r in rows:
        pg.execute(text("""
            INSERT INTO transactions
                (id, user_id, account_name, date, description, amount, sub_category,
                 category, type, owner, is_business, debt_payment_id, is_active,
                 created_at, updated_at)
            VALUES
                (:id, :user_id, :account_name, :date, :description, :amount,
                 :sub_category, :category, :type, :owner, :is_business,
                 :debt_payment_id, :is_active, :created_at, :updated_at)
            ON CONFLICT (id) DO NOTHING
        """), {
            'id':              r['id'],
            'user_id':         user_id,
            'account_name':    r['account_name'],
            'date':            r['date'],
            'description':     r['description'],
            'amount':          _float(r['amount']),
            'sub_category':    r['sub_category'],
            'category':        r['category'],
            'type':            r['type'],
            'owner':           r['owner'],
            'is_business':     _bool(r['is_business'], False),
            'debt_payment_id': r['debt_payment_id'],
            'is_active':       _bool(r['is_active'], True),
            'created_at':      r['created_at'] or datetime.utcnow().isoformat(),
            'updated_at':      r['updated_at'] or datetime.utcnow().isoformat(),
        })
    return len(rows)


def _migrate_budget_templates(rows, pg, user_id, dry_run):
    if dry_run:
        return len(rows)
    for r in rows:
        pg.execute(text("""
            INSERT INTO budget_templates
                (id, user_id, category, budget_amount, notes, is_active,
                 created_at, updated_at)
            VALUES
                (:id, :user_id, :category, :budget_amount, :notes, :is_active,
                 :created_at, :updated_at)
            ON CONFLICT (id) DO NOTHING
        """), {
            'id':            r['id'],
            'user_id':       user_id,
            'category':      r['category'],
            'budget_amount': _float(r['budget_amount']),
            'notes':         r['notes'],
            'is_active':     _bool(r['is_active'], True),
            'created_at':    r['created_at'] or datetime.utcnow().isoformat(),
            'updated_at':    r['updated_at'] or datetime.utcnow().isoformat(),
        })
    return len(rows)


def _migrate_budget_subcategory_templates(rows, pg, user_id, dry_run):
    if dry_run:
        return len(rows)
    for r in rows:
        pg.execute(text("""
            INSERT INTO budget_subcategory_templates
                (id, user_id, category, sub_category, budget_amount, notes,
                 budget_by_category, is_active, created_at, updated_at)
            VALUES
                (:id, :user_id, :category, :sub_category, :budget_amount, :notes,
                 :budget_by_category, :is_active, :created_at, :updated_at)
            ON CONFLICT (id) DO NOTHING
        """), {
            'id':                r['id'],
            'user_id':           user_id,
            'category':          r['category'],
            'sub_category':      r['sub_category'],
            'budget_amount':     _float(r['budget_amount']),
            'notes':             r['notes'],
            'budget_by_category': _bool(r['budget_by_category'], False),
            'is_active':         _bool(r['is_active'], True),
            'created_at':        r['created_at'] or datetime.utcnow().isoformat(),
            'updated_at':        r['updated_at'] or datetime.utcnow().isoformat(),
        })
    return len(rows)


def _migrate_monthly_budgets(rows, pg, user_id, dry_run):
    if dry_run:
        return len(rows)
    for r in rows:
        pg.execute(text("""
            INSERT INTO monthly_budgets
                (id, user_id, category, month, year, budget_amount, notes,
                 created_at, updated_at)
            VALUES
                (:id, :user_id, :category, :month, :year, :budget_amount, :notes,
                 :created_at, :updated_at)
            ON CONFLICT (id) DO NOTHING
        """), {
            'id':            r['id'],
            'user_id':       user_id,
            'category':      r['category'],
            'month':         r['month'],
            'year':          r['year'],
            'budget_amount': _float(r['budget_amount']),
            'notes':         r['notes'],
            'created_at':    r['created_at'] or datetime.utcnow().isoformat(),
            'updated_at':    r['updated_at'] or datetime.utcnow().isoformat(),
        })
    return len(rows)


def _migrate_unexpected_expenses(rows, pg, user_id, dry_run):
    if dry_run:
        return len(rows)
    for r in rows:
        pg.execute(text("""
            INSERT INTO unexpected_expenses
                (id, user_id, category, month, year, amount, description,
                 is_active, created_at, updated_at)
            VALUES
                (:id, :user_id, :category, :month, :year, :amount, :description,
                 :is_active, :created_at, :updated_at)
            ON CONFLICT (id) DO NOTHING
        """), {
            'id':          r['id'],
            'user_id':     user_id,
            'category':    r['category'],
            'month':       r['month'],
            'year':        r['year'],
            'amount':      _float(r['amount']),
            'description': r['description'],
            'is_active':   _bool(r['is_active'], True),
            'created_at':  r['created_at'] or datetime.utcnow().isoformat(),
            'updated_at':  r['updated_at'] or datetime.utcnow().isoformat(),
        })
    return len(rows)


def _migrate_debt_accounts(rows, pg, user_id, dry_run):
    if dry_run:
        return len(rows)
    for r in rows:
        pg.execute(text("""
            INSERT INTO debt_accounts
                (id, user_id, name, debt_type, original_balance, current_balance,
                 interest_rate, minimum_payment, due_date, owner, category,
                 account_number_last4, is_active, created_at, updated_at)
            VALUES
                (:id, :user_id, :name, :debt_type, :original_balance, :current_balance,
                 :interest_rate, :minimum_payment, :due_date, :owner, :category,
                 :account_number_last4, :is_active, :created_at, :updated_at)
            ON CONFLICT (id) DO NOTHING
        """), {
            'id':                   r['id'],
            'user_id':              user_id,
            'name':                 r['name'],
            'debt_type':            r['debt_type'],
            'original_balance':     _float(r['original_balance']),
            'current_balance':      _float(r['current_balance']),
            'interest_rate':        _float(r['interest_rate']),
            'minimum_payment':      _float(r['minimum_payment']),
            'due_date':             r['due_date'],
            'owner':                r['owner'],
            'category':             r['category'],
            'account_number_last4': r['account_number_last4'],
            'is_active':            _bool(r['is_active'], True),
            'created_at':           r['created_at'] or datetime.utcnow().isoformat(),
            'updated_at':           r['updated_at'] or datetime.utcnow().isoformat(),
        })
    return len(rows)


def _migrate_debt_payments(rows, pg, user_id, dry_run):
    if dry_run:
        return len(rows)
    for r in rows:
        pg.execute(text("""
            INSERT INTO debt_payments
                (id, user_id, debt_account_id, debt_charge_id, payment_amount,
                 principal_amount, interest_amount, payment_date,
                 balance_after_payment, payment_type, notes)
            VALUES
                (:id, :user_id, :debt_account_id, :debt_charge_id, :payment_amount,
                 :principal_amount, :interest_amount, :payment_date,
                 :balance_after_payment, :payment_type, :notes)
            ON CONFLICT (id) DO NOTHING
        """), {
            'id':                   r['id'],
            'user_id':              user_id,
            'debt_account_id':      r['debt_account_id'],
            'debt_charge_id':       r['debt_charge_id'],
            'payment_amount':       _float(r['payment_amount']),
            'principal_amount':     _float(r['principal_amount']),
            'interest_amount':      _float(r['interest_amount']),
            'payment_date':         r['payment_date'],
            'balance_after_payment': _float(r['balance_after_payment']),
            'payment_type':         r['payment_type'] or 'Regular',
            'notes':                r['notes'],
        })
    return len(rows)


def _migrate_budget_commitments(rows, pg, user_id, dry_run):
    if dry_run:
        return len(rows)
    for r in rows:
        pg.execute(text("""
            INSERT INTO budget_commitments
                (id, user_id, name, category, sub_category, estimated_amount,
                 due_day_of_month, is_fixed, is_active, created_at, updated_at)
            VALUES
                (:id, :user_id, :name, :category, :sub_category, :estimated_amount,
                 :due_day_of_month, :is_fixed, :is_active, :created_at, :updated_at)
            ON CONFLICT (id) DO NOTHING
        """), {
            'id':               r['id'],
            'user_id':          user_id,
            'name':             r['name'],
            'category':         r['category'],
            'sub_category':     r['sub_category'],
            'estimated_amount': _float(r['estimated_amount']),
            'due_day_of_month': r['due_day_of_month'],
            'is_fixed':         _bool(r['is_fixed'], True),
            'is_active':        _bool(r['is_active'], True),
            'created_at':       r['created_at'] or datetime.utcnow().isoformat(),
            'updated_at':       r['updated_at'] or datetime.utcnow().isoformat(),
        })
    return len(rows)


# ── sequence reset ────────────────────────────────────────────────────────────

_TABLES_WITH_SEQUENCES = [
    'transactions', 'budget_templates', 'budget_subcategory_templates',
    'monthly_budgets', 'unexpected_expenses', 'debt_accounts',
    'debt_payments', 'budget_commitments',
]


def _reset_sequences(pg):
    """Advance PG sequences past the highest migrated id so new inserts don't collide."""
    for table in _TABLES_WITH_SEQUENCES:
        pg.execute(text(f"""
            SELECT setval(
                pg_get_serial_sequence('{table}', 'id'),
                COALESCE((SELECT MAX(id) FROM {table}), 1)
            )
        """))
    print("  ✓ Sequences reset")


# ── main ──────────────────────────────────────────────────────────────────────

TABLES = [
    ('transactions',                _migrate_transactions),
    ('budget_templates',            _migrate_budget_templates),
    ('budget_subcategory_templates', _migrate_budget_subcategory_templates),
    ('monthly_budgets',             _migrate_monthly_budgets),
    ('unexpected_expenses',         _migrate_unexpected_expenses),
    ('debt_accounts',               _migrate_debt_accounts),
    ('debt_payments',               _migrate_debt_payments),
    ('budget_commitments',          _migrate_budget_commitments),
]


def main():
    parser = argparse.ArgumentParser(description='Migrate Finance Dashboard: SQLite → PostgreSQL')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be migrated without writing anything')
    args = parser.parse_args()
    dry_run = args.dry_run

    print('=' * 60)
    print('Finance Dashboard — SQLite → PostgreSQL Migration')
    if dry_run:
        print('DRY RUN — nothing will be written to PostgreSQL')
    print('=' * 60)
    print()

    if not os.path.exists(SQLITE_PATH):
        print(f'ERROR: SQLite database not found: {SQLITE_PATH}')
        sys.exit(1)

    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print('ERROR: DATABASE_URL environment variable not set')
        sys.exit(1)

    app, db = _make_minimal_app()

    with app.app_context():

        # ── Step 1: Schema ────────────────────────────────────────────────────
        print('Step 1: PostgreSQL schema...')
        if not dry_run:
            db.create_all()
            print('  ✓ All tables created / verified')
        else:
            print('  [dry-run] Would call db.create_all()')

        # ── Step 2: Admin user ────────────────────────────────────────────────
        print('\nStep 2: Admin user...')
        user_id = 1
        if not dry_run:
            with db.engine.begin() as pg:
                existing = pg.execute(
                    text("SELECT id FROM users WHERE username = 'suricata'")
                ).fetchone()
                if existing:
                    user_id = existing[0]
                    print(f'  ℹ  User "suricata" already exists (id={user_id}) — skipping')
                else:
                    row = pg.execute(text("""
                        INSERT INTO users (username, role, is_active, created_at)
                        VALUES ('suricata', 'admin', true, NOW())
                        RETURNING id
                    """)).fetchone()
                    user_id = row[0]
                    print(f'  ✓ Admin user "suricata" created (id={user_id})')
        else:
            print('  [dry-run] Would insert user "suricata" (admin)')

        # ── Step 3: Data tables ───────────────────────────────────────────────
        print('\nStep 3: Migrating data tables...')
        sqlite_conn = _open_sqlite()
        counts = {}

        with db.engine.begin() as pg:
            for table_name, fn in TABLES:
                rows = sqlite_conn.execute(
                    f'SELECT * FROM {table_name} ORDER BY id'
                ).fetchall()
                sqlite_n = len(rows)

                n = fn(rows, pg if not dry_run else None, user_id, dry_run)

                if not dry_run:
                    pg_n = pg.execute(text(f'SELECT COUNT(*) FROM {table_name}')).scalar()
                else:
                    pg_n = '—'

                label = f'[dry-run] {sqlite_n}' if dry_run else f'{sqlite_n} → {pg_n}'
                print(f'  {table_name:<35} {label}')
                counts[table_name] = (sqlite_n, pg_n)

        # ── Step 4: User owners ───────────────────────────────────────────────
        print('\nStep 4: User owners...')
        owners = [
            row[0] for row in
            sqlite_conn.execute(
                'SELECT DISTINCT owner FROM transactions WHERE owner IS NOT NULL ORDER BY owner'
            ).fetchall()
        ]
        print(f'  Found: {owners}')

        if not dry_run:
            with db.engine.begin() as pg:
                for name in owners:
                    pg.execute(text("""
                        INSERT INTO user_owners (user_id, name, is_active, created_at)
                        VALUES (:user_id, :name, true, NOW())
                        ON CONFLICT (user_id, name) DO NOTHING
                    """), {'user_id': user_id, 'name': name})
            print(f'  ✓ Inserted {len(owners)} owner(s) for user_id={user_id}')
        else:
            print(f'  [dry-run] Would insert {len(owners)} user_owners')

        sqlite_conn.close()

        # ── Step 5: Category seeds ────────────────────────────────────────────
        print('\nStep 5: Category seeds...')
        from seeds.categories import CATEGORY_SEEDS

        if not dry_run:
            with db.engine.begin() as pg:
                existing = pg.execute(text('SELECT COUNT(*) FROM category_seeds')).scalar()
                if existing > 0:
                    print(f'  ℹ  category_seeds already has {existing} row(s) — skipping')
                else:
                    for seed in CATEGORY_SEEDS:
                        pg.execute(text("""
                            INSERT INTO category_seeds
                                (category, sub_category, budget_amount, is_active)
                            VALUES (:category, :sub_category, :budget_amount, true)
                        """), seed)
                    print(f'  ✓ Inserted {len(CATEGORY_SEEDS)} category seeds')
        else:
            print(f'  [dry-run] Would insert {len(CATEGORY_SEEDS)} category seeds')

        # ── Step 6: Sequence reset ────────────────────────────────────────────
        if not dry_run:
            print('\nStep 6: Resetting sequences...')
            with db.engine.begin() as pg:
                _reset_sequences(pg)

        # ── Summary ───────────────────────────────────────────────────────────
        print()
        print('=' * 62)
        print('MIGRATION SUMMARY')
        print('=' * 62)
        print(f"{'Table':<35} {'SQLite':>8} {'PostgreSQL':>12}  {'OK?':>4}")
        print('-' * 62)
        for table_name, (sc, pc) in counts.items():
            if dry_run:
                ok = '—'
            else:
                ok = '✓' if int(pc) >= sc else '⚠'
            print(f'{table_name:<35} {sc:>8} {str(pc):>12}  {ok:>4}')
        print('=' * 62)

        if dry_run:
            print('\nDry run complete. Run without --dry-run to execute.')
        else:
            print('\nMigration complete!')
            print('Next: start Flask with DATABASE_URL set and smoke-test all pages.')


if __name__ == '__main__':
    main()
