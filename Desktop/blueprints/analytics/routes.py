from flask import Blueprint, render_template, request, jsonify
from datetime import datetime, timedelta
import pandas as pd
from models import db
from sqlalchemy import text
from utils import uid_clause, local_now

analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')


def _df(conn, sql, params=None):
    return pd.read_sql_query(text(sql), conn, params=params or {})


def _year_expr():
    """Return a SQL fragment that extracts the year as an integer, compatible with both Postgres and SQLite."""
    if db.engine.dialect.name == 'sqlite':
        return "CAST(strftime('%Y', date) AS INTEGER)"
    return "EXTRACT(YEAR FROM date)::integer"


def _month_expr():
    """Return a SQL fragment that extracts the month as an integer, compatible with both Postgres and SQLite."""
    if db.engine.dialect.name == 'sqlite':
        return "CAST(strftime('%m', date) AS INTEGER)"
    return "EXTRACT(MONTH FROM date)::integer"


def _build_analytics_filters(args):
    """Build WHERE clause and named params dict from analytics request args."""
    filters = []
    params = {}

    def _in(field, values, prefix):
        keys = {f'{prefix}_{i}': v for i, v in enumerate(values)}
        params.update(keys)
        filters.append(f"{field} IN ({', '.join(f':{k}' for k in keys)})")

    start_date = args.get('start_date')
    end_date = args.get('end_date')
    owners = args.getlist('owners')
    categories = args.getlist('categories')
    subcategories = args.getlist('subcategories')
    accounts = args.getlist('accounts')
    types = args.getlist('types')
    min_amount = args.get('min_amount', type=float)
    max_amount = args.get('max_amount', type=float)

    if start_date:
        filters.append("date >= :start_date")
        params['start_date'] = start_date
    if end_date:
        filters.append("date <= :end_date")
        params['end_date'] = end_date
    if owners and 'all' not in owners:
        _in('owner', owners, 'own')
    if categories and 'all' not in categories:
        _in('category', categories, 'cat')
    if subcategories and 'all' not in subcategories:
        _in('sub_category', subcategories, 'sub')
    if accounts and 'all' not in accounts:
        _in('account_name', accounts, 'acc')
    if types and 'all' not in types:
        _in('type', types, 'typ')
    if min_amount is not None:
        filters.append("amount >= :min_amount")
        params['min_amount'] = min_amount
    if max_amount is not None:
        filters.append("amount <= :max_amount")
        params['max_amount'] = max_amount

    filters.append("COALESCE(is_active, true) = true")
    uid_sql, uid_p = uid_clause()
    if uid_sql:
        filters.append("user_id = :_uid")
        params.update(uid_p)
    return "WHERE " + " AND ".join(filters), params


