from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import Config
from models import db
import os

limiter = Limiter(key_func=get_remote_address, default_limits=[])


def create_app(config_class=None):
    """Application factory pattern"""
    app = Flask(__name__)

    if config_class is None:
        config_class = Config
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    limiter.init_app(app)

    # Create all tables if they don't exist
    with app.app_context():
        db.create_all()

    # Enable CORS so the desktop web frontend and Flutter can reach the API.
    from flask import request as _request

    @app.after_request
    def handle_cors(response):
        if not _request.path.startswith('/api/'):
            return response

        origin = _request.headers.get('Origin', '')
        allowed = app.config.get('CORS_ORIGINS', '*')

        if allowed == '*':
            response.headers['Access-Control-Allow-Origin'] = '*'
        else:
            allowed_list = [o.strip() for o in allowed.split(',')]
            if origin in allowed_list:
                response.headers['Access-Control-Allow-Origin'] = origin
                response.headers['Vary'] = 'Origin'

        if _request.method == 'OPTIONS':
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, PATCH, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            response.headers['Access-Control-Max-Age'] = '86400'

        return response

    # Import and register blueprints
    from blueprints.dashboards.routes import dashboards_bp
    from blueprints.debts.routes import debts_bp
    from blueprints.transactions.routes import transactions_bp
    from blueprints.budgets.routes import budgets_bp
    from blueprints.api.routes import api_bp
    from blueprints.analytics.routes import analytics_bp
    from blueprints.settings.routes import settings_bp
    from blueprints.admin.routes import admin_bp
    from blueprints.onboarding.routes import onboarding_bp

    from auth import check_jwt, check_web_session, auth_bp
    api_bp.before_request(check_jwt)
    app.before_request(check_web_session)
    app.register_blueprint(auth_bp)

    app.register_blueprint(dashboards_bp)
    app.register_blueprint(debts_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(budgets_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(onboarding_bp)

    @app.template_filter('currency')
    def currency_filter(value):
        try:
            return f"{float(value):,.2f}"
        except (ValueError, TypeError):
            return value

    @app.template_filter('currency_whole')
    def currency_whole_filter(value):
        try:
            return f"{float(value):,.0f}"
        except (ValueError, TypeError):
            return value

    @app.errorhandler(404)
    def not_found_error(error):
        from flask import render_template
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        from flask import render_template
        return render_template('500.html'), 500

    return app


if __name__ == '__main__':
    print("Starting Personal Finance Dashboard...")
    print("Dashboard will be available at: http://127.0.0.1:5000")

    app = create_app()

    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_PORT', '5000'))
    app.run(debug=False, host=host, port=port, use_reloader=False)
