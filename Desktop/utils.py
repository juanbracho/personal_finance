import os
from datetime import datetime
from sqlalchemy import text, inspect


def local_now():
    """Return the current datetime in the APP_TIMEZONE (set via env var on Railway).
    Falls back to UTC when the var is missing or the timezone name is invalid.
    Returns a naive datetime so it's a drop-in replacement for datetime.now().
    """
    try:
        from zoneinfo import ZoneInfo
        tz_name = os.environ.get('APP_TIMEZONE', 'UTC')
        return datetime.now(tz=ZoneInfo(tz_name)).replace(tzinfo=None)
    except Exception:
        return datetime.now()


def current_user_id():
    """Return the authenticated user's ID from session or Bearer JWT, or None."""
    from flask import session, request, current_app
    uid = session.get('user_id')
    if uid:
        return int(uid)
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        import jwt
        try:
            payload = jwt.decode(
                auth_header[7:],
                current_app.config['JWT_SECRET_KEY'],
                algorithms=['HS256'],
            )
            return payload['user_id']
        except Exception:
            return None
    return None


def uid_clause(uid=None):
    """
    Returns (sql_fragment, params_dict) to scope a query to the current user.
    If user_id is None (dev/auth-bypass mode) returns ('', {}) — no filter.

    Usage:
        uid_sql, uid_p = uid_clause()
        conn.execute(
            text(f"SELECT * FROM transactions WHERE is_active = true {uid_sql}"),
            {**other_params, **uid_p}
        )
    """
    if uid is None:
        uid = current_user_id()
    if uid is None:
        return '', {}
    return 'AND user_id = :_uid', {'_uid': uid}


def get_available_years_and_owners():
    """Get available years and owners for the current user."""
    from models import db
    try:
        uid = current_user_id()
        with db.engine.connect() as conn:
            years_result = conn.execute(text("""
                SELECT DISTINCT EXTRACT(YEAR FROM date)::integer AS year
                FROM transactions
                ORDER BY year DESC
            """))
            available_years = [row[0] for row in years_result if row[0] is not None]

            if uid is not None:
                owners_result = conn.execute(
                    text("SELECT name FROM user_owners WHERE user_id = :uid AND is_active = true ORDER BY name"),
                    {"uid": uid},
                )
            else:
                owners_result = conn.execute(text("""
                    SELECT DISTINCT owner
                    FROM transactions
                    ORDER BY owner
                """))
            available_owners = [row[0] for row in owners_result if row[0] is not None]

        if not available_years:
            current_year = local_now().year
            available_years = [current_year - 1, current_year, current_year + 1]

        if not available_owners:
            available_owners = []

        return available_years, available_owners

    except Exception as e:
        print(f"Error getting years/owners: {e}")
        current_year = datetime.now().year
        return [current_year - 1, current_year, current_year + 1], []


def validate_database_integrity():
    """Validate that the database has all required tables."""
    from models import db
    print("Validating database integrity...")

    try:
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()

        required_tables = [
            'transactions', 'budget_templates', 'unexpected_expenses',
            'monthly_budgets', 'debt_accounts', 'debt_payments'
        ]

        missing_tables = [t for t in required_tables if t not in existing_tables]

        if missing_tables:
            print(f"Missing tables: {missing_tables}")
            return False

        with db.engine.connect() as conn:
            budget_count = conn.execute(
                text("SELECT COUNT(*) FROM budget_templates WHERE is_active = true")
            ).scalar()

        if budget_count == 0:
            print("No active budget templates found — tables present but empty")

        print("Database integrity validated")
        return True

    except Exception as e:
        print(f"Database validation failed: {e}")
        return False


def get_database_stats():
    """Get basic statistics about the database content using SQLAlchemy."""
    from models import db
    try:
        with db.engine.connect() as conn:
            stats = {}

            stats['transactions'] = conn.execute(
                text("SELECT COUNT(*) FROM transactions")
            ).scalar() or 0

            stats['budget_categories'] = conn.execute(
                text("SELECT COUNT(*) FROM budget_templates WHERE is_active = true")
            ).scalar() or 0

            stats['debt_accounts'] = conn.execute(
                text("SELECT COUNT(*) FROM debt_accounts WHERE is_active = true")
            ).scalar() or 0

            date_row = conn.execute(
                text("SELECT MIN(date), MAX(date) FROM transactions")
            ).fetchone()
            stats['date_range'] = {
                'earliest': str(date_row[0]) if date_row and date_row[0] else 'No data',
                'latest': str(date_row[1]) if date_row and date_row[1] else 'No data'
            }

        return stats

    except Exception as e:
        print(f"Error getting database stats: {e}")
        return {
            'transactions': 0,
            'budget_categories': 0,
            'debt_accounts': 0,
            'date_range': {'earliest': 'Error', 'latest': 'Error'}
        }


def ensure_budget_tables(conn=None):
    """
    Legacy compatibility shim — budget tables are created by db.create_all() at startup.
    The `conn` parameter is ignored; kept for call-site compatibility.
    """
    pass
