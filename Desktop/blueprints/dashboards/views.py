from flask import render_template, request
from datetime import datetime
from models import db
from sqlalchemy import text
import pandas as pd
from utils import uid_clause


def _df(conn, sql, params=None):
    """Execute a SQLAlchemy text query and return a pandas DataFrame."""
    return pd.read_sql_query(text(sql), conn, params=params or {})


def dashboard_overview_view(year, month, owner, available_years, available_owners):
    """Dashboard Overview - Enhanced with additional metrics"""

    try:
        uid_sql, uid_p = uid_clause()
        with db.engine.connect() as conn:
            # Build filter conditions
            date_filter = "EXTRACT(MONTH FROM date)::integer = :month AND EXTRACT(YEAR FROM date)::integer = :year"
            params = {"month": month, "year": year}

            if owner != 'all':
                date_filter += " AND owner = :owner"
                params["owner"] = owner
            date_filter += f" {uid_sql}"
            params.update(uid_p)

            # Monthly spending by type
            monthly_spending_df = _df(conn, f"""
                SELECT type, SUM(amount) as total, COUNT(*) as count
                FROM transactions
                WHERE {date_filter} AND COALESCE(is_active, true) = true
                GROUP BY type ORDER BY total DESC
            """, params)
            monthly_spending = [(row['type'], float(row['total']), int(row['count']))
                                for _, row in monthly_spending_df.iterrows()]

            # Top 5 categories
            top_categories_df = _df(conn, f"""
                SELECT category, SUM(amount) as total, COUNT(*) as count
                FROM transactions
                WHERE {date_filter} AND COALESCE(is_active, true) = true
                GROUP BY category ORDER BY total DESC LIMIT 5
            """, params)
            top_categories = [(row['category'], float(row['total']), int(row['count']))
                              for _, row in top_categories_df.iterrows()]

            # Previous year same month
            prev_params = {"month": month, "year": year - 1}
            if owner != 'all':
                prev_params["owner"] = owner
            prev_params.update(uid_p)
            prev_year_df = _df(conn, f"""
                SELECT SUM(amount) as total FROM transactions
                WHERE {date_filter} AND COALESCE(is_active, true) = true
            """, prev_params)
            prev_year_total = float(prev_year_df['total'].iloc[0]) if not prev_year_df.empty and prev_year_df['total'].iloc[0] else 0

            current_total = sum(amount for _, amount, _ in monthly_spending)

            # Year-to-date
            ytd_filter = "EXTRACT(YEAR FROM date)::integer = :year AND EXTRACT(MONTH FROM date)::integer <= :month"
            ytd_params = {"year": year, "month": month}
            if owner != 'all':
                ytd_filter += " AND owner = :owner"
                ytd_params["owner"] = owner
            ytd_filter += f" {uid_sql}"
            ytd_params.update(uid_p)

            ytd_df = _df(conn, f"""
                SELECT SUM(amount) as total FROM transactions
                WHERE {ytd_filter} AND COALESCE(is_active, true) = true
            """, ytd_params)
            ytd_total = float(ytd_df['total'].iloc[0]) if not ytd_df.empty and ytd_df['total'].iloc[0] else 0

            prev_ytd_params = {"year": year - 1, "month": month}
            if owner != 'all':
                prev_ytd_params["owner"] = owner
            prev_ytd_params.update(uid_p)
            prev_ytd_df = _df(conn, f"""
                SELECT SUM(amount) as total FROM transactions
                WHERE {ytd_filter} AND COALESCE(is_active, true) = true
            """, prev_ytd_params)
            prev_ytd_total = float(prev_ytd_df['total'].iloc[0]) if not prev_ytd_df.empty and prev_ytd_df['total'].iloc[0] else 0

            # Budget performance summary
            budget_df = _df(conn, f"""
                SELECT
                    bt.category,
                    bt.budget_amount,
                    COALESCE(ue.total_unexpected, 0) as unexpected_expenses,
                    COALESCE(actual.actual_amount, 0) as actual_spending
                FROM budget_templates bt
                LEFT JOIN (
                    SELECT category, SUM(amount) as total_unexpected
                    FROM unexpected_expenses
                    WHERE month = :month AND year = :year AND is_active = true {uid_sql}
                    GROUP BY category
                ) ue ON bt.category = ue.category
                LEFT JOIN (
                    SELECT category, SUM(amount) as actual_amount
                    FROM transactions
                    WHERE {date_filter} AND COALESCE(is_active, true) = true
                    GROUP BY category
                ) actual ON bt.category = actual.category
                WHERE bt.is_active = true {uid_sql}
            """, params)

            over_budget_count = under_budget_count = on_track_count = 0
            for _, row in budget_df.iterrows():
                eff = float(row['budget_amount']) + float(row['unexpected_expenses'])
                actual = float(row['actual_spending'])
                variance = actual - eff
                if eff > 0:
                    if variance > 50:
                        over_budget_count += 1
                    elif variance < -50:
                        under_budget_count += 1
                    else:
                        on_track_count += 1

            # Recent transactions
            recent_df = _df(conn, f"""
                SELECT date, description, amount, category, owner, account_name
                FROM transactions
                WHERE COALESCE(is_active, true) = true {uid_sql}
                ORDER BY date DESC, created_at DESC
                LIMIT 10
            """, uid_p)
            recent_transactions = [{
                'date': str(row['date']),
                'description': row['description'],
                'amount': float(row['amount']),
                'category': row['category'],
                'owner': row['owner'],
                'account_name': row['account_name']
            } for _, row in recent_df.iterrows()]

            # 3-month spending trend
            trend_params = {"owner": owner} if owner != 'all' else {}
            owner_clause = "AND owner = :owner" if owner != 'all' else ""
            trend_params.update(uid_p)
            trend_df = _df(conn, f"""
                SELECT TO_CHAR(date, 'YYYY-MM') as month_year, SUM(amount) as total
                FROM transactions
                WHERE date >= CURRENT_DATE - INTERVAL '3 months'
                AND COALESCE(is_active, true) = true
                {owner_clause} {uid_sql}
                GROUP BY TO_CHAR(date, 'YYYY-MM')
                ORDER BY month_year DESC
                LIMIT 3
            """, trend_params)
            monthly_trend = [{'month': row['month_year'], 'total': float(row['total'])}
                             for _, row in trend_df.iterrows()]
            monthly_trend.reverse()

            # Total debt
            try:
                debt_df = _df(conn, f"""
                    SELECT COALESCE(SUM(current_balance), 0) as total_debt
                    FROM debt_accounts WHERE is_active = true {uid_sql}
                """, uid_p)
                total_debt = float(debt_df['total_debt'].iloc[0]) if not debt_df.empty else 0
            except Exception:
                total_debt = 0

            # Owner comparison
            current_month_str = f"{year}-{month:02d}"
            prev_month_str = f"{year-1}-12" if month == 1 else f"{year}-{month-1:02d}"
            owner_df = _df(conn, f"""
                SELECT owner,
                    SUM(CASE WHEN TO_CHAR(date, 'YYYY-MM') = :current_month THEN amount ELSE 0 END) as current_month,
                    SUM(CASE WHEN TO_CHAR(date, 'YYYY-MM') = :prev_month THEN amount ELSE 0 END) as previous_month
                FROM transactions
                WHERE COALESCE(is_active, true) = true {uid_sql}
                GROUP BY owner
                HAVING SUM(CASE WHEN TO_CHAR(date, 'YYYY-MM') = :current_month THEN amount ELSE 0 END) > 0
                    OR SUM(CASE WHEN TO_CHAR(date, 'YYYY-MM') = :prev_month THEN amount ELSE 0 END) > 0
                ORDER BY current_month DESC
            """, {"current_month": current_month_str, "prev_month": prev_month_str, **uid_p})
            owner_comparison = []
            for _, row in owner_df.iterrows():
                current = float(row['current_month'])
                previous = float(row['previous_month'])
                change = ((current - previous) / previous * 100) if previous > 0 else 0
                owner_comparison.append({
                    'owner': row['owner'],
                    'current_month': current,
                    'previous_month': previous,
                    'change_percent': change
                })

        month_change = ((current_total - prev_year_total) / prev_year_total * 100) if prev_year_total > 0 else 0
        ytd_change = ((ytd_total - prev_ytd_total) / prev_ytd_total * 100) if prev_ytd_total > 0 else 0

        return render_template('enhanced_dashboard.html',
                             view='overview',
                             current_year=year, current_month=month, current_owner=owner,
                             available_years=available_years, available_owners=available_owners,
                             monthly_spending=monthly_spending,
                             top_categories=top_categories,
                             current_total=current_total,
                             prev_year_total=prev_year_total,
                             month_change=month_change,
                             ytd_total=ytd_total,
                             prev_ytd_total=prev_ytd_total,
                             ytd_change=ytd_change,
                             budget_performance={
                                 'over_budget_count': over_budget_count,
                                 'under_budget_count': under_budget_count,
                                 'on_track_count': on_track_count
                             },
                             recent_transactions=recent_transactions,
                             monthly_trend=monthly_trend,
                             total_debt=total_debt,
                             owner_comparison=owner_comparison,
                             yearly_data={}, category_trends={}, monthly_data=[],
                             budget_analysis=[], categories_data=[],
                             total_initial_budget=0, total_effective_budget=0,
                             total_unexpected_expenses=0, total_actual_spending=0)

    except Exception as e:
        print(f"Error in enhanced overview view: {e}")
        import traceback
        traceback.print_exc()
        return render_template('enhanced_dashboard.html',
                             view='overview', current_year=year, current_month=month,
                             current_owner=owner, available_years=available_years,
                             available_owners=available_owners,
                             current_total=0, prev_year_total=0, month_change=0,
                             ytd_total=0, prev_ytd_total=0, ytd_change=0,
                             monthly_spending=[], top_categories=[],
                             budget_performance={'over_budget_count': 0, 'under_budget_count': 0, 'on_track_count': 0},
                             recent_transactions=[], monthly_trend=[], total_debt=0,
                             owner_comparison=[], yearly_data={}, category_trends={},
                             monthly_data=[], budget_analysis=[], categories_data=[],
                             total_initial_budget=0, total_effective_budget=0,
                             total_unexpected_expenses=0, total_actual_spending=0,
                             error=str(e))


