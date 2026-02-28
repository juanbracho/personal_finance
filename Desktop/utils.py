from datetime import datetime
from sqlalchemy import text, inspect


def get_available_years_and_owners():
    """Get available years and owners from transactions using SQLAlchemy."""
    from models import db
    try:
        with db.engine.connect() as conn:
            years_result = conn.execute(text("""
                SELECT DISTINCT EXTRACT(YEAR FROM date)::integer AS year
                FROM transactions
                ORDER BY year DESC
            """))
            available_years = [row[0] for row in years_result if row[0] is not None]

            owners_result = conn.execute(text("""
                SELECT DISTINCT owner
                FROM transactions
                ORDER BY owner
            """))
            available_owners = [row[0] for row in owners_result if row[0] is not None]

        if not available_years:
            current_year = datetime.now().year
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