@analytics_bp.route('/')
def analytics_dashboard():
    """Main analytics dashboard page"""
    print("📊 Loading analytics dashboard...")
    try:
        uid_sql, uid_p = uid_clause()
        with db.engine.connect() as conn:
            years_df = _df(conn, f"""
                SELECT DISTINCT {_year_expr()} AS year
                FROM transactions WHERE COALESCE(is_active, true) = true {uid_sql} ORDER BY year DESC
            """, uid_p)
            available_years = [int(y) for y in years_df['year'].tolist() if y is not None]

            owners_df = _df(conn, f"""
                SELECT DISTINCT owner FROM transactions
                WHERE COALESCE(is_active, true) = true {uid_sql} ORDER BY owner
            """, uid_p)
            available_owners = [o for o in owners_df['owner'].tolist() if o is not None]

            categories_df = _df(conn, f"""
                SELECT DISTINCT category FROM transactions
                WHERE COALESCE(is_active, true) = true {uid_sql} ORDER BY category
            """, uid_p)
            available_categories = [c for c in categories_df['category'].tolist() if c is not None]

            accounts_df = _df(conn, f"""
                SELECT DISTINCT account_name FROM transactions
                WHERE COALESCE(is_active, true) = true {uid_sql} ORDER BY account_name
            """, uid_p)
            available_accounts = [a for a in accounts_df['account_name'].tolist() if a is not None]

            subcategories_df = _df(conn, f"""
                SELECT DISTINCT sub_category, category FROM transactions
                WHERE COALESCE(is_active, true) = true {uid_sql}
                AND sub_category IS NOT NULL AND sub_category != ''
                ORDER BY category, sub_category
            """, uid_p)
            available_subcategories = [
                {'subcategory': row['sub_category'], 'category': row['category']}
                for _, row in subcategories_df.iterrows()
            ]

            types_df = _df(conn, f"""
                SELECT DISTINCT type FROM transactions
                WHERE COALESCE(is_active, true) = true {uid_sql} AND type IS NOT NULL AND type != ''
                ORDER BY type
            """, uid_p)
            txn_types = types_df['type'].tolist()

        _defaults = ['Needs', 'Wants', 'Savings', 'Business']
        seen = set(_defaults)
        available_types = _defaults.copy()
        for t in txn_types:
            if t not in seen:
                seen.add(t)
                available_types.append(t)

        end_date = local_now()
        start_date = end_date - timedelta(days=180)

        return render_template('analytics.html',
                             available_years=available_years,
                             available_owners=available_owners,
                             available_categories=available_categories,
                             available_accounts=available_accounts,
                             available_subcategories=available_subcategories,
                             available_types=available_types,
                             default_start_date=start_date.strftime('%Y-%m-%d'),
                             default_end_date=end_date.strftime('%Y-%m-%d'))

    except Exception as e:
        print(f"❌ Error loading analytics dashboard: {e}")
        import traceback
        traceback.print_exc()
        return render_template('analytics.html',
                             available_years=[local_now().year - 1, local_now().year],
                             available_owners=[],
                             available_categories=[],
                             available_accounts=[],
                             available_subcategories=[],
                             available_types=['Needs', 'Wants', 'Savings', 'Business'],
                             default_start_date=(local_now() - timedelta(days=180)).strftime('%Y-%m-%d'),
                             default_end_date=local_now().strftime('%Y-%m-%d'),
                             error=str(e))


@analytics_bp.route('/api/subcategories')
def api_subcategories():
    """Get subcategories for selected categories"""
    try:
        categories = request.args.getlist('categories')
        uid_sql, uid_p = uid_clause()
        with db.engine.connect() as conn:
            if categories and 'all' not in categories:
                cat_params = {f'cat_{i}': v for i, v in enumerate(categories)}
                placeholders = ', '.join(f':{k}' for k in cat_params)
                df = _df(conn, f"""
                    SELECT DISTINCT sub_category, category FROM transactions
                    WHERE COALESCE(is_active, true) = true {uid_sql}
                    AND sub_category IS NOT NULL AND sub_category != ''
                    AND category IN ({placeholders})
                    ORDER BY category, sub_category
                """, {**cat_params, **uid_p})
            else:
                df = _df(conn, f"""
                    SELECT DISTINCT sub_category, category FROM transactions
                    WHERE COALESCE(is_active, true) = true {uid_sql}
                    AND sub_category IS NOT NULL AND sub_category != ''
                    ORDER BY category, sub_category
                """, uid_p)
        result = [{'subcategory': row['sub_category'], 'category': row['category']}
                  for _, row in df.iterrows()]
        return jsonify(result)
    except Exception as e:
        print(f"❌ Error in subcategories API: {e}")
        return jsonify({'error': str(e)}), 500


@analytics_bp.route('/api/subcategory_breakdown')
def api_subcategory_breakdown():
    """Get subcategory breakdown data with filters"""
    try:
        print("🔍 API: Getting subcategory breakdown")
        where_clause, params = _build_analytics_filters(request.args)
        with db.engine.connect() as conn:
            df = _df(conn, f"""
                SELECT sub_category, category,
                       SUM(amount) as total,
                       COUNT(*) as transaction_count,
                       AVG(amount) as avg_amount
                FROM transactions
                {where_clause}
                AND sub_category IS NOT NULL AND sub_category != ''
                GROUP BY sub_category, category
                ORDER BY total DESC
                LIMIT 10
            """, params)

        result = [
            {
                'subcategory': row['sub_category'],
                'category': row['category'],
                'total': float(row['total']),
                'transaction_count': int(row['transaction_count']),
                'avg_amount': float(row['avg_amount'])
            }
            for _, row in df.iterrows()
        ]
        print(f"🔍 Returning breakdown for {len(result)} subcategories")
        return jsonify(result)
    except Exception as e:
        print(f"❌ Error in subcategory breakdown API: {e}")
        return jsonify({'error': str(e)}), 500


