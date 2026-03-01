from flask import Blueprint, render_template, request, redirect, url_for
from datetime import datetime
from utils import get_available_years_and_owners, ensure_budget_tables, local_now
from .views import (
    dashboard_overview_view,
    dashboard_budget_view,
    dashboard_categories_view
)

# Create the blueprint
dashboards_bp = Blueprint('dashboards', __name__)

@dashboards_bp.route('/')
def dashboard():
    """Main dashboard redirect"""
    return redirect(url_for('dashboards.enhanced_dashboard', view='overview'))

@dashboards_bp.route('/dashboard/<view>')
def enhanced_dashboard(view='overview'):
    """Enhanced dashboard with multiple views"""
    
    # Get filter parameters
    selected_year = request.args.get('year', local_now().year, type=int)
    selected_month = request.args.get('month', local_now().month, type=int)
    selected_owner = request.args.get('owner', 'all')
    
    print(f"🎯 Loading dashboard view: {view}")
    print(f"📅 Filters: Year={selected_year}, Month={selected_month}, Owner={selected_owner}")
    
    # Get available years and owners
    available_years, available_owners = get_available_years_and_owners()
    
    if view == 'overview':
        return dashboard_overview_view(selected_year, selected_month, selected_owner, available_years, available_owners)
    elif view == 'budget':
        return dashboard_budget_view(selected_year, selected_month, selected_owner, available_years, available_owners)
    elif view == 'categories':
        return dashboard_categories_view(available_years, available_owners)
    else:
        return redirect(url_for('dashboards.enhanced_dashboard', view='overview'))