from flask import Blueprint, render_template, request, jsonify
from datetime import datetime, timedelta
import pandas as pd
import sqlite3

# Create the analytics blueprint
analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')

@analytics_bp.route('/')
def analytics_dashboard():
    """Main analytics dashboard page"""
    
    print("📊 Loading analytics dashboard...")
    
    try:
        # Get available filter options from database
        conn = sqlite3.connect('data/personal_finance.db')
        
        # Get available years
        years_df = pd.read_sql_query("""
            SELECT DISTINCT strftime('%Y', date) as year 
            FROM transactions 
            WHERE COALESCE(is_active, 1) = 1
            ORDER BY year DESC
        """, conn)
        available_years = [int(year) for year in years_df['year'].tolist()]
        
        # Get available owners
        owners_df = pd.read_sql_query("""
            SELECT DISTINCT owner 
            FROM transactions 
            WHERE COALESCE(is_active, 1) = 1
            ORDER BY owner
        """, conn)
        available_owners = [owner for owner in owners_df['owner'].tolist()]
        
        # Get available categories
        categories_df = pd.read_sql_query("""
            SELECT DISTINCT category 
            FROM transactions 
            WHERE COALESCE(is_active, 1) = 1
            ORDER BY category
        """, conn)
        available_categories = [category for category in categories_df['category'].tolist()]
        
        # Get available accounts
        accounts_df = pd.read_sql_query("""
            SELECT DISTINCT account_name 
            FROM transactions 
            WHERE COALESCE(is_active, 1) = 1
            ORDER BY account_name
        """, conn)
        available_accounts = [account for account in accounts_df['account_name'].tolist()]
        
        # Get available subcategories
        subcategories_df = pd.read_sql_query("""
            SELECT DISTINCT sub_category, category 
            FROM transactions 
            WHERE COALESCE(is_active, 1) = 1 
            AND sub_category IS NOT NULL 
            AND sub_category != ''
            ORDER BY category, sub_category
        """, conn)
        available_subcategories = [{'subcategory': row['sub_category'], 'category': row['category']} 
                                 for _, row in subcategories_df.iterrows()]
        
        conn.close()
        
        # Default date range (last 6 months)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)
        
        return render_template('analytics.html',
                             available_years=available_years,
                             available_owners=available_owners,
                             available_categories=available_categories,
                             available_accounts=available_accounts,
                             available_subcategories=available_subcategories,
                             default_start_date=start_date.strftime('%Y-%m-%d'),
                             default_end_date=end_date.strftime('%Y-%m-%d'))
                             
    except Exception as e:
        print(f"❌ Error loading analytics dashboard: {e}")
        import traceback
        traceback.print_exc()
        
        # Return with empty defaults on error
        return render_template('analytics/analytics.html',
                             available_years=[2023, 2024, 2025],
                             available_owners=['Cata', 'Suricata', 'Cacas'],
                             available_categories=[],
                             available_accounts=[],
                             default_start_date=(datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d'),
                             default_end_date=datetime.now().strftime('%Y-%m-%d'),
                             error=str(e))

@analytics_bp.route('/api/subcategories')
def api_subcategories():
    """Get subcategories for selected categories"""
    try:
        categories = request.args.getlist('categories')
        
        conn = sqlite3.connect('data/personal_finance.db')
        
        # Build query based on selected categories
        if categories and 'all' not in categories:
            placeholders = ','.join(['?' for _ in categories])
            query = f"""
                SELECT DISTINCT sub_category, category 
                FROM transactions 
                WHERE COALESCE(is_active, 1) = 1 
                AND sub_category IS NOT NULL 
                AND sub_category != ''
                AND category IN ({placeholders})
                ORDER BY category, sub_category
            """
            params = categories
        else:
            # Return all subcategories if no specific categories selected
            query = """
                SELECT DISTINCT sub_category, category 
                FROM transactions 
                WHERE COALESCE(is_active, 1) = 1 
                AND sub_category IS NOT NULL 
                AND sub_category != ''
                ORDER BY category, sub_category
            """
            params = []
        
        subcategories_df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        result = [{'subcategory': row['sub_category'], 'category': row['category']} 
                 for _, row in subcategories_df.iterrows()]
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Error in subcategories API: {e}")
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/api/subcategory_breakdown')
def api_subcategory_breakdown():
    """Get subcategory breakdown data with filters"""
    
    try:
        # Get filter parameters (same as category_breakdown)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        owners = request.args.getlist('owners')
        categories = request.args.getlist('categories')
        subcategories = request.args.getlist('subcategories')
        accounts = request.args.getlist('accounts')
        types = request.args.getlist('types')
        min_amount = request.args.get('min_amount', type=float)
        max_amount = request.args.get('max_amount', type=float)
        
        print(f"🔍 API: Getting subcategory breakdown")
        
        conn = sqlite3.connect('data/personal_finance.db')
        
        # Build filters
        filters = []
        params = []
        
        if start_date:
            filters.append("date >= ?")
            params.append(start_date)
        if end_date:
            filters.append("date <= ?")
            params.append(end_date)
        if owners and 'all' not in owners:
            placeholders = ','.join(['?' for _ in owners])
            filters.append(f"owner IN ({placeholders})")
            params.extend(owners)
        if categories and 'all' not in categories:
            placeholders = ','.join(['?' for _ in categories])
            filters.append(f"category IN ({placeholders})")
            params.extend(categories)
        if subcategories and 'all' not in subcategories:
            placeholders = ','.join(['?' for _ in subcategories])
            filters.append(f"sub_category IN ({placeholders})")
            params.extend(subcategories)
        if accounts and 'all' not in accounts:
            placeholders = ','.join(['?' for _ in accounts])
            filters.append(f"account_name IN ({placeholders})")
            params.extend(accounts)
        if types and 'all' not in types:
            placeholders = ','.join(['?' for _ in types])
            filters.append(f"type IN ({placeholders})")
            params.extend(types)
        if min_amount is not None:
            filters.append("amount >= ?")
            params.append(min_amount)
        if max_amount is not None:
            filters.append("amount <= ?")
            params.append(max_amount)
        
        filters.append("COALESCE(is_active, 1) = 1")
        filters.append("sub_category IS NOT NULL")
        filters.append("sub_category != ''")
        where_clause = "WHERE " + " AND ".join(filters)
        
        # Subcategory breakdown query
        breakdown_query = f"""
        SELECT 
            sub_category,
            category,
            SUM(amount) as total,
            COUNT(*) as transaction_count,
            AVG(amount) as avg_amount
        FROM transactions 
        {where_clause}
        GROUP BY sub_category, category
        ORDER BY total DESC
        LIMIT 10
        """
        
        breakdown_df = pd.read_sql_query(breakdown_query, conn, params=params)
        conn.close()
        
        result = []
        for _, row in breakdown_df.iterrows():
            result.append({
                'subcategory': row['sub_category'],
                'category': row['category'],
                'total': float(row['total']),
                'transaction_count': int(row['transaction_count']),
                'avg_amount': float(row['avg_amount'])
            })
        
        print(f"🔍 Returning breakdown for {len(result)} subcategories")
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Error in subcategory breakdown API: {e}")
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/api/spending_trends')
def api_spending_trends():
    """Get spending trends data with filters"""
    
    try:
        # Get filter parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        owners = request.args.getlist('owners')
        categories = request.args.getlist('categories')
        subcategories = request.args.getlist('subcategories')
        accounts = request.args.getlist('accounts')
        types = request.args.getlist('types')
        min_amount = request.args.get('min_amount', type=float)
        max_amount = request.args.get('max_amount', type=float)
        
        print(f"📈 API: Getting spending trends from {start_date} to {end_date}")
        
        conn = sqlite3.connect('data/personal_finance.db')
        
        # Build dynamic query with filters
        filters = []
        params = []
        
        # Date range filter
        if start_date:
            filters.append("date >= ?")
            params.append(start_date)
        if end_date:
            filters.append("date <= ?")
            params.append(end_date)
        
        # Owner filter
        if owners and 'all' not in owners:
            placeholders = ','.join(['?' for _ in owners])
            filters.append(f"owner IN ({placeholders})")
            params.extend(owners)
        
        # Category filter
        if categories and 'all' not in categories:
            placeholders = ','.join(['?' for _ in categories])
            filters.append(f"category IN ({placeholders})")
            params.extend(categories)
        
        # Subcategory filter
        if subcategories and 'all' not in subcategories:
            placeholders = ','.join(['?' for _ in subcategories])
            filters.append(f"sub_category IN ({placeholders})")
            params.extend(subcategories)
        
        # Account filter
        if accounts and 'all' not in accounts:
            placeholders = ','.join(['?' for _ in accounts])
            filters.append(f"account_name IN ({placeholders})")
            params.extend(accounts)
        
        # Type filter
        if types and 'all' not in types:
            placeholders = ','.join(['?' for _ in types])
            filters.append(f"type IN ({placeholders})")
            params.extend(types)
        
        # Amount range filter
        if min_amount is not None:
            filters.append("amount >= ?")
            params.append(min_amount)
        if max_amount is not None:
            filters.append("amount <= ?")
            params.append(max_amount)
        
        # Always filter for active transactions
        filters.append("COALESCE(is_active, 1) = 1")
        
        where_clause = "WHERE " + " AND ".join(filters) if filters else ""
        
        # Spending trends query (monthly grouping)
        trends_query = f"""
        SELECT 
            strftime('%Y-%m', date) as month,
            type,
            SUM(amount) as total,
            COUNT(*) as transaction_count
        FROM transactions 
        {where_clause}
        GROUP BY strftime('%Y-%m', date), type
        ORDER BY month, type
        """
        
        trends_df = pd.read_sql_query(trends_query, conn, params=params)
        conn.close()
        
        # Process data for chart
        result = {}
        for _, row in trends_df.iterrows():
            month = row['month']
            if month not in result:
                result[month] = {'month': month}
            result[month][row['type']] = {
                'total': float(row['total']),
                'count': int(row['transaction_count'])
            }
        
        # Convert to list and sort
        result_list = list(result.values())
        result_list.sort(key=lambda x: x['month'])
        
        print(f"📈 Returning trends for {len(result_list)} months")
        return jsonify(result_list)
        
    except Exception as e:
        print(f"❌ Error in spending trends API: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/api/category_breakdown')
def api_category_breakdown():
    """Get category breakdown data with filters"""
    
    try:
        # Get filter parameters (same as spending_trends)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        owners = request.args.getlist('owners')
        categories = request.args.getlist('categories')
        subcategories = request.args.getlist('subcategories')
        accounts = request.args.getlist('accounts')
        types = request.args.getlist('types')
        min_amount = request.args.get('min_amount', type=float)
        max_amount = request.args.get('max_amount', type=float)
        
        print(f"🥧 API: Getting category breakdown")
        
        conn = sqlite3.connect('data/personal_finance.db')
        
        # Build same filters as trends
        filters = []
        params = []
        
        if start_date:
            filters.append("date >= ?")
            params.append(start_date)
        if end_date:
            filters.append("date <= ?")
            params.append(end_date)
        if owners and 'all' not in owners:
            placeholders = ','.join(['?' for _ in owners])
            filters.append(f"owner IN ({placeholders})")
            params.extend(owners)
        if categories and 'all' not in categories:
            placeholders = ','.join(['?' for _ in categories])
            filters.append(f"category IN ({placeholders})")
            params.extend(categories)
        if subcategories and 'all' not in subcategories:
            placeholders = ','.join(['?' for _ in subcategories])
            filters.append(f"sub_category IN ({placeholders})")
            params.extend(subcategories)
        if accounts and 'all' not in accounts:
            placeholders = ','.join(['?' for _ in accounts])
            filters.append(f"account_name IN ({placeholders})")
            params.extend(accounts)
        if types and 'all' not in types:
            placeholders = ','.join(['?' for _ in types])
            filters.append(f"type IN ({placeholders})")
            params.extend(types)
        if min_amount is not None:
            filters.append("amount >= ?")
            params.append(min_amount)
        if max_amount is not None:
            filters.append("amount <= ?")
            params.append(max_amount)
        
        filters.append("COALESCE(is_active, 1) = 1")
        where_clause = "WHERE " + " AND ".join(filters)
        
        # Category breakdown query
        breakdown_query = f"""
        SELECT 
            category,
            SUM(amount) as total,
            COUNT(*) as transaction_count,
            AVG(amount) as avg_amount
        FROM transactions 
        {where_clause}
        GROUP BY category
        ORDER BY total DESC
        """
        
        breakdown_df = pd.read_sql_query(breakdown_query, conn, params=params)
        conn.close()
        
        # Calculate percentages
        total_amount = breakdown_df['total'].sum()
        
        result = []
        for _, row in breakdown_df.iterrows():
            percentage = (float(row['total']) / total_amount * 100) if total_amount > 0 else 0
            result.append({
                'category': row['category'],
                'total': float(row['total']),
                'transaction_count': int(row['transaction_count']),
                'avg_amount': float(row['avg_amount']),
                'percentage': percentage
            })
        
        print(f"🥧 Returning breakdown for {len(result)} categories")
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Error in category breakdown API: {e}")
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/api/owner_comparison')
def api_owner_comparison():
    """Get owner comparison data with filters"""
    
    try:
        # Get filter parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        owners = request.args.getlist('owners')
        categories = request.args.getlist('categories')
        subcategories = request.args.getlist('subcategories')
        accounts = request.args.getlist('accounts')
        types = request.args.getlist('types')
        min_amount = request.args.get('min_amount', type=float)
        max_amount = request.args.get('max_amount', type=float)
        
        print(f"👥 API: Getting owner comparison")
        
        conn = sqlite3.connect('data/personal_finance.db')
        
        # Build filters
        filters = []
        params = []
        
        if start_date:
            filters.append("date >= ?")
            params.append(start_date)
        if end_date:
            filters.append("date <= ?")
            params.append(end_date)
        if owners and 'all' not in owners:
            placeholders = ','.join(['?' for _ in owners])
            filters.append(f"owner IN ({placeholders})")
            params.extend(owners)
        if categories and 'all' not in categories:
            placeholders = ','.join(['?' for _ in categories])
            filters.append(f"category IN ({placeholders})")
            params.extend(categories)
        if subcategories and 'all' not in subcategories:
            placeholders = ','.join(['?' for _ in subcategories])
            filters.append(f"sub_category IN ({placeholders})")
            params.extend(subcategories)
        if accounts and 'all' not in accounts:
            placeholders = ','.join(['?' for _ in accounts])
            filters.append(f"account_name IN ({placeholders})")
            params.extend(accounts)
        if types and 'all' not in types:
            placeholders = ','.join(['?' for _ in types])
            filters.append(f"type IN ({placeholders})")
            params.extend(types)
        if min_amount is not None:
            filters.append("amount >= ?")
            params.append(min_amount)
        if max_amount is not None:
            filters.append("amount <= ?")
            params.append(max_amount)
        
        filters.append("COALESCE(is_active, 1) = 1")
        where_clause = "WHERE " + " AND ".join(filters)
        
        # Owner comparison query
        comparison_query = f"""
        SELECT 
            owner,
            type,
            SUM(amount) as total,
            COUNT(*) as transaction_count,
            AVG(amount) as avg_amount
        FROM transactions 
        {where_clause}
        GROUP BY owner, type
        ORDER BY owner, total DESC
        """
        
        comparison_df = pd.read_sql_query(comparison_query, conn, params=params)
        conn.close()
        
        # Group by owner
        result = {}
        for _, row in comparison_df.iterrows():
            owner = row['owner']
            if owner not in result:
                result[owner] = {
                    'owner': owner,
                    'total': 0,
                    'transaction_count': 0,
                    'types': {}
                }
            
            result[owner]['total'] += float(row['total'])
            result[owner]['transaction_count'] += int(row['transaction_count'])
            result[owner]['types'][row['type']] = {
                'total': float(row['total']),
                'count': int(row['transaction_count']),
                'avg': float(row['avg_amount'])
            }
        
        # Convert to list
        result_list = list(result.values())
        result_list.sort(key=lambda x: x['total'], reverse=True)
        
        print(f"👥 Returning comparison for {len(result_list)} owners")
        return jsonify(result_list)
        
    except Exception as e:
        print(f"❌ Error in owner comparison API: {e}")
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/api/filtered_transactions')
def api_filtered_transactions():
    """Return filtered transactions for analytics summary table"""
    try:
        # Get filter parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        owners = request.args.getlist('owners')
        categories = request.args.getlist('categories')
        subcategories = request.args.getlist('subcategories')
        accounts = request.args.getlist('accounts')
        types = request.args.getlist('types')
        min_amount = request.args.get('min_amount', type=float)
        max_amount = request.args.get('max_amount', type=float)

        conn = sqlite3.connect('data/personal_finance.db')

        # Build dynamic query with filters
        filters = []
        params = []
        if start_date:
            filters.append("date >= ?")
            params.append(start_date)
        if end_date:
            filters.append("date <= ?")
            params.append(end_date)
        if owners and 'all' not in owners:
            placeholders = ','.join(['?' for _ in owners])
            filters.append(f"owner IN ({placeholders})")
            params.extend(owners)
        if categories and 'all' not in categories:
            placeholders = ','.join(['?' for _ in categories])
            filters.append(f"category IN ({placeholders})")
            params.extend(categories)
        if subcategories and 'all' not in subcategories:
            placeholders = ','.join(['?' for _ in subcategories])
            filters.append(f"sub_category IN ({placeholders})")
            params.extend(subcategories)
        if accounts and 'all' not in accounts:
            placeholders = ','.join(['?' for _ in accounts])
            filters.append(f"account_name IN ({placeholders})")
            params.extend(accounts)
        if types and 'all' not in types:
            placeholders = ','.join(['?' for _ in types])
            filters.append(f"type IN ({placeholders})")
            params.extend(types)
        if min_amount is not None:
            filters.append("amount >= ?")
            params.append(min_amount)
        if max_amount is not None:
            filters.append("amount <= ?")
            params.append(max_amount)
        filters.append("COALESCE(is_active, 1) = 1")
        where_clause = "WHERE " + " AND ".join(filters) if filters else ""
        query = f"""
        SELECT date, description, amount, category, sub_category, owner, account_name, type
        FROM transactions
        {where_clause}
        ORDER BY date DESC
        LIMIT 100
        """
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        result = df.to_dict(orient='records')
        return jsonify(result)
    except Exception as e:
        print(f"❌ Error in filtered transactions API: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

def get_monthly_spending_matrix(conn):
    import pandas as pd
    # Query: total spending per month per year
    query = '''
        SELECT strftime('%Y', date) as year, strftime('%m', date) as month, SUM(amount) as total
        FROM transactions
        WHERE amount > 0 AND COALESCE(is_active, 1) = 1
        GROUP BY year, month
        ORDER BY year, month
    '''
    df = pd.read_sql_query(query, conn)
    if df.empty:
        return {}
    # Pivot to year as rows, months as columns
    pivot = df.pivot(index='year', columns='month', values='total').fillna(0)
    # Calculate percent change from previous year for each month
    pct_change = pivot.pct_change().fillna(0) * 100
    # Build result: {year: {month: {total, pct_change}}}
    result = {}
    for year in pivot.index:
        result[year] = {}
        for month in pivot.columns:
            total = float(pivot.loc[year, month])
            pct = float(pct_change.loc[year, month]) if year != pivot.index[0] else None
            result[year][month] = {'total': total, 'pct_change': pct}
    return result

@analytics_bp.route('/api/monthly_spending_matrix')
def api_monthly_spending_matrix():
    """Return a matrix of total spending per month per year, with percent change from previous year"""
    import sqlite3
    try:
        conn = sqlite3.connect('data/personal_finance.db')
        matrix = get_monthly_spending_matrix(conn)
        conn.close()
        return jsonify(matrix)
    except Exception as e:
        print(f"❌ Error in monthly spending matrix API: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500