@analytics_bp.route('/api/spending_trends')
def api_spending_trends():
    """Get spending trends data with filters"""
    try:
        print("📈 API: Getting spending trends")
        where_clause, params = _build_analytics_filters(request.args)
        with db.engine.connect() as conn:
            df = _df(conn, f"""
                SELECT TO_CHAR(date, 'YYYY-MM') as month,
                       type,
                       SUM(amount) as total,
                       COUNT(*) as transaction_count
                FROM transactions
                {where_clause}
                GROUP BY TO_CHAR(date, 'YYYY-MM'), type
                ORDER BY month, type
            """, params)

        result = {}
        for _, row in df.iterrows():
            month = row['month']
            if month not in result:
                result[month] = {'month': month}
            result[month][row['type']] = {
                'total': float(row['total']),
                'count': int(row['transaction_count'])
            }
        result_list = sorted(result.values(), key=lambda x: x['month'])
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
        print("🥧 API: Getting category breakdown")
        where_clause, params = _build_analytics_filters(request.args)
        with db.engine.connect() as conn:
            df = _df(conn, f"""
                SELECT category,
                       SUM(amount) as total,
                       COUNT(*) as transaction_count,
                       AVG(amount) as avg_amount
                FROM transactions
                {where_clause}
                GROUP BY category
                ORDER BY total DESC
            """, params)

        total_amount = df['total'].sum()
        result = [
            {
                'category': row['category'],
                'total': float(row['total']),
                'transaction_count': int(row['transaction_count']),
                'avg_amount': float(row['avg_amount']),
                'percentage': (float(row['total']) / total_amount * 100) if total_amount > 0 else 0
            }
            for _, row in df.iterrows()
        ]
        print(f"🥧 Returning breakdown for {len(result)} categories")
        return jsonify(result)
    except Exception as e:
        print(f"❌ Error in category breakdown API: {e}")
        return jsonify({'error': str(e)}), 500


@analytics_bp.route('/api/owner_comparison')
def api_owner_comparison():
    """Get owner comparison data with filters"""
    try:
        print("👥 API: Getting owner comparison")
        where_clause, params = _build_analytics_filters(request.args)
        with db.engine.connect() as conn:
            df = _df(conn, f"""
                SELECT owner, type,
                       SUM(amount) as total,
                       COUNT(*) as transaction_count,
                       AVG(amount) as avg_amount
                FROM transactions
                {where_clause}
                GROUP BY owner, type
                ORDER BY owner, total DESC
            """, params)

        result = {}
        for _, row in df.iterrows():
            owner = row['owner']
            if owner not in result:
                result[owner] = {'owner': owner, 'total': 0, 'transaction_count': 0, 'types': {}}
            result[owner]['total'] += float(row['total'])
            result[owner]['transaction_count'] += int(row['transaction_count'])
            result[owner]['types'][row['type']] = {
                'total': float(row['total']),
                'count': int(row['transaction_count']),
                'avg': float(row['avg_amount'])
            }
        result_list = sorted(result.values(), key=lambda x: x['total'], reverse=True)
        print(f"👥 Returning comparison for {len(result_list)} owners")
        return jsonify(result_list)
    except Exception as e:
        print(f"❌ Error in owner comparison API: {e}")
        return jsonify({'error': str(e)}), 500


@analytics_bp.route('/api/transaction_types_breakdown')
def api_transaction_types_breakdown():
    """Get transaction types breakdown data with filters"""
    try:
        print("💳 API: Getting transaction types breakdown")
        where_clause, params = _build_analytics_filters(request.args)
        with db.engine.connect() as conn:
            df = _df(conn, f"""
                SELECT type,
                       SUM(amount) as total,
                       COUNT(*) as transaction_count,
                       AVG(amount) as avg_amount
                FROM transactions
                {where_clause}
                GROUP BY type
                ORDER BY total DESC
            """, params)

        total_amount = df['total'].sum()
        result = [
            {
                'type': row['type'],
                'total': float(row['total']),
                'transaction_count': int(row['transaction_count']),
                'avg_amount': float(row['avg_amount']),
                'percentage': (float(row['total']) / total_amount * 100) if total_amount > 0 else 0
            }
            for _, row in df.iterrows()
        ]
        print(f"💳 Returning breakdown for {len(result)} transaction types")
        return jsonify(result)
    except Exception as e:
        print(f"❌ Error in transaction types breakdown API: {e}")
        return jsonify({'error': str(e)}), 500


