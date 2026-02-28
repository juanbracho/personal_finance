"""
One-time migration: set suricata's hashed password in the database.

Usage (run from the Desktop/ directory):
    python migrations/set_initial_password.py

DATABASE_URL is read from Desktop/.env automatically.
You can also override it on the command line:
    DATABASE_URL=postgresql://... python migrations/set_initial_password.py
"""

import os
import sys
import getpass

# ── path bootstrap ─────────────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_DESKTOP = os.path.dirname(_HERE)
sys.path.insert(0, _DESKTOP)


# ── load .env from Desktop/ (same as Flask dev server does) ───────────────────
def _load_dotenv(path):
    """Minimal .env loader — no extra dependencies needed."""
    if not os.path.isfile(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, _, value = line.partition('=')
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            # Only set if not already in environment (env var takes precedence)
            if key and key not in os.environ:
                os.environ[key] = value


_load_dotenv(os.path.join(_DESKTOP, '.env'))


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL is not set.")
        print(f"  Looked for Desktop/.env at: {os.path.join(_DESKTOP, '.env')}")
        print("  Or set it inline: DATABASE_URL=postgresql://... python migrations/set_initial_password.py")
        sys.exit(1)

    if not database_url.startswith(('postgresql', 'postgres')):
        print(f"WARNING: DATABASE_URL does not look like a PostgreSQL URL: {database_url[:40]}...")
        print("  This script is meant for the Neon PostgreSQL database.")
        confirm = input("Continue anyway? [y/N] ").strip().lower()
        if confirm != 'y':
            sys.exit(0)

    password = getpass.getpass("Enter new password for 'suricata': ")
    if not password:
        print("ERROR: Password cannot be empty.")
        sys.exit(1)

    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("ERROR: Passwords do not match.")
        sys.exit(1)

    from werkzeug.security import generate_password_hash
    from sqlalchemy import create_engine, text

    password_hash = generate_password_hash(password)

    print(f"Connecting to database...")
    engine = create_engine(database_url)
    with engine.connect() as conn:
        result = conn.execute(
            text("UPDATE users SET password_hash = :h WHERE username = 'suricata'"),
            {"h": password_hash},
        )
        conn.commit()

        if result.rowcount == 0:
            print("ERROR: No user with username 'suricata' found in the database.")
            print("  Make sure the multi-user migration has been run first.")
            sys.exit(1)

    print("✓ Password set successfully for user 'suricata'.")


if __name__ == '__main__':
    main()
