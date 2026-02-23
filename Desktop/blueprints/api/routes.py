from flask import Blueprint, jsonify, request, current_app
from datetime import datetime
from utils import ensure_budget_tables
import pandas as pd
import sqlite3

# Create the blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/monthly_trends')
def monthly_trends():
    """Get monthly spending trends for charts"""

    try:
        owner = request.args.get('owner', 'all')
        date_range = request.args.get('date_range', '365')  # days
        type_filter = request.args.get('type', None)  # optional Kakeibo type filter

        conn = sqlite3.connect('data/personal_finance.db')

        # Build filter conditions
        extra_filters = ""
        params = []
        if owner != 'all':
            extra_filters += " AND owner = ?"
            params.append(owner)
        if type_filter and type_filter != 'all':
            extra_filters += " AND type = ?"
            params.append(type_filter)

        # Sum spending per month. Optionally filtered by Kakeibo type.
        trends_query = f"""
        SELECT
            strftime('%Y-%m', date) as month,
            SUM(amount) as total
        FROM transactions
        WHERE date >= date('now', '-12 months') AND COALESCE(is_active, 1) = 1
        {extra_filters}
        GROUP BY strftime('%Y-%m', date)
        ORDER BY month DESC
        """

        trends_df = pd.read_sql_query(trends_query, conn, params=params)
        conn.close()

        result_list = [
            {'month': row['month'], 'expense': float(row['total'])}
            for _, row in trends_df.iterrows()
        ]
        result_list.sort(key=lambda x: x['month'])

        return jsonify(result_list)
        
    except Exception as e:
        print(f"❌ Error in monthly trends API: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/category_spending')
def category_spending():
    """Get category spending data with filters"""
    
    try:
        owner = request.args.get('owner', 'all')
        date_range = request.args.get('date_range', '30')  # days
        include_business = request.args.get('include_business', 'true').lower() == 'true'
        
        conn = sqlite3.connect('data/personal_finance.db')
        
        # Build filter conditions
        filters = []
        params = []
        
        # Date filter
        if date_range != 'all':
            filters.append("date >= date('now', '-' || ? || ' days')")
            params.append(date_range)
        
        # Owner filter
        if owner != 'all':
            filters.append("owner = ?")
            params.append(owner)
        
        # Business filter
        if not include_business:
            filters.append("is_business = 0")
        
        where_clause = "WHERE " + " AND ".join(filters) if filters else ""
        
        category_query = f"""
        SELECT 
            category,
            SUM(amount) as total,
            COUNT(*) as transaction_count,
            AVG(amount) as avg_amount
        FROM transactions 
        {where_clause} AND COALESCE(is_active, 1) = 1
        GROUP BY category
        ORDER BY total DESC
        LIMIT 20
        """
        
        category_df = pd.read_sql_query(category_query, conn, params=params)
        conn.close()
        
        result = [{
            'category': str(row['category']),
            'total': float(row['total']),
            'transaction_count': int(row['transaction_count']),
            'avg_amount': float(row['avg_amount'])
        } for _, row in category_df.iterrows()]
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Error in category spending API: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/budget_analysis')
def budget_analysis():
    """Get comprehensive budget analysis for a specific month/year"""
    
    try:
        month = request.args.get('month', datetime.now().month, type=int)
        year = request.args.get('year', datetime.now().year, type=int)
        owner = request.args.get('owner', 'all')
        
        conn = sqlite3.connect('data/personal_finance.db')
        ensure_budget_tables(conn)
        
        # Get filter for actual spending
        spending_filter = "strftime('%m', date) = ? AND strftime('%Y', date) = ?"
        spending_params = [f"{month:02d}", str(year)]
        
        if owner != 'all':
            spending_filter += " AND owner = ?"
            spending_params.append(owner)
        
        # Get actual spending
        actual_spending_query = f"""
        SELECT 
            category,
            SUM(amount) as actual_amount,
            COUNT(*) as transaction_count
        FROM transactions 
        WHERE {spending_filter} AND COALESCE(is_active, 1) = 1
        GROUP BY category
        ORDER BY actual_amount DESC
        """
        actual_spending_df = pd.read_sql_query(actual_spending_query, conn, params=spending_params)
        
        # Get initial budgets — use subcategory templates (the source the web
        # Budget page writes to) so values match what the user actually set.
        initial_budgets_query = """
        SELECT category, SUM(budget_amount) AS budget_amount
        FROM budget_subcategory_templates
        WHERE is_active = 1
        GROUP BY category
        ORDER BY category
        """
        initial_budgets_df = pd.read_sql_query(initial_budgets_query, conn)
        
        # Get unexpected expenses
        unexpected_expenses_query = """
        SELECT category, SUM(amount) as total_unexpected
        FROM unexpected_expenses 
        WHERE month = ? AND year = ? AND is_active = 1
        GROUP BY category
        ORDER BY category
        """
        unexpected_expenses_df = pd.read_sql_query(unexpected_expenses_query, conn, params=[month, year])
        
        conn.close()
        
        # Process data
        initial_budget_dict = {row['category']: float(row['budget_amount']) for _, row in initial_budgets_df.iterrows()}
        unexpected_expenses_dict = {row['category']: float(row['total_unexpected']) for _, row in unexpected_expenses_df.iterrows()}
        actual_spending_dict = {row['category']: float(row['actual_amount']) for _, row in actual_spending_df.iterrows()}
        
        # Create comprehensive analysis
        all_categories = set(initial_budget_dict.keys()) | set(unexpected_expenses_dict.keys()) | set(actual_spending_dict.keys())
        
        result = []
        for category in sorted(all_categories):
            initial_budget = initial_budget_dict.get(category, 0.0)
            unexpected_expenses = unexpected_expenses_dict.get(category, 0.0)
            effective_budget = initial_budget + unexpected_expenses
            actual_spending = actual_spending_dict.get(category, 0.0)
            
            variance = actual_spending - effective_budget
            variance_pct = (variance / effective_budget * 100) if effective_budget > 0 else 0
            
            # Determine status
            if effective_budget == 0:
                status = 'no_budget'
            elif variance > 50:
                status = 'over'
            elif variance < -50:
                status = 'under'
            else:
                status = 'on_track'
            
            result.append({
                'category': category,
                'initial_budget': initial_budget,
                'unexpected_expenses': unexpected_expenses,
                'effective_budget': effective_budget,
                'actual_spending': actual_spending,
                'variance': variance,
                'variance_pct': variance_pct,
                'status': status
            })
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Error in budget analysis API: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/budget_subcategories')
def budget_subcategories():
    """Get budget analysis with subcategory breakdown for Flutter accordion view.

    Returns a list of categories, each with a nested list of subcategories.
    Categories that have no subcategory templates are returned with the category
    itself as a single subcategory row (so the accordion always has content).

    Params: year, month, owner
    """
    try:
        month = request.args.get('month', datetime.now().month, type=int)
        year  = request.args.get('year',  datetime.now().year,  type=int)
        owner = request.args.get('owner', 'all')

        conn = sqlite3.connect('data/personal_finance.db')
        ensure_budget_tables(conn)

        spending_filter = (
            "strftime('%m', date) = ? AND strftime('%Y', date) = ?"
            " AND COALESCE(is_active, 1) = 1"
        )
        spending_params = [f"{month:02d}", str(year)]
        if owner != 'all':
            spending_filter += " AND owner = ?"
            spending_params.append(owner)

        # Actual spending grouped by category + sub_category
        spending_df = pd.read_sql_query(f"""
            SELECT
                category,
                COALESCE(NULLIF(TRIM(sub_category), ''), '(other)') AS sub_category,
                SUM(amount) AS actual
            FROM transactions
            WHERE {spending_filter}
            GROUP BY category, sub_category
            ORDER BY category, sub_category
        """, conn, params=spending_params)

        # Category-level initial budgets — sum from subcategory templates
        # (the source the web Budget page writes to, not the stale budget_templates)
        cat_budgets_df = pd.read_sql_query(
            "SELECT category, SUM(budget_amount) AS budget_amount"
            " FROM budget_subcategory_templates WHERE is_active = 1"
            " GROUP BY category",
            conn
        )

        # Subcategory budgets
        subcat_budgets_df = pd.read_sql_query(
            "SELECT category, sub_category, budget_amount"
            " FROM budget_subcategory_templates WHERE is_active = 1",
            conn
        )

        # Unexpected expenses (category level)
        unexpected_df = pd.read_sql_query("""
            SELECT category, SUM(amount) AS total_unexpected
            FROM unexpected_expenses
            WHERE month = ? AND year = ? AND is_active = 1
            GROUP BY category
        """, conn, params=[month, year])

        conn.close()

        # ── Build lookup dicts ───────────────────────────────────────────────
        cat_budgets  = {r['category']: float(r['budget_amount'])     for _, r in cat_budgets_df.iterrows()}
        unexpected   = {r['category']: float(r['total_unexpected'])  for _, r in unexpected_df.iterrows()}

        subcat_budgets: dict = {}   # {category: {sub_category: budget}}
        for _, r in subcat_budgets_df.iterrows():
            subcat_budgets.setdefault(r['category'], {})[r['sub_category']] = float(r['budget_amount'])

        spending: dict = {}         # {category: {sub_category: actual}}
        for _, r in spending_df.iterrows():
            spending.setdefault(r['category'], {})[r['sub_category']] = float(r['actual'])

        def _status(variance, budget):
            if budget == 0:      return 'no_budget'
            if variance >  50:   return 'over'
            if variance < -50:   return 'under'
            return 'on_track'

        all_categories = (
            set(cat_budgets.keys()) |
            set(subcat_budgets.keys()) |
            set(spending.keys()) |
            set(unexpected.keys())
        )

        result = []
        for category in sorted(all_categories):
            cat_initial    = cat_budgets.get(category, 0.0)
            cat_unexpected = unexpected.get(category, 0.0)
            cat_subs_b     = subcat_budgets.get(category, {})
            cat_subs_s     = spending.get(category, {})
            all_subs       = set(cat_subs_b.keys()) | set(cat_subs_s.keys())

            subcategories = []
            if all_subs:
                for sub in sorted(all_subs):
                    sub_budget = cat_subs_b.get(sub, 0.0)
                    sub_actual = cat_subs_s.get(sub, 0.0)
                    sub_var    = sub_actual - sub_budget
                    subcategories.append({
                        'sub_category':   sub,
                        'initial_budget': sub_budget,
                        'actual_spending': sub_actual,
                        'variance':       sub_var,
                        'status':         _status(sub_var, sub_budget),
                    })
            else:
                # No sub-category definitions — category is its own sub
                cat_actual = sum(cat_subs_s.values()) if cat_subs_s else 0.0
                cat_var    = cat_actual - cat_initial
                subcategories.append({
                    'sub_category':    category,
                    'initial_budget':  cat_initial,
                    'actual_spending': cat_actual,
                    'variance':        cat_var,
                    'status':          _status(cat_var, cat_initial),
                })

            cat_actual_total = sum(s['actual_spending'] for s in subcategories)
            cat_effective    = cat_initial + cat_unexpected
            cat_var          = cat_actual_total - cat_effective

            result.append({
                'category':           category,
                'initial_budget':     cat_initial,
                'unexpected_expenses': cat_unexpected,
                'effective_budget':   cat_effective,
                'actual_spending':    cat_actual_total,
                'variance':           cat_var,
                'status':             _status(cat_var, cat_effective),
                'subcategories':      subcategories,
            })

        return jsonify(result)

    except Exception as e:
        print(f"❌ Error in budget_subcategories: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/dashboard_summary')
def dashboard_summary():
    """Get dashboard summary data for quick overview"""
    
    try:
        year = request.args.get('year', datetime.now().year, type=int)
        month = request.args.get('month', datetime.now().month, type=int)
        owner = request.args.get('owner', 'all')
        
        conn = sqlite3.connect('data/personal_finance.db')
        
        # Build filter conditions
        date_filter = "strftime('%m', date) = ? AND strftime('%Y', date) = ?"
        params = [f"{month:02d}", str(year)]
        
        if owner != 'all':
            date_filter += " AND owner = ?"
            params.append(owner)
        
        # Get monthly totals
        monthly_query = f"""
        SELECT 
            type,
            SUM(amount) as total,
            COUNT(*) as count
        FROM transactions 
        WHERE {date_filter} AND COALESCE(is_active, 1) = 1
        GROUP BY type
        """
        monthly_df = pd.read_sql_query(monthly_query, conn, params=params)
        
        # Get top categories
        categories_query = f"""
        SELECT 
            category,
            SUM(amount) as total,
            COUNT(*) as count
        FROM transactions 
        WHERE {date_filter} AND COALESCE(is_active, 1) = 1
        GROUP BY category
        ORDER BY total DESC
        LIMIT 5
        """
        categories_df = pd.read_sql_query(categories_query, conn, params=params)
        
        # Get debt totals (if debt accounts exist)
        try:
            debt_query = """
            SELECT 
                COALESCE(SUM(current_balance), 0) as total_debt,
                COALESCE(SUM(minimum_payment), 0) as total_minimum_payments,
                COUNT(*) as debt_accounts
            FROM debt_accounts 
            WHERE is_active = 1
            """
            debt_df = pd.read_sql_query(debt_query, conn)
            debt_data = debt_df.iloc[0].to_dict() if not debt_df.empty else {'total_debt': 0, 'total_minimum_payments': 0, 'debt_accounts': 0}
        except:
            debt_data = {'total_debt': 0, 'total_minimum_payments': 0, 'debt_accounts': 0}
        
        conn.close()
        
        # Process monthly data
        monthly_spending = {}
        total_spending = 0
        for _, row in monthly_df.iterrows():
            monthly_spending[row['type']] = {
                'total': float(row['total']),
                'count': int(row['count'])
            }
            total_spending += float(row['total'])
        
        # Process category data
        top_categories = [{
            'category': str(row['category']),
            'total': float(row['total']),
            'count': int(row['count'])
        } for _, row in categories_df.iterrows()]
        
        result = {
            'summary': {
                'total_monthly_spending': total_spending,
                'total_debt': float(debt_data['total_debt']),
                'total_minimum_payments': float(debt_data['total_minimum_payments']),
                'debt_accounts': int(debt_data['debt_accounts']),
                'period': f"{year}-{month:02d}",
                'owner': owner
            },
            'monthly_spending': monthly_spending,
            'top_categories': top_categories
        }
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Error in dashboard summary API: {e}")
        return jsonify({'error': str(e)}), 500
    
@api_bp.route('/categories/categories')
def api_categories():
    """Get categories with statistics"""

    try:
        year = request.args.get('year', datetime.now().year, type=int)
        month = request.args.get('month', 'all')
        owner = request.args.get('owner', 'all')

        conn = sqlite3.connect('data/personal_finance.db')

        # Build date filter
        date_filter = "strftime('%Y', date) = ?"
        params = [str(year)]

        if month != 'all':
            date_filter += " AND strftime('%m', date) = ?"
            params.append(f"{int(month):02d}")

        if owner != 'all':
            date_filter += " AND owner = ?"
            params.append(owner)
        
        # Get categories with statistics
        categories_query = f"""
        SELECT 
            t.category,
            COUNT(*) as transaction_count,
            SUM(t.amount) as total_amount,
            AVG(t.amount) as avg_amount,
            bt.budget_amount,
            MAX(t.date) as last_used,
            MIN(t.date) as first_used
        FROM transactions t
        LEFT JOIN budget_templates bt ON t.category = bt.category AND bt.is_active = 1
        WHERE {date_filter}
        GROUP BY t.category, bt.budget_amount
        ORDER BY total_amount DESC
        """
        
        categories_df = pd.read_sql_query(categories_query, conn, params=params)
        
        # Get category types (we'll need to determine this from transaction patterns)
        type_query = f"""
        SELECT 
            category,
            type,
            COUNT(*) as type_count
        FROM transactions 
        WHERE {date_filter}
        GROUP BY category, type
        ORDER BY category, type_count DESC
        """
        
        type_df = pd.read_sql_query(type_query, conn, params=params)
        conn.close()
        
        # Determine primary type for each category
        category_types = {}
        for _, row in type_df.iterrows():
            if row['category'] not in category_types:
                category_types[row['category']] = row['type']
        
        result = []
        for _, row in categories_df.iterrows():
            result.append({
                'name': str(row['category']),
                'type': category_types.get(row['category'], ''),
                'transaction_count': int(row['transaction_count']),
                'total_amount': float(row['total_amount']),
                'avg_amount': float(row['avg_amount']),
                'budget_amount': float(row['budget_amount']) if row['budget_amount'] else 0.0,
                'last_used': str(row['last_used']),
                'first_used': str(row['first_used'])
            })
        
        print(f"📊 Returning {len(result)} categories")
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Error getting categories: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/categories/subcategories')
def api_subcategories():
    """Get subcategories with statistics"""

    try:
        year = request.args.get('year', datetime.now().year, type=int)
        month = request.args.get('month', 'all')
        owner = request.args.get('owner', 'all')

        conn = sqlite3.connect('data/personal_finance.db')

        # Build date filter
        date_filter = "strftime('%Y', date) = ?"
        params = [str(year)]

        if month != 'all':
            date_filter += " AND strftime('%m', date) = ?"
            params.append(f"{int(month):02d}")

        if owner != 'all':
            date_filter += " AND owner = ?"
            params.append(owner)
        
        # Get subcategories with statistics - FIXED QUERY
        subcategories_query = f"""
        SELECT 
            sub_category as name,
            category,
            COUNT(*) as transaction_count,
            SUM(amount) as total_amount,
            AVG(amount) as avg_amount,
            MAX(date) as last_used,
            MIN(date) as first_used
        FROM transactions 
        WHERE {date_filter} AND sub_category IS NOT NULL AND sub_category != '' AND COALESCE(is_active, 1) = 1
        GROUP BY sub_category, category
        ORDER BY total_amount DESC
        """
        
        subcategories_df = pd.read_sql_query(subcategories_query, conn, params=params)
        conn.close()
        
        result = []
        for _, row in subcategories_df.iterrows():
            result.append({
                'name': str(row['name']),
                'category': str(row['category']),
                'transaction_count': int(row['transaction_count']),
                'total_amount': float(row['total_amount']),
                'avg_amount': float(row['avg_amount']),
                'last_used': str(row['last_used']),
                'first_used': str(row['first_used'])
            })
        
        print(f"🏷️ Returning {len(result)} subcategories")
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Error getting subcategories: {e}")
        return jsonify({'error': str(e)}), 500
    
@api_bp.route('/categories/owners')
def api_owners():
    """Get owners with statistics"""
    
    try:
        year = request.args.get('year', datetime.now().year, type=int)
        month = request.args.get('month', 'all')
        
        conn = sqlite3.connect('data/personal_finance.db')
        
        # Build date filter
        date_filter = "strftime('%Y', date) = ?"
        params = [str(year)]
        
        if month != 'all':
            date_filter += " AND strftime('%m', date) = ?"
            params.append(f"{int(month):02d}")
        
        # Get owners with statistics
        owners_query = f"""
        SELECT 
            owner as name,
            COUNT(*) as transaction_count,
            SUM(amount) as total_amount,
            AVG(amount) as avg_amount,
            MAX(date) as last_used,
            MIN(date) as first_used
        FROM transactions 
        WHERE {date_filter} AND COALESCE(is_active, 1) = 1
        GROUP BY owner
        ORDER BY total_amount DESC
        """
        
        owners_df = pd.read_sql_query(owners_query, conn, params=params)
        conn.close()
        
        result = []
        for _, row in owners_df.iterrows():
            result.append({
                'name': str(row['name']),
                'transaction_count': int(row['transaction_count']),
                'total_amount': float(row['total_amount']),
                'avg_amount': float(row['avg_amount']),
                'last_used': str(row['last_used']),
                'first_used': str(row['first_used'])
            })
        
        print(f"👥 Returning {len(result)} owners")
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Error getting owners: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/categories/accounts')
def api_accounts():
    """Get accounts with statistics"""
    
    try:
        year = request.args.get('year', datetime.now().year, type=int)
        month = request.args.get('month', 'all')
        
        conn = sqlite3.connect('data/personal_finance.db')
        
        # Build date filter
        date_filter = "strftime('%Y', date) = ?"
        params = [str(year)]
        
        if month != 'all':
            date_filter += " AND strftime('%m', date) = ?"
            params.append(f"{int(month):02d}")
        
        # Get accounts with statistics
        accounts_query = f"""
        SELECT 
            account_name as name,
            COUNT(*) as transaction_count,
            SUM(amount) as total_amount,
            AVG(amount) as avg_amount,
            MAX(date) as last_used,
            MIN(date) as first_used
        FROM transactions 
        WHERE {date_filter} AND COALESCE(is_active, 1) = 1
        GROUP BY account_name
        ORDER BY total_amount DESC
        """
        
        accounts_df = pd.read_sql_query(accounts_query, conn, params=params)
        conn.close()
        
        result = []
        for _, row in accounts_df.iterrows():
            result.append({
                'name': str(row['name']),
                'transaction_count': int(row['transaction_count']),
                'total_amount': float(row['total_amount']),
                'avg_amount': float(row['avg_amount']),
                'last_used': str(row['last_used']),
                'first_used': str(row['first_used'])
            })
        
        print(f"💳 Returning {len(result)} accounts")
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Error getting accounts: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/categories/types')
def api_types():
    """Get types with statistics (includes custom types with 0 transactions)"""

    try:
        # all_years=1 → skip date filter entirely (used by the mobile form so
        # every type ever recorded in the DB is available for selection)
        all_years = request.args.get('all_years', '0') == '1'
        year = request.args.get('year', datetime.now().year, type=int)
        month = request.args.get('month', 'all')
        owner = request.args.get('owner', 'all')

        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()

        # Ensure custom_types table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS custom_types (
                name TEXT PRIMARY KEY,
                created_at TEXT NOT NULL
            )
        """)

        # Build date filter
        if all_years:
            date_filter = "1=1"
            params = []
        else:
            date_filter = "strftime('%Y', date) = ?"
            params = [str(year)]

            if month != 'all':
                date_filter += " AND strftime('%m', date) = ?"
                params.append(f"{int(month):02d}")

        if owner != 'all':
            date_filter += " AND owner = ?"
            params.append(owner)

        # Get types from transactions
        types_query = f"""
        SELECT
            type as name,
            COUNT(*) as transaction_count,
            SUM(amount) as total_amount,
            AVG(amount) as avg_amount,
            MAX(date) as last_used,
            MIN(date) as first_used
        FROM transactions
        WHERE {date_filter}
        GROUP BY type
        ORDER BY total_amount DESC
        """

        types_df = pd.read_sql_query(types_query, conn, params=params)
        txn_type_names = set(types_df['name'].tolist())

        # Also get custom types with no transactions in current filter
        cursor.execute("SELECT name FROM custom_types")
        custom_names = [row[0] for row in cursor.fetchall() if row[0] not in txn_type_names]

        conn.close()

        result = []
        for _, row in types_df.iterrows():
            result.append({
                'name': str(row['name']),
                'transaction_count': int(row['transaction_count']),
                'total_amount': float(row['total_amount']),
                'avg_amount': float(row['avg_amount']),
                'last_used': str(row['last_used']),
                'first_used': str(row['first_used'])
            })

        # Append custom types with zeros
        for name in custom_names:
            result.append({
                'name': name,
                'transaction_count': 0,
                'total_amount': 0.0,
                'avg_amount': 0.0,
                'last_used': '—',
                'first_used': '—'
            })

        print(f"🔖 Returning {len(result)} types")
        return jsonify(result)

    except Exception as e:
        print(f"❌ Error getting types: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/categories/types', methods=['POST'])
def add_type():
    """Add a new custom type"""
    try:
        data = request.get_json()
        name = (data.get('name') or '').strip()
        if not name:
            return jsonify({'success': False, 'error': 'Name is required'}), 400

        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS custom_types (
                name TEXT PRIMARY KEY,
                created_at TEXT NOT NULL
            )
        """)

        # Check if already in use
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE type = ?", (name,))
        if cursor.fetchone()[0] > 0:
            conn.close()
            return jsonify({'success': False, 'error': f'Type "{name}" already exists in transactions'}), 400

        try:
            cursor.execute("INSERT INTO custom_types (name, created_at) VALUES (?, ?)",
                           (name, datetime.utcnow().isoformat()))
            conn.commit()
        except Exception:
            conn.close()
            return jsonify({'success': False, 'error': f'Type "{name}" already exists'}), 400

        conn.close()
        return jsonify({'success': True, 'message': f'Type "{name}" created successfully'})

    except Exception as e:
        print(f"❌ Error adding type: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/categories/types/<type_name>', methods=['PUT'])
def edit_type(type_name):
    """Rename a type (updates all transactions and custom_types table)"""
    try:
        data = request.get_json()
        new_name = (data.get('name') or '').strip()
        if not new_name:
            return jsonify({'success': False, 'error': 'Name is required'}), 400

        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS custom_types (
                name TEXT PRIMARY KEY,
                created_at TEXT NOT NULL
            )
        """)

        cursor.execute("UPDATE transactions SET type = ?, updated_at = ? WHERE type = ?",
                       (new_name, datetime.utcnow().isoformat(), type_name))
        cursor.execute("UPDATE custom_types SET name = ? WHERE name = ?", (new_name, type_name))

        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': f'Type renamed from "{type_name}" to "{new_name}"'})

    except Exception as e:
        print(f"❌ Error editing type: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/categories/types/<type_name>', methods=['DELETE'])
def delete_type(type_name):
    """Delete a custom type (only if no transactions use it)"""
    try:
        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS custom_types (
                name TEXT PRIMARY KEY,
                created_at TEXT NOT NULL
            )
        """)

        cursor.execute("SELECT COUNT(*) FROM transactions WHERE type = ?", (type_name,))
        count = cursor.fetchone()[0]
        if count > 0:
            conn.close()
            return jsonify({
                'success': False,
                'error': f'Cannot delete: {count} transactions use this type. Migrate first.',
                'transaction_count': count
            }), 400

        cursor.execute("DELETE FROM custom_types WHERE name = ?", (type_name,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': f'Type "{type_name}" deleted'})

    except Exception as e:
        print(f"❌ Error deleting type: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/categories/migration_preview')
def api_migration_preview():
    """Get preview of transactions that would be affected by migration"""
    
    try:
        item_type = request.args.get('type')
        name = request.args.get('name')
        
        if not item_type or not name:
            return jsonify({'error': 'Type and name required'}), 400
        
        conn = sqlite3.connect('data/personal_finance.db')
        
        # Determine which field to query
        field_map = {
            'category': 'category',
            'subcategory': 'sub_category',
            'owner': 'owner',
            'account': 'account_name',
            'type': 'type'
        }

        field = field_map.get(item_type)
        if not field:
            return jsonify({'error': 'Invalid type'}), 400
        
        # Get affected transactions
        preview_query = f"""
        SELECT 
            date,
            description,
            amount,
            category,
            sub_category,
            owner,
            account_name
        FROM transactions 
        WHERE {field} = ? AND COALESCE(is_active, 1) = 1
        ORDER BY date DESC
        LIMIT 50
        """
        
        preview_df = pd.read_sql_query(preview_query, conn, params=[name])
        conn.close()
        
        result = []
        for _, row in preview_df.iterrows():
            result.append({
                'date': str(row['date']),
                'description': str(row['description']),
                'amount': float(row['amount']),
                'category': str(row['category']),
                'sub_category': str(row['sub_category']) if row['sub_category'] else '',
                'owner': str(row['owner']),
                'account_name': str(row['account_name'])
            })
        
        print(f"🔍 Returning preview of {len(result)} transactions for {item_type}: {name}")
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Error getting migration preview: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/categories/categories', methods=['POST'])
def add_category():
    """Add a new category"""
    
    try:
        data = request.get_json()
        name = data['name'].strip()
        category_type = data.get('type', '')
        
        if not name:
            return jsonify({'success': False, 'error': 'Category name required'}), 400
        
        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()
        
        # Check if category already exists in transactions
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE category = ?", (name,))
        if cursor.fetchone()[0] > 0:
            conn.close()
            return jsonify({'success': False, 'error': 'Category already exists in transactions'}), 400
        
        # Add to budget templates to track it
        cursor.execute("""
            INSERT OR IGNORE INTO budget_templates 
            (category, budget_amount, notes, is_active, created_at, updated_at)
            VALUES (?, 0.00, ?, 1, ?, ?)
        """, (name, f'Added via categories management', 
              datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Added category: {name}")
        return jsonify({'success': True, 'message': f'Category "{name}" added successfully'})
        
    except Exception as e:
        print(f"❌ Error adding category: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/categories/subcategories', methods=['POST'])
def add_subcategory():
    """Add a new subcategory"""
    
    try:
        data = request.get_json()
        name = data['name'].strip()
        category = data['category'].strip()
        
        if not name or not category:
            return jsonify({'success': False, 'error': 'Subcategory name and parent category required'}), 400
        
        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()
        
        # Check if subcategory already exists
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE sub_category = ?", (name,))
        if cursor.fetchone()[0] > 0:
            conn.close()
            return jsonify({'success': False, 'error': 'Subcategory already exists in transactions'}), 400
        
        # Verify parent category exists
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE category = ?", (category,))
        if cursor.fetchone()[0] == 0:
            conn.close()
            return jsonify({'success': False, 'error': 'Parent category does not exist'}), 400
        
        conn.close()
        
        print(f"✅ Subcategory ready to be added: {name} under {category}")
        return jsonify({'success': True, 'message': f'Subcategory "{name}" ready to be used under "{category}"'})
        
    except Exception as e:
        print(f"❌ Error adding subcategory: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/categories/owners', methods=['POST'])
def add_owner():
    """Add a new owner"""
    
    try:
        data = request.get_json()
        name = data['name'].strip()
        
        if not name:
            return jsonify({'success': False, 'error': 'Owner name required'}), 400
        
        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()
        
        # Check if owner already exists
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE owner = ?", (name,))
        if cursor.fetchone()[0] > 0:
            conn.close()
            return jsonify({'success': False, 'error': 'Owner already exists in transactions'}), 400
        
        conn.close()
        
        print(f"✅ Owner ready to be added: {name}")
        return jsonify({'success': True, 'message': f'Owner "{name}" ready to be used in transactions'})
        
    except Exception as e:
        print(f"❌ Error adding owner: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/categories/accounts', methods=['POST'])
def add_account():
    """Add a new account"""
    
    try:
        data = request.get_json()
        name = data['name'].strip()
        
        if not name:
            return jsonify({'success': False, 'error': 'Account name required'}), 400
        
        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()
        
        # Check if account already exists
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE account_name = ?", (name,))
        if cursor.fetchone()[0] > 0:
            conn.close()
            return jsonify({'success': False, 'error': 'Account already exists in transactions'}), 400
        
        conn.close()
        
        print(f"✅ Account ready to be added: {name}")
        return jsonify({'success': True, 'message': f'Account "{name}" ready to be used in transactions'})
        
    except Exception as e:
        print(f"❌ Error adding account: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/categories/migrate', methods=['POST'])
def migrate_categories():
    """Migrate transactions from one category/subcategory/owner/account to another"""
    
    try:
        data = request.get_json()
        item_type = data['type']
        source = data['source']
        target = data['target']
        
        if not all([item_type, source, target]):
            return jsonify({'success': False, 'error': 'Type, source, and target required'}), 400
        
        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()
        
        # Determine which field to update
        field_map = {
            'category': 'category',
            'subcategory': 'sub_category',
            'owner': 'owner',
            'account': 'account_name',
            'type': 'type'
        }

        field = field_map.get(item_type)
        if not field:
            return jsonify({'success': False, 'error': 'Invalid type'}), 400

        # Get count of affected transactions
        cursor.execute(f"SELECT COUNT(*) FROM transactions WHERE {field} = ?", (source,))
        affected_count = cursor.fetchone()[0]
        
        if affected_count == 0:
            conn.close()
            return jsonify({'success': False, 'error': 'No transactions found to migrate'}), 400
        
        # Perform migration
        cursor.execute(f"""
            UPDATE transactions 
            SET {field} = ?, updated_at = ?
            WHERE {field} = ?
        """, (target, datetime.utcnow().isoformat(), source))
        
        migrated_count = cursor.rowcount
        
        # If it's a category, also update budget templates
        if item_type == 'category':
            cursor.execute("""
                UPDATE budget_templates 
                SET category = ?, updated_at = ?
                WHERE category = ?
            """, (target, datetime.utcnow().isoformat(), source))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Migrated {migrated_count} transactions from {source} to {target}")
        return jsonify({
            'success': True, 
            'message': f'Successfully migrated {migrated_count} transactions from "{source}" to "{target}"'
        })
        
    except Exception as e:
        print(f"❌ Error migrating categories: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/categories/categories/<category_name>', methods=['DELETE'])
def delete_category(category_name):
    """Delete a category (only if no transactions)"""
    
    try:
        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()
        
        # Check if category has transactions
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE category = ?", (category_name,))
        transaction_count = cursor.fetchone()[0]
        
        if transaction_count > 0:
            conn.close()
            return jsonify({'success': False, 'error': f'Cannot delete category with {transaction_count} transactions. Please migrate them first.'}), 400
        
        # Remove from budget templates
        cursor.execute("DELETE FROM budget_templates WHERE category = ?", (category_name,))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Deleted category: {category_name}")
        return jsonify({'success': True, 'message': f'Category "{category_name}" deleted successfully'})
        
    except Exception as e:
        print(f"❌ Error deleting category: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Similar delete endpoints for other types...
@api_bp.route('/categories/subcategories/<subcategory_name>', methods=['DELETE'])
def delete_subcategory(subcategory_name):
    """Delete a subcategory (only if no transactions)"""
    
    try:
        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()
        
        # Check if subcategory has transactions
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE sub_category = ?", (subcategory_name,))
        transaction_count = cursor.fetchone()[0]
        
        if transaction_count > 0:
            conn.close()
            return jsonify({'success': False, 'error': f'Cannot delete subcategory with {transaction_count} transactions. Please migrate them first.'}), 400
        
        conn.close()
        
        print(f"✅ Subcategory {subcategory_name} can be deleted (no transactions)")
        return jsonify({'success': True, 'message': f'Subcategory "{subcategory_name}" removed from system'})
        
    except Exception as e:
        print(f"❌ Error deleting subcategory: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
@api_bp.route('/categories/categories/<category_name>', methods=['PUT'])
def edit_category(category_name):
    """Edit an existing category"""
    
    try:
        data = request.get_json()
        new_name = data['name'].strip()
        category_type = data.get('type', '').strip()
        
        if not new_name:
            return jsonify({'success': False, 'error': 'Category name required'}), 400
        
        if new_name == category_name:
            return jsonify({'success': True, 'message': 'No changes needed'})
        
        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()
        
        # Check if new name already exists
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE category = ?", (new_name,))
        if cursor.fetchone()[0] > 0:
            conn.close()
            return jsonify({'success': False, 'error': 'Category name already exists'}), 400
        
        # Update transactions
        cursor.execute("""
            UPDATE transactions 
            SET category = ?, updated_at = ?
            WHERE category = ?
        """, (new_name, datetime.utcnow().isoformat(), category_name))
        
        # Update budget templates
        cursor.execute("""
            UPDATE budget_templates 
            SET category = ?, updated_at = ?
            WHERE category = ?
        """, (new_name, datetime.utcnow().isoformat(), category_name))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Renamed category from {category_name} to {new_name}")
        return jsonify({'success': True, 'message': f'Category renamed successfully'})
        
    except Exception as e:
        print(f"❌ Error editing category: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/categories/subcategories/<subcategory_name>', methods=['PUT'])
def edit_subcategory(subcategory_name):
    """Edit an existing subcategory"""
    
    try:
        data = request.get_json()
        new_name = data['name'].strip()
        new_category = data.get('category', '').strip()
        
        if not new_name:
            return jsonify({'success': False, 'error': 'Subcategory name required'}), 400
        
        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()
        
        # Update transactions
        update_query = """
            UPDATE transactions 
            SET sub_category = ?, updated_at = ?
            WHERE sub_category = ?
        """
        params = [new_name, datetime.utcnow().isoformat(), subcategory_name]
        
        if new_category:
            update_query = """
                UPDATE transactions 
                SET sub_category = ?, category = ?, updated_at = ?
                WHERE sub_category = ?
            """
            params = [new_name, new_category, datetime.utcnow().isoformat(), subcategory_name]
        
        cursor.execute(update_query, params)
        
        conn.commit()
        conn.close()
        
        print(f"✅ Updated subcategory from {subcategory_name} to {new_name}")
        return jsonify({'success': True, 'message': f'Subcategory updated successfully'})
        
    except Exception as e:
        print(f"❌ Error editing subcategory: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/categories/owners/<owner_name>', methods=['PUT'])
def edit_owner(owner_name):
    """Edit an existing owner"""
    
    try:
        data = request.get_json()
        new_name = data['name'].strip()
        
        if not new_name:
            return jsonify({'success': False, 'error': 'Owner name required'}), 400
        
        if new_name == owner_name:
            return jsonify({'success': True, 'message': 'No changes needed'})
        
        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()
        
        # Update transactions
        cursor.execute("""
            UPDATE transactions 
            SET owner = ?, updated_at = ?
            WHERE owner = ?
        """, (new_name, datetime.utcnow().isoformat(), owner_name))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Renamed owner from {owner_name} to {new_name}")
        return jsonify({'success': True, 'message': f'Owner renamed successfully'})
        
    except Exception as e:
        print(f"❌ Error editing owner: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/categories/accounts/<account_name>', methods=['PUT'])
def edit_account(account_name):
    """Edit an existing account"""
    
    try:
        data = request.get_json()
        new_name = data['name'].strip()
        
        if not new_name:
            return jsonify({'success': False, 'error': 'Account name required'}), 400
        
        if new_name == account_name:
            return jsonify({'success': True, 'message': 'No changes needed'})
        
        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()
        
        # Update transactions
        cursor.execute("""
            UPDATE transactions 
            SET account_name = ?, updated_at = ?
            WHERE account_name = ?
        """, (new_name, datetime.utcnow().isoformat(), account_name))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Renamed account from {account_name} to {new_name}")
        return jsonify({'success': True, 'message': f'Account renamed successfully'})
        
    except Exception as e:
        print(f"❌ Error editing account: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
@api_bp.route('/categories/statistics')
def api_categories_statistics():
    """Get statistics for all category types"""

    try:
        year = request.args.get('year', datetime.now().year, type=int)
        month = request.args.get('month', 'all')
        owner = request.args.get('owner', 'all')

        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS custom_types (
                name TEXT PRIMARY KEY,
                created_at TEXT NOT NULL
            )
        """)

        # Build date filter
        date_filter = "strftime('%Y', date) = ?"
        params = [str(year)]

        if month != 'all':
            date_filter += " AND strftime('%m', date) = ?"
            params.append(f"{int(month):02d}")

        if owner != 'all':
            date_filter += " AND owner = ?"
            params.append(owner)

        # Get counts for each type
        stats = {}

        cursor.execute(f"""
            SELECT COUNT(DISTINCT category) FROM transactions
            WHERE {date_filter} AND COALESCE(is_active, 1) = 1
        """, params)
        stats['categories'] = cursor.fetchone()[0] or 0

        cursor.execute(f"""
            SELECT COUNT(DISTINCT sub_category) FROM transactions
            WHERE {date_filter} AND sub_category IS NOT NULL AND sub_category != '' AND COALESCE(is_active, 1) = 1
        """, params)
        stats['subcategories'] = cursor.fetchone()[0] or 0

        cursor.execute(f"""
            SELECT COUNT(DISTINCT owner) FROM transactions
            WHERE {date_filter} AND COALESCE(is_active, 1) = 1
        """, params)
        stats['owners'] = cursor.fetchone()[0] or 0

        cursor.execute(f"""
            SELECT COUNT(DISTINCT account_name) FROM transactions
            WHERE {date_filter} AND COALESCE(is_active, 1) = 1
        """, params)
        stats['accounts'] = cursor.fetchone()[0] or 0

        cursor.execute(f"""
            SELECT COUNT(DISTINCT type) FROM transactions
            WHERE {date_filter} AND COALESCE(is_active, 1) = 1
        """, params)
        txn_types = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(*) FROM custom_types")
        custom_types = cursor.fetchone()[0] or 0
        stats['types'] = max(txn_types, custom_types)

        conn.close()

        print(f"📊 Statistics for {year}-{month} owner={owner}: {stats}")
        return jsonify(stats)

    except Exception as e:
        print(f"❌ Error getting statistics: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'categories': 0, 'subcategories': 0, 'owners': 0, 'accounts': 0}), 500

@api_bp.route('/accounts/list')
def get_accounts_list():
    """Get all accounts (regular + debt accounts) for transaction form dropdown"""

    try:
        print("💳 Getting accounts list for transaction form")

        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()

        accounts_list = []

        # Get regular accounts from accounts table
        cursor.execute("""
            SELECT id, name, account_type, is_debt, debt_account_id
            FROM accounts
            WHERE is_active = 1
            ORDER BY name
        """)

        regular_accounts = cursor.fetchall()
        for account in regular_accounts:
            accounts_list.append({
                'id': account[0],
                'name': account[1],
                'account_type': account[2],
                'is_debt': bool(account[3]),
                'debt_account_id': account[4]
            })

        # Get debt accounts and add them
        cursor.execute("""
            SELECT id, name, debt_type
            FROM debt_accounts
            WHERE is_active = 1
            ORDER BY name
        """)

        debt_accounts = cursor.fetchall()
        for debt in debt_accounts:
            # Check if this debt account is already in accounts table
            existing = next((a for a in accounts_list if a.get('debt_account_id') == debt[0]), None)
            if not existing:
                # Add debt account
                accounts_list.append({
                    'id': f"debt_{debt[0]}",  # Prefix with debt_ to distinguish
                    'name': debt[1],
                    'account_type': debt[2],  # Credit Card, Car Loan, etc.
                    'is_debt': True,
                    'debt_account_id': debt[0]
                })

        conn.close()

        # Sort by name
        accounts_list.sort(key=lambda x: x['name'])

        print(f"💳 Returning {len(accounts_list)} accounts")
        return jsonify(accounts_list)

    except Exception as e:
        print(f"❌ Error getting accounts list: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([]), 500

@api_bp.route('/transactions/by-subcategory')
def get_transactions_by_subcategory():
    """Get transactions for a specific category/subcategory and month for budget drill-down.
    If subcategory is not provided, returns all transactions for the category."""

    try:
        # Get parameters
        category = request.args.get('category')
        subcategory = request.args.get('subcategory')  # Optional - if not provided, fetch all for category
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        owner = request.args.get('owner', 'all')

        # Validate required parameters (subcategory is now optional)
        if not all([category, year, month]):
            return jsonify({'error': 'Missing required parameters: category, year, month'}), 400

        if subcategory:
            print(f"📊 Fetching transactions: {category} > {subcategory} for {year}-{month:02d}")
        else:
            print(f"📊 Fetching all transactions for category: {category} for {year}-{month:02d}")

        conn = sqlite3.connect('data/personal_finance.db')
        conn.row_factory = sqlite3.Row

        # Build query - subcategory filter is optional
        query = """
        SELECT
            id,
            date,
            description,
            amount,
            account_name,
            owner,
            type,
            sub_category
        FROM transactions
        WHERE category = ?
        AND strftime('%Y', date) = ?
        AND strftime('%m', date) = ?
        AND COALESCE(is_active, 1) = 1
        """
        params = [category, str(year), f"{month:02d}"]

        # Add subcategory filter only if provided
        if subcategory:
            query += " AND sub_category = ?"
            params.append(subcategory)

        # Add owner filter if not 'all'
        if owner != 'all':
            query += " AND owner = ?"
            params.append(owner)

        # Order by date descending (most recent first)
        query += " ORDER BY date DESC, created_at DESC"

        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Convert to list of dictionaries
        transactions = []
        for row in rows:
            transactions.append({
                'id': row['id'],
                'date': row['date'],
                'description': row['description'],
                'amount': float(row['amount']),
                'account_name': row['account_name'] or 'N/A',
                'owner': row['owner'] or 'Unknown',
                'type': row['type'] or '',
                'sub_category': row['sub_category'] or ''
            })

        conn.close()

        print(f"✅ Found {len(transactions)} transactions")

        return jsonify({
            'transactions': transactions,
            'count': len(transactions),
            'category': category,
            'subcategory': subcategory,
            'month': f"{year}-{month:02d}"
        })

    except Exception as e:
        print(f"❌ Error fetching transactions by subcategory: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------------------------
# Flutter-facing endpoints (JSON only)
# All routes below are protected by the api_bp.before_request auth hook.
# ---------------------------------------------------------------------------

@api_bp.route('/transactions', methods=['GET'])
def api_transactions_list():
    """Paginated transaction list for the Flutter mobile app.

    Query params:
      page       (int, default 1)
      per_page   (int, default 50, max 200)
      owner      (str, default 'all')
      year       (int)
      month      (int)
      category   (str)
    """
    try:
        page = max(1, request.args.get('page', 1, type=int))
        per_page = min(200, max(1, request.args.get('per_page', 50, type=int)))
        offset = (page - 1) * per_page
        owner = request.args.get('owner', 'all')
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        category = request.args.get('category', '')

        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()

        filters = ["COALESCE(is_active, 1) = 1"]
        params = []

        if owner and owner != 'all':
            filters.append("owner = ?")
            params.append(owner)
        if year:
            filters.append("strftime('%Y', date) = ?")
            params.append(str(year))
        if month:
            filters.append("strftime('%m', date) = ?")
            params.append(f"{month:02d}")
        if category:
            filters.append("category = ?")
            params.append(category)

        where = "WHERE " + " AND ".join(filters)

        cursor.execute(f"SELECT COUNT(*) FROM transactions {where}", params)
        total = cursor.fetchone()[0]

        cursor.execute(
            f"""SELECT id, account_name, date, description, amount,
                       sub_category, category, type, owner, is_business
                FROM transactions {where}
                ORDER BY date DESC, id DESC
                LIMIT ? OFFSET ?""",
            params + [per_page, offset]
        )
        rows = cursor.fetchall()
        conn.close()

        transactions = [
            {
                'id': r[0], 'account_name': r[1], 'date': r[2],
                'description': r[3], 'amount': float(r[4]) if r[4] is not None else 0.0,
                'sub_category': r[5], 'category': r[6],
                'type': r[7], 'owner': r[8], 'is_business': bool(r[9])
            }
            for r in rows
        ]

        return jsonify({
            'transactions': transactions,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page,
            'has_next': offset + per_page < total,
            'has_prev': page > 1
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/transactions', methods=['POST'])
def api_add_transaction():
    """Add a transaction from the Flutter mobile app (JSON body).

    Required fields: account_name, date (YYYY-MM-DD), description,
                     amount, category, type, owner
    Optional fields: sub_category, is_business (bool, default false)
    """
    try:
        data = request.get_json(force=True, silent=True) or {}

        required = ['date', 'description', 'amount', 'category', 'type', 'owner']
        for field in required:
            if not data.get(field) and data.get(field) != 0:
                return jsonify({'success': False, 'error': f'{field} is required'}), 400

        try:
            amount = float(data['amount'])
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'Invalid amount'}), 400

        if amount == 0:
            return jsonify({'success': False, 'error': 'Amount cannot be zero'}), 400

        from datetime import datetime as dt
        try:
            dt.strptime(data['date'], '%Y-%m-%d')
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid date format, expected YYYY-MM-DD'}), 400

        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO transactions
               (account_name, date, description, amount, sub_category, category, type, owner, is_business, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
            (
                data['account_name'],
                data['date'],
                data['description'],
                amount,
                data.get('sub_category', ''),
                data['category'],
                data['type'],
                data['owner'],
                1 if data.get('is_business', False) else 0,
            )
        )
        transaction_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'id': transaction_id}), 201

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/login', methods=['POST'])
def api_login():
    """Authenticate with dashboard credentials and receive the Bearer token.

    Body: {"username": "...", "password": "..."}
    Returns: {"success": true, "token": "<API_SECRET_KEY>"}

    This endpoint is intentionally exempt from Bearer token auth
    (see auth.py _API_PUBLIC_ENDPOINTS) so the mobile app can call it
    before it has a token.
    """
    import hmac as _hmac
    data = request.get_json(force=True, silent=True) or {}
    username = data.get('username', '')
    password = data.get('password', '')

    expected_user = current_app.config.get('DASHBOARD_USERNAME', '')
    expected_pass = current_app.config.get('DASHBOARD_PASSWORD', '')

    # Local dev mode — credentials not configured, allow through
    if not expected_user:
        token = current_app.config.get('API_SECRET_KEY', '')
        return jsonify({'success': True, 'token': token})

    user_ok = _hmac.compare_digest(username, expected_user)
    pass_ok = _hmac.compare_digest(password, expected_pass)

    if user_ok and pass_ok:
        token = current_app.config.get('API_SECRET_KEY', '')
        return jsonify({'success': True, 'token': token})

    return jsonify({'success': False, 'error': 'Invalid username or password'}), 401


@api_bp.route('/debts', methods=['GET'])
def api_debts_list():
    """Debt accounts list for the Flutter mobile app.

    Query params:
      show_paid_off  (bool string, default 'false')
    """
    try:
        show_paid_off = request.args.get('show_paid_off', 'false').lower() == 'true'

        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()

        if show_paid_off:
            cursor.execute(
                "SELECT * FROM debt_accounts ORDER BY is_active DESC, current_balance DESC"
            )
        else:
            cursor.execute(
                "SELECT * FROM debt_accounts WHERE is_active = 1 ORDER BY current_balance DESC"
            )

        rows = cursor.fetchall()
        columns = [d[0] for d in cursor.description]
        conn.close()

        debts = []
        for row in rows:
            debt = dict(zip(columns, row))
            for key in ('current_balance', 'original_balance', 'interest_rate', 'minimum_payment'):
                if debt.get(key) is not None:
                    debt[key] = float(debt[key])
            debt['is_active'] = bool(debt.get('is_active', 1))
            debts.append(debt)

        active_debts = [d for d in debts if d['is_active']]
        total_debt = sum(d['current_balance'] for d in active_debts)
        total_minimum = sum(d.get('minimum_payment') or 0.0 for d in active_debts)

        return jsonify({
            'debts': debts,
            'total_debt': total_debt,
            'total_minimum_payments': total_minimum,
            'active_count': len(active_debts)
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500