@analytics_bp.route('/api/filtered_transactions')
def api_filtered_transactions():
    """Return filtered transactions for analytics summary table"""
    try:
        where_clause, params = _build_analytics_filters(request.args)
        with db.engine.connect() as conn:
            df = _df(conn, f"""
                SELECT id, date, description, amount, category,
                       sub_category, owner, account_name, type
                FROM transactions
                {where_clause}
                ORDER BY date DESC
                LIMIT 100
            """, params)
        result = df.to_dict(orient='records')
        return jsonify(result)
    except Exception as e:
        print(f"❌ Error in filtered transactions API: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def get_monthly_spending_matrix(conn, filter_type=None, filter_value=None):
    extra = ""
    params = {}
    if filter_type == 'category' and filter_value:
        extra = ' AND category = :filter_val'
        params['filter_val'] = filter_value
    elif filter_type == 'subcategory' and filter_value:
        extra = ' AND sub_category = :filter_val'
        params['filter_val'] = filter_value
    elif filter_type == 'owner' and filter_value:
        extra = ' AND owner = :filter_val'
        params['filter_val'] = filter_value
    uid_sql, uid_p = uid_clause()
    params.update(uid_p)

    df = pd.read_sql_query(text(f"""
        SELECT {_year_expr()} AS year,
               {_month_expr()} AS month,
               SUM(amount) AS total
        FROM transactions
        WHERE COALESCE(is_active, true) = true{extra} {uid_sql}
        GROUP BY year, month
        ORDER BY year, month
    """), conn, params=params)

    if df.empty:
        return {}

    pivot = df.pivot(index='year', columns='month', values='total').fillna(0)
    pct_change = pivot.copy()
    for col in pivot.columns:
        for i in range(1, len(pivot)):
            prev_val = pivot.iloc[i - 1][col]
            curr_val = pivot.iloc[i][col]
            pct_change.iloc[i][col] = ((curr_val - prev_val) / abs(prev_val)) * 100 if prev_val != 0 else 0
        pct_change.iloc[0][col] = 0

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
    """Return a matrix of total spending per month per year, with percent change from previous year."""
    try:
        filter_type = request.args.get('filter_type')
        filter_value = request.args.get('filter_value')
        with db.engine.connect() as conn:
            matrix = get_monthly_spending_matrix(conn, filter_type, filter_value)
        return jsonify(matrix)
    except Exception as e:
        print(f"❌ Error in monthly spending matrix API: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@analytics_bp.route('/api/bulk_update_transactions', methods=['POST'])
def api_bulk_update_transactions():
    """Bulk update multiple transactions with new classification fields"""
    try:
        data = request.get_json()
        transaction_ids = data.get('transaction_ids', [])
        updates = data.get('updates', {})

        if not transaction_ids:
            return jsonify({'error': 'No transaction IDs provided'}), 400
        if not updates:
            return jsonify({'error': 'No updates provided'}), 400

        print(f"🔄 Bulk updating {len(transaction_ids)} transactions with: {updates}")

        set_clauses = []
        params = {}

        for field in ('category', 'sub_category', 'type', 'account_name', 'owner'):
            if updates.get(field):
                set_clauses.append(f"{field} = :{field}")
                params[field] = updates[field]

        if not set_clauses:
            return jsonify({'error': 'No valid update fields provided'}), 400

        id_params = {f'id_{i}': v for i, v in enumerate(transaction_ids)}
        params.update(id_params)
        id_placeholders = ', '.join(f':{k}' for k in id_params)
        uid_sql, uid_p = uid_clause()
        params.update(uid_p)

        with db.engine.begin() as conn:
            result = conn.execute(text(f"""
                UPDATE transactions
                SET {', '.join(set_clauses)}
                WHERE id IN ({id_placeholders}) {uid_sql}
            """), params)
            rows_updated = result.rowcount

        print(f"✅ Successfully updated {rows_updated} transactions")
        return jsonify({
            'success': True,
            'rows_updated': rows_updated,
            'message': f'Successfully updated {rows_updated} transactions'
        })
    except Exception as e:
        print(f"❌ Error in bulk update API: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
