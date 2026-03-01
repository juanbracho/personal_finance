from flask import Blueprint, jsonify, request
from datetime import datetime, date, timedelta
from utils import ensure_budget_tables, uid_clause, local_now
import pandas as pd
from models import db
from sqlalchemy import text
from app import limiter

api_bp = Blueprint('api', __name__, url_prefix='/api')


def _df(conn, sql, params=None):
    return pd.read_sql_query(text(sql), conn, params=params or {})


def _year_month_owner_filter(year, month, owner='all', month_str=False):
    """Build a WHERE fragment and params dict for year/month/owner filters."""
    filters = []
    params = {}
    filters.append("EXTRACT(YEAR FROM date)::integer = :year")
    params['year'] = year
    if month and month != 'all':
        filters.append("EXTRACT(MONTH FROM date)::integer = :month")
        params['month'] = int(month)
    if owner and owner != 'all':
        filters.append("owner = :owner")
        params['owner'] = owner
    uid_sql, uid_p = uid_clause()
    if uid_sql:
        filters.append("user_id = :_uid")
        params.update(uid_p)
    return " AND ".join(filters), params


@api_bp.route('/monthly_trends')
def monthly_trends():
    """Get monthly spending trends for charts"""
    try:
        owner = request.args.get('owner', 'all')
        type_filter = request.args.get('type')

        extra_filters = ""
        params = {}
        if owner != 'all':
            extra_filters += " AND owner = :owner"
            params['owner'] = owner
        if type_filter and type_filter != 'all':
            extra_filters += " AND type = :type_filter"
            params['type_filter'] = type_filter
        uid_sql, uid_p = uid_clause()
        extra_filters += f" {uid_sql}"
        params.update(uid_p)

        with db.engine.connect() as conn:
            df = _df(conn, f"""
                SELECT TO_CHAR(date, 'YYYY-MM') as month, SUM(amount) as total
                FROM transactions
                WHERE date >= CURRENT_DATE - INTERVAL '12 months'
                AND COALESCE(is_active, true) = true
                {extra_filters}
                GROUP BY TO_CHAR(date, 'YYYY-MM')
                ORDER BY month DESC
            """, params)

        result_list = [
            {'month': row['month'], 'expense': float(row['total'])}
            for _, row in df.iterrows()
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
        date_range = request.args.get('date_range', '30')
        include_business = request.args.get('include_business', 'true').lower() == 'true'

        filters = []
        params = {}

        if date_range != 'all':
            cutoff = (date.today() - timedelta(days=int(date_range))).isoformat()
            filters.append("date >= :date_cutoff")
            params['date_cutoff'] = cutoff
        if owner != 'all':
            filters.append("owner = :owner")
            params['owner'] = owner
        if not include_business:
            filters.append("is_business = false")

        filters.append("COALESCE(is_active, true) = true")
        uid_sql, uid_p = uid_clause()
        if uid_sql:
            filters.append("user_id = :_uid")
            params.update(uid_p)
        where_clause = "WHERE " + " AND ".join(filters)

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
                LIMIT 20
            """, params)

        result = [{
            'category': str(row['category']),
            'total': float(row['total']),
            'transaction_count': int(row['transaction_count']),
            'avg_amount': float(row['avg_amount'])
        } for _, row in df.iterrows()]
        return jsonify(result)
    except Exception as e:
        print(f"❌ Error in category spending API: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/budget_analysis')
def budget_analysis():
    """Get comprehensive budget analysis for a specific month/year"""
    try:
        month = request.args.get('month', local_now().month, type=int)
        year = request.args.get('year', local_now().year, type=int)
        owner = request.args.get('owner', 'all')

        spending_filter = ("EXTRACT(MONTH FROM date)::integer = :month"
                           " AND EXTRACT(YEAR FROM date)::integer = :year"
                           " AND COALESCE(is_active, true) = true")
        spending_params = {'month': month, 'year': year}
        if owner != 'all':
            spending_filter += " AND owner = :owner"
            spending_params['owner'] = owner
        uid_sql, uid_p = uid_clause()
        spending_filter += f" {uid_sql}"
        spending_params.update(uid_p)

        with db.engine.connect() as conn:
            actual_df = _df(conn, f"""
                SELECT category,
                       SUM(amount) as actual_amount,
                       COUNT(*) as transaction_count
                FROM transactions
                WHERE {spending_filter}
                GROUP BY category
                ORDER BY actual_amount DESC
            """, spending_params)

            budgets_df = _df(conn, f"""
                SELECT category, SUM(budget_amount) AS budget_amount
                FROM budget_subcategory_templates
                WHERE is_active = true {uid_sql}
                GROUP BY category
                ORDER BY category
            """, uid_p)

            unexpected_df = _df(conn, f"""
                SELECT category, SUM(amount) as total_unexpected
                FROM unexpected_expenses
                WHERE month = :month AND year = :year AND is_active = true {uid_sql}
                GROUP BY category
                ORDER BY category
            """, {'month': month, 'year': year, **uid_p})

        initial_budget_dict = {row['category']: float(row['budget_amount']) for _, row in budgets_df.iterrows()}
        unexpected_dict = {row['category']: float(row['total_unexpected']) for _, row in unexpected_df.iterrows()}
        actual_dict = {row['category']: float(row['actual_amount']) for _, row in actual_df.iterrows()}

        all_categories = set(initial_budget_dict.keys()) | set(unexpected_dict.keys()) | set(actual_dict.keys())

        result = []
        for category in sorted(all_categories):
            initial_budget = initial_budget_dict.get(category, 0.0)
            unexpected_expenses = unexpected_dict.get(category, 0.0)
            effective_budget = initial_budget + unexpected_expenses
            actual_spending = actual_dict.get(category, 0.0)
            variance = actual_spending - effective_budget
            variance_pct = (variance / effective_budget * 100) if effective_budget > 0 else 0

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
    """Get budget analysis with subcategory breakdown."""
    try:
        month = request.args.get('month', local_now().month, type=int)
        year = request.args.get('year', local_now().year, type=int)
        owner = request.args.get('owner', 'all')

        spending_filter = ("EXTRACT(MONTH FROM date)::integer = :month"
                           " AND EXTRACT(YEAR FROM date)::integer = :year"
                           " AND COALESCE(is_active, true) = true")
        spending_params = {'month': month, 'year': year}
        if owner != 'all':
            spending_filter += " AND owner = :owner"
            spending_params['owner'] = owner
        uid_sql, uid_p = uid_clause()
        spending_filter += f" {uid_sql}"
        spending_params.update(uid_p)

        with db.engine.connect() as conn:
            spending_df = _df(conn, f"""
                SELECT category,
                       COALESCE(NULLIF(TRIM(sub_category), ''), '(other)') AS sub_category,
                       SUM(amount) AS actual
                FROM transactions
                WHERE {spending_filter}
                GROUP BY category, sub_category
                ORDER BY category, sub_category
            """, spending_params)

            cat_budgets_df = _df(conn, f"""
                SELECT category, SUM(budget_amount) AS budget_amount
                FROM budget_subcategory_templates WHERE is_active = true {uid_sql}
                GROUP BY category
            """, uid_p)

            subcat_budgets_df = _df(conn, f"""
                SELECT category, sub_category, budget_amount
                FROM budget_subcategory_templates WHERE is_active = true {uid_sql}
            """, uid_p)

            unexpected_df = _df(conn, f"""
                SELECT category, SUM(amount) AS total_unexpected
                FROM unexpected_expenses
                WHERE month = :month AND year = :year AND is_active = true {uid_sql}
                GROUP BY category
            """, {'month': month, 'year': year, **uid_p})

        cat_budgets = {r['category']: float(r['budget_amount']) for _, r in cat_budgets_df.iterrows()}
        unexpected = {r['category']: float(r['total_unexpected']) for _, r in unexpected_df.iterrows()}

        subcat_budgets = {}
        for _, r in subcat_budgets_df.iterrows():
            subcat_budgets.setdefault(r['category'], {})[r['sub_category']] = float(r['budget_amount'])

        spending = {}
        for _, r in spending_df.iterrows():
            spending.setdefault(r['category'], {})[r['sub_category']] = float(r['actual'])

        def _status(variance, budget):
            if budget == 0:      return 'no_budget'
            if variance >  50:   return 'over'
            if variance < -50:   return 'under'
            return 'on_track'

        all_categories = (set(cat_budgets.keys()) | set(subcat_budgets.keys()) |
                          set(spending.keys()) | set(unexpected.keys()))

        result = []
        for category in sorted(all_categories):
            cat_initial = cat_budgets.get(category, 0.0)
            cat_unexpected = unexpected.get(category, 0.0)
            cat_subs_b = subcat_budgets.get(category, {})
            cat_subs_s = spending.get(category, {})
            all_subs = set(cat_subs_b.keys()) | set(cat_subs_s.keys())

            subcategories = []
            if all_subs:
                for sub in sorted(all_subs):
                    sub_budget = cat_subs_b.get(sub, 0.0)
                    sub_actual = cat_subs_s.get(sub, 0.0)
                    sub_var = sub_actual - sub_budget
                    subcategories.append({
                        'sub_category': sub,
                        'initial_budget': sub_budget,
                        'actual_spending': sub_actual,
                        'variance': sub_var,
                        'status': _status(sub_var, sub_budget),
                    })
            else:
                cat_actual = sum(cat_subs_s.values()) if cat_subs_s else 0.0
                cat_var = cat_actual - cat_initial
                subcategories.append({
                    'sub_category': category,
                    'initial_budget': cat_initial,
                    'actual_spending': cat_actual,
                    'variance': cat_var,
                    'status': _status(cat_var, cat_initial),
                })

            cat_actual_total = sum(s['actual_spending'] for s in subcategories)
            cat_effective = cat_initial + cat_unexpected
            cat_var = cat_actual_total - cat_effective

            result.append({
                'category': category,
                'initial_budget': cat_initial,
                'unexpected_expenses': cat_unexpected,
                'effective_budget': cat_effective,
                'actual_spending': cat_actual_total,
                'variance': cat_var,
                'status': _status(cat_var, cat_effective),
                'subcategories': subcategories,
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
        year = request.args.get('year', local_now().year, type=int)
        month = request.args.get('month', local_now().month, type=int)
        owner = request.args.get('owner', 'all')

        date_filter = ("EXTRACT(MONTH FROM date)::integer = :month"
                       " AND EXTRACT(YEAR FROM date)::integer = :year"
                       " AND COALESCE(is_active, true) = true")
        params = {'month': month, 'year': year}
        if owner != 'all':
            date_filter += " AND owner = :owner"
            params['owner'] = owner
        uid_sql, uid_p = uid_clause()
        date_filter += f" {uid_sql}"
        params.update(uid_p)

        with db.engine.connect() as conn:
            monthly_df = _df(conn, f"""
                SELECT type, SUM(amount) as total, COUNT(*) as count
                FROM transactions
                WHERE {date_filter}
                GROUP BY type
            """, params)

            categories_df = _df(conn, f"""
                SELECT category, SUM(amount) as total, COUNT(*) as count
                FROM transactions
                WHERE {date_filter}
                GROUP BY category
                ORDER BY total DESC
                LIMIT 5
            """, params)

            try:
                debt_df = _df(conn, f"""
                    SELECT COALESCE(SUM(current_balance), 0) as total_debt,
                           COALESCE(SUM(minimum_payment), 0) as total_minimum_payments,
                           COUNT(*) as debt_accounts
                    FROM debt_accounts WHERE is_active = true {uid_sql}
                """, uid_p)
                debt_data = debt_df.iloc[0].to_dict() if not debt_df.empty else {}
            except Exception:
                debt_data = {}

        monthly_spending = {}
        total_spending = 0
        for _, row in monthly_df.iterrows():
            monthly_spending[row['type']] = {
                'total': float(row['total']),
                'count': int(row['count'])
            }
            total_spending += float(row['total'])

        top_categories = [{
            'category': str(row['category']),
            'total': float(row['total']),
            'count': int(row['count'])
        } for _, row in categories_df.iterrows()]

        return jsonify({
            'summary': {
                'total_monthly_spending': total_spending,
                'total_debt': float(debt_data.get('total_debt', 0)),
                'total_minimum_payments': float(debt_data.get('total_minimum_payments', 0)),
                'debt_accounts': int(debt_data.get('debt_accounts', 0)),
                'period': f"{year}-{month:02d}",
                'owner': owner
            },
            'monthly_spending': monthly_spending,
            'top_categories': top_categories
        })
    except Exception as e:
        print(f"❌ Error in dashboard summary API: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/categories/categories')
def api_categories():
    """Get categories with statistics"""
    try:
        year = request.args.get('year', local_now().year, type=int)
        month = request.args.get('month', 'all')
        owner = request.args.get('owner', 'all')

        date_filter = "EXTRACT(YEAR FROM date)::integer = :year"
        params = {'year': year}
        if month != 'all':
            date_filter += " AND EXTRACT(MONTH FROM date)::integer = :month"
            params['month'] = int(month)
        if owner != 'all':
            date_filter += " AND owner = :owner"
            params['owner'] = owner
        uid_sql, uid_p = uid_clause()
        # date_filter is used in the plain transactions query (no JOIN).
        date_filter += f" {uid_sql}"
        params.update(uid_p)
        # For the LEFT JOIN query, budget_templates also has user_id, making the
        # bare reference ambiguous in PostgreSQL. Use a table-qualified variant.
        joined_filter = date_filter.replace('AND user_id', 'AND t.user_id')

        with db.engine.connect() as conn:
            categories_df = _df(conn, f"""
                SELECT t.category,
                       COUNT(*) as transaction_count,
                       SUM(t.amount) as total_amount,
                       AVG(t.amount) as avg_amount,
                       bt.budget_amount,
                       MAX(t.date) as last_used,
                       MIN(t.date) as first_used
                FROM transactions t
                LEFT JOIN budget_templates bt
                       ON t.category = bt.category
                      AND bt.is_active = true
                      AND bt.user_id = t.user_id
                WHERE {joined_filter}
                GROUP BY t.category, bt.budget_amount
                ORDER BY total_amount DESC
            """, params)

            type_df = _df(conn, f"""
                SELECT category, type, COUNT(*) as type_count
                FROM transactions
                WHERE {date_filter}
                GROUP BY category, type
                ORDER BY category, type_count DESC
            """, params)

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
        year = request.args.get('year', local_now().year, type=int)
        month = request.args.get('month', 'all')
        owner = request.args.get('owner', 'all')

        date_filter = "EXTRACT(YEAR FROM date)::integer = :year"
        params = {'year': year}
        if month != 'all':
            date_filter += " AND EXTRACT(MONTH FROM date)::integer = :month"
            params['month'] = int(month)
        if owner != 'all':
            date_filter += " AND owner = :owner"
            params['owner'] = owner
        uid_sql, uid_p = uid_clause()
        date_filter += f" {uid_sql}"
        params.update(uid_p)

        with db.engine.connect() as conn:
            df = _df(conn, f"""
                SELECT sub_category as name, category,
                       COUNT(*) as transaction_count,
                       SUM(amount) as total_amount,
                       AVG(amount) as avg_amount,
                       MAX(date) as last_used,
                       MIN(date) as first_used
                FROM transactions
                WHERE {date_filter}
                AND sub_category IS NOT NULL AND sub_category != ''
                AND COALESCE(is_active, true) = true
                GROUP BY sub_category, category
                ORDER BY total_amount DESC
            """, params)

        result = [{
            'name': str(row['name']),
            'category': str(row['category']),
            'transaction_count': int(row['transaction_count']),
            'total_amount': float(row['total_amount']),
            'avg_amount': float(row['avg_amount']),
            'last_used': str(row['last_used']),
            'first_used': str(row['first_used'])
        } for _, row in df.iterrows()]

        print(f"🏷️ Returning {len(result)} subcategories")
        return jsonify(result)
    except Exception as e:
        print(f"❌ Error getting subcategories: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/categories/owners')
def api_owners():
    """Get owners with statistics"""
    try:
        year = request.args.get('year', local_now().year, type=int)
        month = request.args.get('month', 'all')

        date_filter = "EXTRACT(YEAR FROM date)::integer = :year"
        params = {'year': year}
        if month != 'all':
            date_filter += " AND EXTRACT(MONTH FROM date)::integer = :month"
            params['month'] = int(month)
        uid_sql, uid_p = uid_clause()
        date_filter += f" {uid_sql}"
        params.update(uid_p)

        with db.engine.connect() as conn:
            df = _df(conn, f"""
                SELECT owner as name,
                       COUNT(*) as transaction_count,
                       SUM(amount) as total_amount,
                       AVG(amount) as avg_amount,
                       MAX(date) as last_used,
                       MIN(date) as first_used
                FROM transactions
                WHERE {date_filter} AND COALESCE(is_active, true) = true
                GROUP BY owner
                ORDER BY total_amount DESC
            """, params)

        result = [{
            'name': str(row['name']),
            'transaction_count': int(row['transaction_count']),
            'total_amount': float(row['total_amount']),
            'avg_amount': float(row['avg_amount']),
            'last_used': str(row['last_used']),
            'first_used': str(row['first_used'])
        } for _, row in df.iterrows()]

        print(f"👥 Returning {len(result)} owners")
        return jsonify(result)
    except Exception as e:
        print(f"❌ Error getting owners: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/categories/accounts')
def api_accounts():
    """Get accounts with statistics"""
    try:
        year = request.args.get('year', local_now().year, type=int)
        month = request.args.get('month', 'all')

        date_filter = "EXTRACT(YEAR FROM date)::integer = :year"
        params = {'year': year}
        if month != 'all':
            date_filter += " AND EXTRACT(MONTH FROM date)::integer = :month"
            params['month'] = int(month)
        uid_sql, uid_p = uid_clause()
        date_filter += f" {uid_sql}"
        params.update(uid_p)

        with db.engine.connect() as conn:
            df = _df(conn, f"""
                SELECT account_name as name,
                       COUNT(*) as transaction_count,
                       SUM(amount) as total_amount,
                       AVG(amount) as avg_amount,
                       MAX(date) as last_used,
                       MIN(date) as first_used
                FROM transactions
                WHERE {date_filter} AND COALESCE(is_active, true) = true
                GROUP BY account_name
                ORDER BY total_amount DESC
            """, params)

        result = [{
            'name': str(row['name']),
            'transaction_count': int(row['transaction_count']),
            'total_amount': float(row['total_amount']),
            'avg_amount': float(row['avg_amount']),
            'last_used': str(row['last_used']),
            'first_used': str(row['first_used'])
        } for _, row in df.iterrows()]

        print(f"💳 Returning {len(result)} accounts")
        return jsonify(result)
    except Exception as e:
        print(f"❌ Error getting accounts: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/categories/types')
def api_types():
    """Get types with statistics"""
    try:
        all_years = request.args.get('all_years', '0') == '1'
        year = request.args.get('year', local_now().year, type=int)
        month = request.args.get('month', 'all')
        owner = request.args.get('owner', 'all')

        if all_years:
            date_filter = "1=1"
            params = {}
        else:
            date_filter = "EXTRACT(YEAR FROM date)::integer = :year"
            params = {'year': year}
            if month != 'all':
                date_filter += " AND EXTRACT(MONTH FROM date)::integer = :month"
                params['month'] = int(month)
        if owner != 'all':
            date_filter += " AND owner = :owner"
            params['owner'] = owner
        uid_sql, uid_p = uid_clause()
        date_filter += f" {uid_sql}"
        params.update(uid_p)

        with db.engine.connect() as conn:
            df = _df(conn, f"""
                SELECT type as name,
                       COUNT(*) as transaction_count,
                       SUM(amount) as total_amount,
                       AVG(amount) as avg_amount,
                       MAX(date) as last_used,
                       MIN(date) as first_used
                FROM transactions
                WHERE {date_filter}
                GROUP BY type
                ORDER BY total_amount DESC
            """, params)

        result = [{
            'name': str(row['name']),
            'transaction_count': int(row['transaction_count']),
            'total_amount': float(row['total_amount']),
            'avg_amount': float(row['avg_amount']),
            'last_used': str(row['last_used']),
            'first_used': str(row['first_used'])
        } for _, row in df.iterrows()]

        print(f"🔖 Returning {len(result)} types")
        return jsonify(result)
    except Exception as e:
        print(f"❌ Error getting types: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/categories/types', methods=['POST'])
def add_type():
    """Validate that a new custom type name is not already in use."""
    try:
        data = request.get_json()
        name = (data.get('name') or '').strip()
        if not name:
            return jsonify({'success': False, 'error': 'Name is required'}), 400

        uid_sql, uid_p = uid_clause()
        with db.engine.connect() as conn:
            count = conn.execute(text(
                f"SELECT COUNT(*) FROM transactions WHERE type = :name {uid_sql}"
            ), {'name': name, **uid_p}).scalar()

        if count > 0:
            return jsonify({'success': False, 'error': f'Type "{name}" already exists in transactions'}), 400

        return jsonify({'success': True, 'message': f'Type "{name}" created successfully'})
    except Exception as e:
        print(f"❌ Error adding type: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/categories/types/<type_name>', methods=['PUT'])
def edit_type(type_name):
    """Rename a type (updates all transactions that use it)"""
    try:
        data = request.get_json()
        new_name = (data.get('name') or '').strip()
        if not new_name:
            return jsonify({'success': False, 'error': 'Name is required'}), 400

        uid_sql, uid_p = uid_clause()
        with db.engine.begin() as conn:
            conn.execute(text(f"""
                UPDATE transactions SET type = :new_name, updated_at = :now
                WHERE type = :old_name {uid_sql}
            """), {'new_name': new_name, 'now': datetime.utcnow(), 'old_name': type_name, **uid_p})

        return jsonify({'success': True, 'message': f'Type renamed from "{type_name}" to "{new_name}"'})
    except Exception as e:
        print(f"❌ Error editing type: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/categories/types/<type_name>', methods=['DELETE'])
def delete_type(type_name):
    """Delete a type only if no transactions use it."""
    try:
        uid_sql, uid_p = uid_clause()
        with db.engine.connect() as conn:
            count = conn.execute(text(
                f"SELECT COUNT(*) FROM transactions WHERE type = :name {uid_sql}"
            ), {'name': type_name, **uid_p}).scalar()

        if count > 0:
            return jsonify({
                'success': False,
                'error': f'Cannot delete: {count} transactions use this type. Migrate first.',
                'transaction_count': count
            }), 400

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

        uid_sql, uid_p = uid_clause()
        with db.engine.connect() as conn:
            df = _df(conn, f"""
                SELECT date, description, amount, category,
                       sub_category, owner, account_name
                FROM transactions
                WHERE {field} = :name AND COALESCE(is_active, true) = true {uid_sql}
                ORDER BY date DESC
                LIMIT 50
            """, {'name': name, **uid_p})

        result = [{
            'date': str(row['date']),
            'description': str(row['description']),
            'amount': float(row['amount']),
            'category': str(row['category']),
            'sub_category': str(row['sub_category']) if row['sub_category'] else '',
            'owner': str(row['owner']),
            'account_name': str(row['account_name'])
        } for _, row in df.iterrows()]

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
        if not name:
            return jsonify({'success': False, 'error': 'Category name required'}), 400

        uid_sql, uid_p = uid_clause()
        uid = uid_p.get('_uid')
        with db.engine.begin() as conn:
            count = conn.execute(text(
                f"SELECT COUNT(*) FROM transactions WHERE category = :name {uid_sql}"
            ), {'name': name, **uid_p}).scalar()
            if count > 0:
                return jsonify({'success': False, 'error': 'Category already exists in transactions'}), 400

            # Only insert if not already in budget_templates for this user
            existing = conn.execute(text(
                f"SELECT COUNT(*) FROM budget_templates WHERE category = :name {uid_sql}"
            ), {'name': name, **uid_p}).scalar()
            if existing == 0:
                conn.execute(text("""
                    INSERT INTO budget_templates (category, budget_amount, notes, is_active, user_id, created_at, updated_at)
                    VALUES (:name, 0.00, :notes, true, :uid, :now, :now)
                """), {'name': name, 'notes': 'Added via categories management', 'uid': uid, 'now': datetime.utcnow()})

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

        uid_sql, uid_p = uid_clause()
        with db.engine.connect() as conn:
            count = conn.execute(text(
                f"SELECT COUNT(*) FROM transactions WHERE sub_category = :name {uid_sql}"
            ), {'name': name, **uid_p}).scalar()
            if count > 0:
                return jsonify({'success': False, 'error': 'Subcategory already exists in transactions'}), 400

            cat_count = conn.execute(text(
                f"SELECT COUNT(*) FROM transactions WHERE category = :cat {uid_sql}"
            ), {'cat': category, **uid_p}).scalar()
            if cat_count == 0:
                return jsonify({'success': False, 'error': 'Parent category does not exist'}), 400

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

        uid_sql, uid_p = uid_clause()
        with db.engine.connect() as conn:
            count = conn.execute(text(
                f"SELECT COUNT(*) FROM transactions WHERE owner = :name {uid_sql}"
            ), {'name': name, **uid_p}).scalar()
            if count > 0:
                return jsonify({'success': False, 'error': 'Owner already exists in transactions'}), 400

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

        uid_sql, uid_p = uid_clause()
        with db.engine.connect() as conn:
            count = conn.execute(text(
                f"SELECT COUNT(*) FROM transactions WHERE account_name = :name {uid_sql}"
            ), {'name': name, **uid_p}).scalar()
            if count > 0:
                return jsonify({'success': False, 'error': 'Account already exists in transactions'}), 400

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

        uid_sql, uid_p = uid_clause()
        with db.engine.begin() as conn:
            count = conn.execute(text(
                f"SELECT COUNT(*) FROM transactions WHERE {field} = :source {uid_sql}"
            ), {'source': source, **uid_p}).scalar()

            if count == 0:
                return jsonify({'success': False, 'error': 'No transactions found to migrate'}), 400

            upd = conn.execute(text(f"""
                UPDATE transactions
                SET {field} = :target, updated_at = :now
                WHERE {field} = :source {uid_sql}
            """), {'target': target, 'now': datetime.utcnow(), 'source': source, **uid_p})
            migrated_count = upd.rowcount

            if item_type == 'category':
                conn.execute(text(f"""
                    UPDATE budget_templates
                    SET category = :target, updated_at = :now
                    WHERE category = :source {uid_sql}
                """), {'target': target, 'now': datetime.utcnow(), 'source': source, **uid_p})

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
        uid_sql, uid_p = uid_clause()
        with db.engine.begin() as conn:
            count = conn.execute(text(
                f"SELECT COUNT(*) FROM transactions WHERE category = :name {uid_sql}"
            ), {'name': category_name, **uid_p}).scalar()

            if count > 0:
                return jsonify({
                    'success': False,
                    'error': f'Cannot delete category with {count} transactions. Please migrate them first.'
                }), 400

            conn.execute(text(
                f"DELETE FROM budget_templates WHERE category = :name {uid_sql}"
            ), {'name': category_name, **uid_p})

        print(f"✅ Deleted category: {category_name}")
        return jsonify({'success': True, 'message': f'Category "{category_name}" deleted successfully'})
    except Exception as e:
        print(f"❌ Error deleting category: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/categories/subcategories/<subcategory_name>', methods=['DELETE'])
def delete_subcategory(subcategory_name):
    """Delete a subcategory (only if no transactions)"""
    try:
        uid_sql, uid_p = uid_clause()
        with db.engine.connect() as conn:
            count = conn.execute(text(
                f"SELECT COUNT(*) FROM transactions WHERE sub_category = :name {uid_sql}"
            ), {'name': subcategory_name, **uid_p}).scalar()

        if count > 0:
            return jsonify({
                'success': False,
                'error': f'Cannot delete subcategory with {count} transactions. Please migrate them first.'
            }), 400

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
        if not new_name:
            return jsonify({'success': False, 'error': 'Category name required'}), 400
        if new_name == category_name:
            return jsonify({'success': True, 'message': 'No changes needed'})

        uid_sql, uid_p = uid_clause()
        with db.engine.begin() as conn:
            exists = conn.execute(text(
                f"SELECT COUNT(*) FROM transactions WHERE category = :name {uid_sql}"
            ), {'name': new_name, **uid_p}).scalar()
            if exists > 0:
                return jsonify({'success': False, 'error': 'Category name already exists'}), 400

            conn.execute(text(f"""
                UPDATE transactions SET category = :new_name, updated_at = :now
                WHERE category = :old_name {uid_sql}
            """), {'new_name': new_name, 'now': datetime.utcnow(), 'old_name': category_name, **uid_p})

            conn.execute(text(f"""
                UPDATE budget_templates SET category = :new_name, updated_at = :now
                WHERE category = :old_name {uid_sql}
            """), {'new_name': new_name, 'now': datetime.utcnow(), 'old_name': category_name, **uid_p})

        print(f"✅ Renamed category from {category_name} to {new_name}")
        return jsonify({'success': True, 'message': 'Category renamed successfully'})
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

        uid_sql, uid_p = uid_clause()
        with db.engine.begin() as conn:
            if new_category:
                conn.execute(text(f"""
                    UPDATE transactions
                    SET sub_category = :new_name, category = :new_cat, updated_at = :now
                    WHERE sub_category = :old_name {uid_sql}
                """), {'new_name': new_name, 'new_cat': new_category,
                       'now': datetime.utcnow(), 'old_name': subcategory_name, **uid_p})
            else:
                conn.execute(text(f"""
                    UPDATE transactions SET sub_category = :new_name, updated_at = :now
                    WHERE sub_category = :old_name {uid_sql}
                """), {'new_name': new_name, 'now': datetime.utcnow(), 'old_name': subcategory_name, **uid_p})

        print(f"✅ Updated subcategory from {subcategory_name} to {new_name}")
        return jsonify({'success': True, 'message': 'Subcategory updated successfully'})
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

        uid_sql, uid_p = uid_clause()
        with db.engine.begin() as conn:
            conn.execute(text(f"""
                UPDATE transactions SET owner = :new_name, updated_at = :now
                WHERE owner = :old_name {uid_sql}
            """), {'new_name': new_name, 'now': datetime.utcnow(), 'old_name': owner_name, **uid_p})

        print(f"✅ Renamed owner from {owner_name} to {new_name}")
        return jsonify({'success': True, 'message': 'Owner renamed successfully'})
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

        uid_sql, uid_p = uid_clause()
        with db.engine.begin() as conn:
            conn.execute(text(f"""
                UPDATE transactions SET account_name = :new_name, updated_at = :now
                WHERE account_name = :old_name {uid_sql}
            """), {'new_name': new_name, 'now': datetime.utcnow(), 'old_name': account_name, **uid_p})

        print(f"✅ Renamed account from {account_name} to {new_name}")
        return jsonify({'success': True, 'message': 'Account renamed successfully'})
    except Exception as e:
        print(f"❌ Error editing account: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/categories/statistics')
def api_categories_statistics():
    """Get statistics for all category types"""
    try:
        year = request.args.get('year', local_now().year, type=int)
        month = request.args.get('month', 'all')
        owner = request.args.get('owner', 'all')

        date_filter = "EXTRACT(YEAR FROM date)::integer = :year"
        params = {'year': year}
        if month != 'all':
            date_filter += " AND EXTRACT(MONTH FROM date)::integer = :month"
            params['month'] = int(month)
        if owner != 'all':
            date_filter += " AND owner = :owner"
            params['owner'] = owner
        uid_sql, uid_p = uid_clause()
        date_filter += f" {uid_sql}"
        params.update(uid_p)

        active_filter = f"{date_filter} AND COALESCE(is_active, true) = true"

        with db.engine.connect() as conn:
            def _scalar(sql):
                return conn.execute(text(sql), params).scalar() or 0

            stats = {
                'categories': _scalar(f"SELECT COUNT(DISTINCT category) FROM transactions WHERE {active_filter}"),
                'subcategories': _scalar(f"""
                    SELECT COUNT(DISTINCT sub_category) FROM transactions
                    WHERE {active_filter} AND sub_category IS NOT NULL AND sub_category != ''
                """),
                'owners': _scalar(f"SELECT COUNT(DISTINCT owner) FROM transactions WHERE {active_filter}"),
                'accounts': _scalar(f"SELECT COUNT(DISTINCT account_name) FROM transactions WHERE {active_filter}"),
                'types': _scalar(f"SELECT COUNT(DISTINCT type) FROM transactions WHERE {active_filter}"),
            }

        print(f"📊 Statistics for {year}-{month} owner={owner}: {stats}")
        return jsonify(stats)
    except Exception as e:
        print(f"❌ Error getting statistics: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'categories': 0, 'subcategories': 0, 'owners': 0, 'accounts': 0, 'types': 0}), 500


@api_bp.route('/accounts/list')
def get_accounts_list():
    """Get all accounts (regular + debt accounts) for transaction form dropdown"""
    try:
        print("💳 Getting accounts list for transaction form")
        accounts_list = []

        with db.engine.connect() as conn:
            # Try accounts table (may not exist)
            try:
                rows = conn.execute(text("""
                    SELECT id, name, account_type, is_debt, debt_account_id
                    FROM accounts WHERE is_active = true ORDER BY name
                """)).fetchall()
                for row in rows:
                    accounts_list.append({
                        'id': row[0],
                        'name': row[1],
                        'account_type': row[2],
                        'is_debt': bool(row[3]),
                        'debt_account_id': row[4]
                    })
            except Exception:
                pass

            # Debt accounts
            uid_sql, uid_p = uid_clause()
            debt_rows = conn.execute(text(f"""
                SELECT id, name, debt_type FROM debt_accounts
                WHERE is_active = true {uid_sql} ORDER BY name
            """), uid_p).fetchall()
            for debt in debt_rows:
                existing = next((a for a in accounts_list if a.get('debt_account_id') == debt[0]), None)
                if not existing:
                    accounts_list.append({
                        'id': f"debt_{debt[0]}",
                        'name': debt[1],
                        'account_type': debt[2],
                        'is_debt': True,
                        'debt_account_id': debt[0]
                    })

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
    """Get transactions for a specific category/subcategory and month for budget drill-down."""
    try:
        category = request.args.get('category')
        subcategory = request.args.get('subcategory')
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        owner = request.args.get('owner', 'all')

        if not all([category, year, month]):
            return jsonify({'error': 'Missing required parameters: category, year, month'}), 400

        if subcategory:
            print(f"📊 Fetching transactions: {category} > {subcategory} for {year}-{month:02d}")
        else:
            print(f"📊 Fetching all transactions for category: {category} for {year}-{month:02d}")

        filters = [
            "category = :category",
            "EXTRACT(YEAR FROM date)::integer = :year",
            "EXTRACT(MONTH FROM date)::integer = :month",
            "COALESCE(is_active, true) = true"
        ]
        params = {'category': category, 'year': year, 'month': month}

        if subcategory:
            filters.append("sub_category = :subcategory")
            params['subcategory'] = subcategory
        if owner != 'all':
            filters.append("owner = :owner")
            params['owner'] = owner
        uid_sql, uid_p = uid_clause()
        if uid_sql:
            filters.append("user_id = :_uid")
            params.update(uid_p)

        where = "WHERE " + " AND ".join(filters)

        with db.engine.connect() as conn:
            rows = conn.execute(text(f"""
                SELECT id, date, description, amount, account_name, owner, type, sub_category
                FROM transactions
                {where}
                ORDER BY date DESC, created_at DESC
            """), params).fetchall()

        transactions = [{
            'id': row[0],
            'date': row[1],
            'description': row[2],
            'amount': float(row[3]),
            'account_name': row[4] or 'N/A',
            'owner': row[5] or 'Unknown',
            'type': row[6] or '',
            'sub_category': row[7] or ''
        } for row in rows]

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
# ---------------------------------------------------------------------------

@api_bp.route('/transactions', methods=['GET'])
def api_transactions_list():
    """Paginated transaction list for the Flutter mobile app."""
    try:
        page = max(1, request.args.get('page', 1, type=int))
        per_page = min(200, max(1, request.args.get('per_page', 50, type=int)))
        offset = (page - 1) * per_page
        owner = request.args.get('owner', 'all')
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        category = request.args.get('category', '')

        filters = ["COALESCE(is_active, true) = true"]
        params = {}

        if owner and owner != 'all':
            filters.append("owner = :owner")
            params['owner'] = owner
        if year:
            filters.append("EXTRACT(YEAR FROM date)::integer = :year")
            params['year'] = year
        if month:
            filters.append("EXTRACT(MONTH FROM date)::integer = :month")
            params['month'] = month
        if category:
            filters.append("category = :category")
            params['category'] = category
        uid_sql, uid_p = uid_clause()
        if uid_sql:
            filters.append("user_id = :_uid")
            params.update(uid_p)

        where = "WHERE " + " AND ".join(filters)

        with db.engine.connect() as conn:
            total = conn.execute(text(f"SELECT COUNT(*) FROM transactions {where}"), params).scalar()

            params_paged = {**params, 'per_page': per_page, 'offset': offset}
            rows = conn.execute(text(f"""
                SELECT id, account_name, date, description, amount,
                       sub_category, category, type, owner, is_business
                FROM transactions {where}
                ORDER BY date DESC, id DESC
                LIMIT :per_page OFFSET :offset
            """), params_paged).fetchall()

        transactions = [{
            'id': r[0], 'account_name': r[1], 'date': r[2],
            'description': r[3], 'amount': float(r[4]) if r[4] is not None else 0.0,
            'sub_category': r[5], 'category': r[6],
            'type': r[7], 'owner': r[8], 'is_business': bool(r[9])
        } for r in rows]

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
    """Add a transaction from the Flutter mobile app (JSON body)."""
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

        try:
            datetime.strptime(data['date'], '%Y-%m-%d')
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid date format, expected YYYY-MM-DD'}), 400

        from utils import current_user_id
        with db.engine.begin() as conn:
            result = conn.execute(text("""
                INSERT INTO transactions
                (account_name, date, description, amount, sub_category, category,
                 type, owner, is_business, is_active, user_id)
                VALUES (:account_name, :date, :description, :amount, :sub_category,
                        :category, :type, :owner, :is_business, true, :user_id)
                RETURNING id
            """), {
                'account_name': data.get('account_name', ''),
                'date': data['date'],
                'description': data['description'],
                'amount': amount,
                'sub_category': data.get('sub_category', ''),
                'category': data['category'],
                'type': data['type'],
                'owner': data['owner'],
                'is_business': bool(data.get('is_business', False)),
                'user_id': current_user_id(),
            })
            transaction_id = result.fetchone()[0]

        return jsonify({'success': True, 'id': transaction_id}), 201
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def api_login():
    """JWT authentication for Flutter / programmatic clients."""
    from werkzeug.security import check_password_hash
    from auth import _issue_jwt, _log_audit
    from models import User
    from flask import current_app

    data = request.get_json(silent=True) or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'success': False, 'error': 'username and password are required.'}), 400

    try:
        user = db.session.query(User).filter_by(username=username).first()
    except Exception as exc:
        current_app.logger.error("api_login DB error: %s", exc)
        return jsonify({'success': False, 'error': 'Server error.'}), 500

    if not user or not user.is_active or not user.password_hash or \
            not check_password_hash(user.password_hash, password):
        _log_audit('api_login_failure', extra={'username': username, 'ip': request.remote_addr})
        return jsonify({'success': False, 'error': 'Invalid username or password.'}), 401

    token = _issue_jwt(user)
    _log_audit('api_login_success', user_id=user.id, extra={'username': username})

    return jsonify({
        'success': True,
        'token': token,
        'user_id': user.id,
        'role': user.role,
        'expires_in': 3600,
    }), 200


@api_bp.route('/debts', methods=['GET'])
def api_debts_list():
    """Debt accounts list for the Flutter mobile app."""
    try:
        show_paid_off = request.args.get('show_paid_off', 'false').lower() == 'true'

        with db.engine.connect() as conn:
            if show_paid_off:
                rows = conn.execute(text(
                    "SELECT * FROM debt_accounts ORDER BY is_active DESC, current_balance DESC"
                )).mappings().all()
            else:
                rows = conn.execute(text(
                    "SELECT * FROM debt_accounts WHERE is_active = true ORDER BY current_balance DESC"
                )).mappings().all()

        debts = []
        for row in rows:
            debt = dict(row)
            for key in ('current_balance', 'original_balance', 'interest_rate', 'minimum_payment'):
                if debt.get(key) is not None:
                    debt[key] = float(debt[key])
            debt['is_active'] = bool(debt.get('is_active', True))
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
