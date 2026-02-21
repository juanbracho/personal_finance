from flask import Flask
from config import Config
from models import db
import os

def create_app(config_class=None):
    """Application factory pattern"""
    app = Flask(__name__)

    if config_class is None:
        config_class = Config
    app.config.from_object(config_class)

    # Initialize database with app
    db.init_app(app)

    # Enable CORS so the desktop web frontend and Flutter can reach the API.
    # Origins are restricted via CORS_ORIGINS in ProductionConfig.
    try:
        from flask_cors import CORS
        CORS(app, resources={r'/api/*': {'origins': app.config.get('CORS_ORIGINS', '*')}})
    except ImportError:
        pass  # flask-cors not installed; CORS headers omitted (fine for local use)

    # Import and register blueprints (personal finance only)
    from blueprints.dashboards.routes import dashboards_bp
    from blueprints.debts.routes import debts_bp
    from blueprints.transactions.routes import transactions_bp
    from blueprints.budgets.routes import budgets_bp
    from blueprints.api.routes import api_bp
    from blueprints.analytics.routes import analytics_bp
    from blueprints.settings.routes import settings_bp

    # Protect all /api/* routes with Bearer token auth.
    # check_api_key() is a no-op when API_SECRET_KEY is empty (local dev).
    from auth import check_api_key
    api_bp.before_request(check_api_key)

    # Register blueprints
    app.register_blueprint(dashboards_bp)
    app.register_blueprint(debts_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(budgets_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(settings_bp)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        from flask import render_template
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        from flask import render_template
        return render_template('500.html'), 500
    
    return app

def initialize_personal_finance_database():
    """Initialize personal finance database with proper setup and validation"""
    
    from utils import create_fresh_database, validate_database_integrity, get_database_stats
    
    database_exists = os.path.exists('data/personal_finance.db')
    
    if not database_exists:
        print("📦 No personal finance database found - creating fresh database...")
        if create_fresh_database():
            print("✅ Fresh personal finance database created successfully!")
            return True
        else:
            print("❌ Failed to create personal finance database")
            return False
    else:
        print("💾 Personal finance database found - validating integrity...")
        if validate_database_integrity():
            # Show database stats
            stats = get_database_stats()
            print("📊 Personal Finance Database statistics:")
            print(f"   - Transactions: {stats['transactions']:,}")
            print(f"   - Budget categories: {stats['budget_categories']}")
            print(f"   - Debt accounts: {stats['debt_accounts']}")
            print(f"   - Date range: {stats['date_range']['earliest']} to {stats['date_range']['latest']}")
            return True
        else:
            print("❌ Personal finance database validation failed - consider recreating database")
            return False

def test_database_connection():
    """Test database connection and basic functionality"""
    
    print("🔍 Testing database connection...")
    
    try:
        import sqlite3
        
        if not os.path.exists('data/personal_finance.db'):
            print("❌ Personal finance database file not found!")
            return False
        
        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()
        
        # Test basic table access
        cursor.execute("SELECT COUNT(*) FROM transactions")
        transaction_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM budget_templates WHERE is_active = 1")
        budget_count = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"✅ Database connection successful!")
        print(f"   - {transaction_count:,} transactions")
        print(f"   - {budget_count} budget categories")
        
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

if __name__ == '__main__':
    print("🚀 Starting Personal Finance Dashboard...")
    print("📊 Dashboard will be available at: http://127.0.0.1:5000")
    print("💾 Using database: personal_finance.db")
    print("=" * 60)
    
    # Initialize and validate personal finance database
    print("\n🏠 PERSONAL FINANCE DATABASE INITIALIZATION")
    print("-" * 50)
    if initialize_personal_finance_database():
        print("✅ Personal finance database initialization completed!")
    else:
        print("❌ Personal finance database initialization failed!")
        print("💡 You can try deleting personal_finance.db to start fresh")
        exit(1)
    
    # Test database connection
    print("\n🔍 DATABASE CONNECTION TESTING")
    print("-" * 50)
    if test_database_connection():
        print("✅ Database connection validated!")
    else:
        print("❌ Database connection test failed!")
        exit(1)
    
    # Create and run the app
    app = create_app()
    
    print("\n🎯 APPLICATION READY")
    print("=" * 60)
    print("✅ Application initialized successfully!")
    print("🎯 Available routes:")
    print("   - / (redirects to dashboard)")
    print("   - /dashboard/<view> (overview, yearly, monthly, budget, categories)")
    print("   - /debts (debt management)")
    print("   - /transactions (view transactions)")
    print("   - /transactions/add (add new transaction)")
    print("   - /budget (budget management)")
    print("   - /api/* (chart data endpoints)")
    print("=" * 60)
    print("🌟 Ready to start! Database is initialized and connected...")
    
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_PORT', '5000'))
    app.run(debug=False, host=host, port=port, use_reloader=False)