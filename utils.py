from datetime import datetime
import sqlite3
import os

def create_fresh_database():
    """Create a completely fresh personal finance database with all required tables"""
    print("🚀 Creating fresh personal finance database...")
    
    try:
        # Remove existing database if it exists
        if os.path.exists('data/personal_finance.db'):
            os.remove('personal_finance.db')
            print("🗑️ Removed existing database")
        
        # Create new database
        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()
        
        # Create all required tables
        create_personal_finance_tables(cursor)
        
        # Initialize with basic data
        initialize_basic_data(cursor)
        
        conn.commit()
        conn.close()
        
        print("✅ Fresh database created successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error creating fresh database: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_personal_finance_tables(cursor):
    """Create all tables for personal finance module"""
    
    print("📋 Creating personal finance tables...")
    
    # Main transactions table
    cursor.execute('''
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_name TEXT NOT NULL,
            date DATE NOT NULL,
            description TEXT NOT NULL,
            amount DECIMAL(10,2) NOT NULL,
            sub_category TEXT,
            category TEXT NOT NULL,
            type TEXT NOT NULL,
            owner TEXT NOT NULL,
            is_business BOOLEAN DEFAULT 0,
            debt_payment_id INTEGER,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Budget templates table
    cursor.execute('''
        CREATE TABLE budget_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL UNIQUE,
            budget_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
            notes TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Unexpected expenses table
    cursor.execute('''
        CREATE TABLE unexpected_expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            month INTEGER NOT NULL CHECK(month >= 1 AND month <= 12),
            year INTEGER NOT NULL,
            amount DECIMAL(10,2) NOT NULL,
            description TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(category, month, year, description)
        )
    ''')
    
    # Monthly budgets table (for historical data)
    cursor.execute('''
        CREATE TABLE monthly_budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            month INTEGER NOT NULL CHECK(month >= 1 AND month <= 12),
            year INTEGER NOT NULL,
            budget_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(category, month, year)
        )
    ''')
    
    # Debt accounts table
    cursor.execute('''
        CREATE TABLE debt_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            debt_type TEXT NOT NULL,
            original_balance DECIMAL(10,2) NOT NULL,
            current_balance DECIMAL(10,2) NOT NULL,
            interest_rate DECIMAL(5,4),
            minimum_payment DECIMAL(10,2),
            due_date INTEGER,
            owner TEXT NOT NULL,
            category TEXT NOT NULL,
            account_number_last4 TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Debt payments table
    cursor.execute('''
        CREATE TABLE debt_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            debt_account_id INTEGER NOT NULL,
            payment_amount DECIMAL(10,2) NOT NULL,
            principal_amount DECIMAL(10,2),
            interest_amount DECIMAL(10,2),
            payment_date DATE NOT NULL,
            balance_after_payment DECIMAL(10,2) NOT NULL,
            payment_type TEXT DEFAULT 'Regular',
            notes TEXT,
            FOREIGN KEY (debt_account_id) REFERENCES debt_accounts(id)
        )
    ''')
    
    print("✅ All personal finance tables created")

def initialize_basic_data(cursor):
    """Initialize database with basic categories and setup data"""
    
    print("📊 Initializing basic data...")
    
    # Initialize basic expense categories
    basic_categories = [
        ('Living Expenses', 0.00, 'Essential living costs'),
        ('Dining Out', 0.00, 'Restaurants and food delivery'),
        ('Groceries', 0.00, 'Food and household items'),
        ('Transport', 0.00, 'Gas, public transit, car maintenance'),
        ('Entertainment', 0.00, 'Movies, games, hobbies'),
        ('Shopping', 0.00, 'Clothes, personal items'),
        ('Bills & Utilities', 0.00, 'Phone, internet, electricity'),
        ('Medical', 0.00, 'Healthcare and pharmacy'),
        ('Home', 0.00, 'Home maintenance and supplies'),
        ('Subscriptions', 0.00, 'Netflix, Spotify, apps'),
        ('Debt', 0.00, 'Debt payments and interest'),
        ('Savings', 0.00, 'Savings and investments'),
        ('Miscellaneous', 0.00, 'Other expenses')
    ]
    
    for category, amount, notes in basic_categories:
        cursor.execute('''
            INSERT INTO budget_templates (category, budget_amount, notes, is_active, created_at, updated_at)
            VALUES (?, ?, ?, 1, ?, ?)
        ''', (category, amount, notes, 
              datetime.utcnow().isoformat(), 
              datetime.utcnow().isoformat()))
    
    print(f"✅ Initialized {len(basic_categories)} basic categories")

def ensure_budget_tables(conn):
    """Legacy function - now just ensures tables exist (for backward compatibility)"""
    cursor = conn.cursor()
    
    # Check if tables exist, if not, create them
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='budget_templates'")
    if not cursor.fetchone():
        print("⚠️ Budget tables missing, creating them...")
        create_personal_finance_tables(cursor)
        initialize_basic_data(cursor)
        conn.commit()

def get_available_years_and_owners():
    """Get available years and owners from transactions"""
    try:
        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()
        
        # Get available years
        cursor.execute("""
            SELECT DISTINCT strftime('%Y', date) as year 
            FROM transactions 
            ORDER BY year DESC
        """)
        years_result = cursor.fetchall()
        available_years = [int(year[0]) for year in years_result if year[0]]
        
        # Get available owners
        cursor.execute("""
            SELECT DISTINCT owner 
            FROM transactions 
            ORDER BY owner
        """)
        owners_result = cursor.fetchall()
        available_owners = [owner[0] for owner in owners_result if owner[0]]
        
        conn.close()
        
        # Default values if no data exists
        if not available_years:
            current_year = datetime.now().year
            available_years = [current_year - 1, current_year, current_year + 1]
        
        if not available_owners:
            available_owners = ['Cata', 'Suricata', 'Cacas']
            
        return available_years, available_owners
        
    except Exception as e:
        print(f"❌ Error getting years/owners: {e}")
        current_year = datetime.now().year
        return [current_year - 1, current_year, current_year + 1], ['Cata', 'Suricata', 'Cacas']

def validate_database_integrity():
    """Validate that the database has all required tables and basic data"""
    
    print("🔍 Validating database integrity...")
    
    try:
        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()
        
        # Check for required tables
        required_tables = [
            'transactions', 'budget_templates', 'unexpected_expenses', 
            'monthly_budgets', 'debt_accounts', 'debt_payments'
        ]
        
        missing_tables = []
        for table in required_tables:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            if not cursor.fetchone():
                missing_tables.append(table)
        
        if missing_tables:
            print(f"❌ Missing tables: {missing_tables}")
            conn.close()
            return False
        
        # Check if budget templates have data
        cursor.execute("SELECT COUNT(*) FROM budget_templates WHERE is_active = 1")
        budget_count = cursor.fetchone()[0]
        
        if budget_count == 0:
            print("⚠️ No active budget templates found")
            initialize_basic_data(cursor)
            conn.commit()
        
        conn.close()
        print("✅ Database integrity validated")
        return True
        
    except Exception as e:
        print(f"❌ Database validation failed: {e}")
        return False

def get_database_stats():
    """Get basic statistics about the database content"""
    
    try:
        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()
        
        stats = {}
        
        # Transaction count
        cursor.execute("SELECT COUNT(*) FROM transactions")
        stats['transactions'] = cursor.fetchone()[0]
        
        # Budget templates count
        cursor.execute("SELECT COUNT(*) FROM budget_templates WHERE is_active = 1")
        stats['budget_categories'] = cursor.fetchone()[0]
        
        # Debt accounts count
        cursor.execute("SELECT COUNT(*) FROM debt_accounts WHERE is_active = 1")
        stats['debt_accounts'] = cursor.fetchone()[0]
        
        # Date range
        cursor.execute("SELECT MIN(date), MAX(date) FROM transactions")
        date_result = cursor.fetchone()
        stats['date_range'] = {
            'earliest': date_result[0] if date_result[0] else 'No data',
            'latest': date_result[1] if date_result[1] else 'No data'
        }
        
        conn.close()
        return stats
        
    except Exception as e:
        print(f"❌ Error getting database stats: {e}")
        return {
            'transactions': 0,
            'budget_categories': 0,
            'debt_accounts': 0,
            'date_range': {'earliest': 'Error', 'latest': 'Error'}
        }

def reset_database():
    """Reset the entire database - useful for testing"""
    
    print("🔄 Resetting database...")
    confirmation = input("⚠️ This will delete ALL data. Type 'RESET' to confirm: ")
    
    if confirmation == 'RESET':
        if create_fresh_database():
            print("✅ Database reset completed")
            return True
        else:
            print("❌ Database reset failed")
            return False
    else:
        print("❌ Reset cancelled")
        return False