def dashboard_budget_view(year, month, owner, available_years, available_owners):
    """Dashboard Budget Management"""

    try:
        uid_sql, uid_p = uid_clause()
        with db.engine.connect() as conn:
            spending_filter = "EXTRACT(MONTH FROM date)::integer = :month AND EXTRACT(YEAR FROM date)::integer = :year"
            spending_params = {"month": month, "year": year}
            if owner != 'all':
                spending_filter += " AND owner = :owner"
                spending_params["owner"] = owner
            spending_filter += f" {uid_sql}"
            spending_params.update(uid_p)

            actual_spending_df = _df(conn, f"""
                SELECT category, sub_category, SUM(amount) as actual_amount, COUNT(*) as transaction_count
                FROM transactions
                WHERE {spending_filter}
                AND sub_category IS NOT NULL AND sub_category != ''
                AND COALESCE(type, '') != ''
                AND COALESCE(is_active, true) = true
                GROUP BY category, sub_category
                ORDER BY category, sub_category
            """, spending_params)

            subcategory_budgets_df = _df(conn, f"""
                SELECT category, sub_category, budget_amount, notes, budget_by_category
                FROM budget_subcategory_templates
                WHERE is_active = true AND budget_amount > 0 {uid_sql}
                ORDER BY category, sub_category
            """, uid_p)

            category_budget_mode = {}
            for _, row in subcategory_budgets_df.iterrows():
                if row['category'] not in category_budget_mode:
                    category_budget_mode[row['category']] = bool(row['budget_by_category'])

            commitments_df = _df(conn, f"""
                SELECT COALESCE(SUM(estimated_amount), 0) as total_commitments,
                       COALESCE(SUM(CASE WHEN is_fixed = true THEN estimated_amount ELSE 0 END), 0) as total_fixed,
                       COALESCE(SUM(CASE WHEN is_fixed = false THEN estimated_amount ELSE 0 END), 0) as total_variable,
                       COUNT(*) as count
                FROM budget_commitments WHERE is_active = true {uid_sql}
            """, uid_p)

            unexpected_expenses_df = _df(conn, f"""
                SELECT category, SUM(amount) as total_unexpected
                FROM unexpected_expenses
                WHERE month = :month AND year = :year AND is_active = true {uid_sql}
                GROUP BY category ORDER BY category
            """, {"month": month, "year": year, **uid_p})

        # Build budget analysis
        subcategory_budget_dict = {}
        for _, row in subcategory_budgets_df.iterrows():
            key = f"{row['category']}|{row['sub_category']}"
            subcategory_budget_dict[key] = float(row['budget_amount'])

        actual_spending_dict = {}
        for _, row in actual_spending_df.iterrows():
            key = f"{row['category']}|{row['sub_category']}"
            actual_spending_dict[key] = float(row['actual_amount'])

        unexpected_expenses_dict = {row['category']: float(row['total_unexpected'])
                                    for _, row in unexpected_expenses_df.iterrows()}

        all_subcategories = set(subcategory_budget_dict.keys()) | set(actual_spending_dict.keys())

        category_groups = {}
        for subcat_key in sorted(all_subcategories):
            category, sub_category = subcat_key.split('|')
            budget_amount = subcategory_budget_dict.get(subcat_key, 0.0)
            actual_spending = actual_spending_dict.get(subcat_key, 0.0)
            variance = actual_spending - budget_amount
            variance_pct = (variance / budget_amount * 100) if budget_amount > 0 else 0

            if budget_amount == 0 and actual_spending > 0:
                status = 'over'
            elif budget_amount == 0 and actual_spending == 0:
                status = 'no_budget'
            elif variance > 20:
                status = 'over'
            elif variance < -20:
                status = 'under'
            else:
                status = 'on_track'

            subcat_data = {
                'sub_category': sub_category,
                'budget_amount': budget_amount,
                'actual_spending': actual_spending,
                'variance': variance,
                'variance_pct': variance_pct,
                'status': status
            }

            if category not in category_groups:
                category_groups[category] = {
                    'category': category,
                    'subcategories': [],
                    'total_budget': 0,
                    'total_actual': 0,
                    'unexpected_expenses': unexpected_expenses_dict.get(category, 0.0)
                }
            category_groups[category]['subcategories'].append(subcat_data)
            category_groups[category]['total_budget'] += budget_amount
            category_groups[category]['total_actual'] += actual_spending

        budget_analysis = []
        for cat_data in category_groups.values():
            category = cat_data['category']
            is_category_level = category_budget_mode.get(category, False)
            initial_budget = cat_data['total_budget']
            unexpected = cat_data['unexpected_expenses']
            effective_budget = initial_budget + unexpected
            actual_spending = cat_data['total_actual']
            variance = actual_spending - effective_budget

            if effective_budget == 0 and actual_spending > 0:
                status = 'over'
            elif effective_budget == 0 and actual_spending == 0:
                status = 'no_budget'
            elif variance > 50:
                status = 'over'
            elif variance < -50:
                status = 'under'
            else:
                status = 'on_track'

            budget_analysis.append({
                'category': category,
                'initial_budget': initial_budget,
                'unexpected_expenses': unexpected,
                'effective_budget': effective_budget,
                'actual_spending': actual_spending,
                'variance': variance,
                'status': status,
                'subcategories': cat_data['subcategories'],
                'budget_by_category': is_category_level
            })

        total_budget = sum(item['initial_budget'] for item in budget_analysis)
        total_unexpected_expenses = sum(item['unexpected_expenses'] for item in budget_analysis)
        total_effective_budget = total_budget + total_unexpected_expenses
        total_actual_spending = sum(item['actual_spending'] for item in budget_analysis)

        total_commitments = float(commitments_df['total_commitments'].iloc[0]) if not commitments_df.empty else 0.0
        total_fixed_commitments = float(commitments_df['total_fixed'].iloc[0]) if not commitments_df.empty else 0.0
        total_variable_commitments = float(commitments_df['total_variable'].iloc[0]) if not commitments_df.empty else 0.0
        commitment_count = int(commitments_df['count'].iloc[0]) if not commitments_df.empty else 0
        living_budget = total_budget - total_commitments

        return render_template('enhanced_dashboard.html',
                             view='budget', current_year=year, current_month=month,
                             current_owner=owner, available_years=available_years,
                             available_owners=available_owners,
                             budget_analysis=budget_analysis,
                             total_initial_budget=total_budget,
                             total_unexpected_expenses=total_unexpected_expenses,
                             total_effective_budget=total_effective_budget,
                             total_actual_spending=total_actual_spending,
                             total_commitments=total_commitments,
                             total_fixed_commitments=total_fixed_commitments,
                             total_variable_commitments=total_variable_commitments,
                             commitment_count=commitment_count,
                             living_budget=living_budget,
                             current_total=0, prev_year_total=0, month_change=0,
                             ytd_total=0, prev_ytd_total=0, ytd_change=0,
                             monthly_spending=[], top_categories=[],
                             yearly_data={}, category_trends={}, monthly_data=[], categories_data=[])

    except Exception as e:
        print(f"Error in budget view: {e}")
        import traceback
        traceback.print_exc()
        return render_template('enhanced_dashboard.html',
                             view='budget', current_year=year, current_month=month,
                             current_owner=owner, available_years=available_years,
                             available_owners=available_owners,
                             budget_analysis=[], total_initial_budget=0,
                             total_unexpected_expenses=0, total_effective_budget=0,
                             total_actual_spending=0, total_commitments=0,
                             total_fixed_commitments=0, total_variable_commitments=0,
                             commitment_count=0, living_budget=0,
                             current_total=0, prev_year_total=0, month_change=0,
                             ytd_total=0, prev_ytd_total=0, ytd_change=0,
                             monthly_spending=[], top_categories=[],
                             yearly_data={}, category_trends={}, monthly_data=[],
                             categories_data=[],
                             budget_performance={'over_budget_count': 0, 'under_budget_count': 0, 'on_track_count': 0},
                             recent_transactions=[], monthly_trend=[], total_debt=0,
                             owner_comparison=[], error=str(e))


def dashboard_categories_view(available_years, available_owners):
    """Dashboard Categories Management"""
    try:
        current_year = request.args.get('year', datetime.now().year, type=int)
        current_month = request.args.get('month', 'all')
        uid_sql, uid_p = uid_clause()

        with db.engine.connect() as conn:
            categories_rows = conn.execute(text(f"""
                SELECT id, category, notes, budget_amount, is_active
                FROM budget_templates
                WHERE is_active = true AND category IS NOT NULL {uid_sql}
                ORDER BY category
            """), uid_p).fetchall()

            categories_data = []
            for cat_row in categories_rows:
                cat_id, category_name, notes, budget_amount, is_active = cat_row
                if current_month == 'all':
                    stats = conn.execute(text(f"""
                        SELECT COUNT(*) as count, SUM(amount) as total, AVG(amount) as avg
                        FROM transactions
                        WHERE category = :category
                        AND EXTRACT(YEAR FROM date)::integer = :year {uid_sql}
                    """), {"category": category_name, "year": current_year, **uid_p}).fetchone()
                else:
                    stats = conn.execute(text(f"""
                        SELECT COUNT(*) as count, SUM(amount) as total, AVG(amount) as avg
                        FROM transactions
                        WHERE category = :category
                        AND EXTRACT(YEAR FROM date)::integer = :year
                        AND EXTRACT(MONTH FROM date)::integer = :month {uid_sql}
                    """), {"category": category_name, "year": current_year, "month": int(current_month), **uid_p}).fetchone()

                categories_data.append({
                    'category': category_name,
                    'type': notes or '',
                    'transactions': stats[0] or 0,
                    'total_amount': float(stats[1]) if stats[1] else 0.0,
                    'average': float(stats[2]) if stats[2] else 0.0,
                    'budget': float(budget_amount) if budget_amount else 0.0
                })

        return render_template('enhanced_dashboard.html',
                             view='categories', current_year=current_year,
                             current_month=current_month, current_owner='all',
                             available_years=available_years, available_owners=available_owners,
                             categories_data=categories_data,
                             current_total=0, prev_year_total=0, month_change=0,
                             ytd_total=0, prev_ytd_total=0, ytd_change=0,
                             monthly_spending=[], top_categories=[],
                             yearly_data={}, category_trends={}, monthly_data=[],
                             budget_analysis=[], total_initial_budget=0,
                             total_effective_budget=0, total_unexpected_expenses=0,
                             total_actual_spending=0)

    except Exception as e:
        print(f"Error in categories view: {e}")
        import traceback
        traceback.print_exc()
        return render_template('enhanced_dashboard.html',
                             view='categories', current_year=datetime.now().year,
                             current_month='all', current_owner='all',
                             available_years=available_years, available_owners=available_owners,
                             categories_data=[],
                             current_total=0, prev_year_total=0, month_change=0,
                             ytd_total=0, prev_ytd_total=0, ytd_change=0,
                             monthly_spending=[], top_categories=[],
                             yearly_data={}, category_trends={}, monthly_data=[],
                             budget_analysis=[], total_initial_budget=0,
                             total_effective_budget=0, total_unexpected_expenses=0,
                             total_actual_spending=0, error=str(e))
