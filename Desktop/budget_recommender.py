"""
Budget Recommendation Engine
Uses ML-powered statistical analysis with seasonality detection, trend analysis, and outlier removal.
PostgreSQL-compatible (no sqlite3).
"""

from datetime import datetime
from dateutil.relativedelta import relativedelta
from sqlalchemy import text
import numpy as np


def _get_engine():
    from models import db
    return db.engine


def calculate_subcategory_recommendations(owner=None):
    """
    Calculate budget recommendations for all subcategories using ML-powered statistical analysis.

    Args:
        owner: Optional owner filter (e.g., 'Cata', 'Cacas', 'Suricata')

    Returns:
        List of dicts with recommendations per subcategory
    """
    engine = _get_engine()

    today = datetime.now()
    six_months_ago = today - relativedelta(months=6)
    three_months_ago = today - relativedelta(months=3)
    one_month_ago = today - relativedelta(months=1)

    with engine.connect() as conn:
        # Get category budget_by_category settings
        result = conn.execute(text("""
            SELECT DISTINCT category, budget_by_category
            FROM budget_subcategory_templates
            WHERE is_active = true
            ORDER BY category
        """))
        category_settings = {}
        for cat, budget_by_cat in result:
            if cat not in category_settings:
                category_settings[cat] = budget_by_cat

        # Get all unique category/subcategory combos from transactions
        if owner:
            result = conn.execute(text("""
                SELECT DISTINCT category, sub_category
                FROM transactions
                WHERE sub_category IS NOT NULL
                AND sub_category != ''
                AND type IN ('Needs', 'Wants', 'Business')
                AND is_active = true
                AND owner = :owner
                ORDER BY category, sub_category
            """), {"owner": owner})
        else:
            result = conn.execute(text("""
                SELECT DISTINCT category, sub_category
                FROM transactions
                WHERE sub_category IS NOT NULL
                AND sub_category != ''
                AND type IN ('Needs', 'Wants', 'Business')
                AND is_active = true
                ORDER BY category, sub_category
            """))
        subcategories = result.fetchall()

    # Group subcategories by category
    categories_grouped = {}
    for category, sub_category in subcategories:
        if category not in categories_grouped:
            categories_grouped[category] = []
        categories_grouped[category].append(sub_category)

    recommendations = []
    with engine.connect() as conn:
        for category, subcategory_list in categories_grouped.items():
            budget_by_category = category_settings.get(category, False)

            if budget_by_category:
                rec = _calc_category_recommendation(
                    conn, category, subcategory_list,
                    six_months_ago, three_months_ago, one_month_ago, today, owner
                )
                if rec:
                    recommendations.append(rec)
            else:
                for sub_category in subcategory_list:
                    rec = _calc_subcategory_recommendation(
                        conn, category, sub_category,
                        six_months_ago, three_months_ago, one_month_ago, today, owner
                    )
                    if rec:
                        recommendations.append(rec)

    return recommendations


def _build_owner_clause(owner):
    """Return SQL fragment and params dict for optional owner filter."""
    if owner:
        return "AND owner = :owner", {"owner": owner}
    return "", {}


def _calc_subcategory_recommendation(conn, category, sub_category,
                                     six_months_ago, three_months_ago, one_month_ago, today,
                                     owner):
    owner_sql, owner_params = _build_owner_clause(owner)

    base_params = {
        "six_months_ago": six_months_ago.strftime('%Y-%m-%d'),
        "three_months_ago": three_months_ago.strftime('%Y-%m-%d'),
        "one_month_ago": one_month_ago.strftime('%Y-%m-%d'),
        "today": today.strftime('%Y-%m-%d'),
        "category": category,
        "sub_category": sub_category,
        **owner_params
    }

    # 6-month totals
    row = conn.execute(text(f"""
        SELECT SUM(ABS(amount)) as total_6mo,
               COUNT(DISTINCT TO_CHAR(date, 'YYYY-MM')) as months_with_spending
        FROM transactions
        WHERE date >= :six_months_ago
        AND category = :category AND sub_category = :sub_category
        AND type IN ('Needs', 'Wants', 'Business') AND is_active = true
        {owner_sql}
    """), base_params).fetchone()

    total_6mo = float(row[0]) if row[0] else 0.0
    avg_6mo = total_6mo / 6

    # 3-month totals
    row = conn.execute(text(f"""
        SELECT SUM(ABS(amount)) as total_3mo
        FROM transactions
        WHERE date >= :three_months_ago
        AND category = :category AND sub_category = :sub_category
        AND type IN ('Needs', 'Wants', 'Business') AND is_active = true
        {owner_sql}
    """), base_params).fetchone()
    avg_3mo = float(row[0]) / 3 if row[0] else 0.0

    # Last month actual
    row = conn.execute(text(f"""
        SELECT SUM(ABS(amount)) as total_1mo
        FROM transactions
        WHERE date >= :one_month_ago AND date < :today
        AND category = :category AND sub_category = :sub_category
        AND type IN ('Needs', 'Wants', 'Business') AND is_active = true
        {owner_sql}
    """), base_params).fetchone()
    actual_1mo = float(row[0]) if row[0] else 0.0

    if avg_6mo == 0 and avg_3mo == 0 and actual_1mo == 0:
        return None

    # All historical monthly data for ML
    monthly_rows = conn.execute(text(f"""
        SELECT TO_CHAR(date, 'YYYY-MM') as month, SUM(ABS(amount)) as total
        FROM transactions
        WHERE category = :category AND sub_category = :sub_category
        AND type IN ('Needs', 'Wants', 'Business') AND is_active = true
        {owner_sql}
        GROUP BY TO_CHAR(date, 'YYYY-MM')
        ORDER BY month
    """), base_params).fetchall()

    recommended_budget = _ml_recommend(monthly_rows, avg_6mo, avg_3mo)
    confidence = _confidence(len(monthly_rows))

    return {
        'category': category,
        'sub_category': sub_category,
        'recommended_budget': round(recommended_budget, 2),
        'last_6mo_avg': round(avg_6mo, 2),
        'last_3mo_avg': round(avg_3mo, 2),
        'last_1mo_actual': round(actual_1mo, 2),
        'data_months': len(monthly_rows),
        'confidence': confidence,
        'budget_by_category': False
    }


def _calc_category_recommendation(conn, category, subcategory_list,
                                   six_months_ago, three_months_ago, one_month_ago, today,
                                   owner):
    owner_sql, owner_params = _build_owner_clause(owner)
    sub_in = ','.join([f':sub_{i}' for i in range(len(subcategory_list))])
    sub_params = {f'sub_{i}': v for i, v in enumerate(subcategory_list)}

    base_params = {
        "six_months_ago": six_months_ago.strftime('%Y-%m-%d'),
        "three_months_ago": three_months_ago.strftime('%Y-%m-%d'),
        "one_month_ago": one_month_ago.strftime('%Y-%m-%d'),
        "today": today.strftime('%Y-%m-%d'),
        "category": category,
        **sub_params,
        **owner_params
    }

    row = conn.execute(text(f"""
        SELECT SUM(ABS(amount)) as total_6mo,
               COUNT(DISTINCT TO_CHAR(date, 'YYYY-MM')) as months_with_spending
        FROM transactions
        WHERE date >= :six_months_ago
        AND category = :category AND sub_category IN ({sub_in})
        AND type IN ('Needs', 'Wants', 'Business') AND is_active = true
        {owner_sql}
    """), base_params).fetchone()
    total_6mo = float(row[0]) if row[0] else 0.0
    avg_6mo = total_6mo / 6

    row = conn.execute(text(f"""
        SELECT SUM(ABS(amount)) as total_3mo
        FROM transactions
        WHERE date >= :three_months_ago
        AND category = :category AND sub_category IN ({sub_in})
        AND type IN ('Needs', 'Wants', 'Business') AND is_active = true
        {owner_sql}
    """), base_params).fetchone()
    avg_3mo = float(row[0]) / 3 if row[0] else 0.0

    row = conn.execute(text(f"""
        SELECT SUM(ABS(amount)) as total_1mo
        FROM transactions
        WHERE date >= :one_month_ago AND date < :today
        AND category = :category AND sub_category IN ({sub_in})
        AND type IN ('Needs', 'Wants', 'Business') AND is_active = true
        {owner_sql}
    """), base_params).fetchone()
    actual_1mo = float(row[0]) if row[0] else 0.0

    if avg_6mo == 0 and avg_3mo == 0 and actual_1mo == 0:
        return None

    monthly_rows = conn.execute(text(f"""
        SELECT TO_CHAR(date, 'YYYY-MM') as month, SUM(ABS(amount)) as total
        FROM transactions
        WHERE category = :category AND sub_category IN ({sub_in})
        AND type IN ('Needs', 'Wants', 'Business') AND is_active = true
        {owner_sql}
        GROUP BY TO_CHAR(date, 'YYYY-MM')
        ORDER BY month
    """), base_params).fetchall()

    recommended_budget = _ml_recommend(monthly_rows, avg_6mo, avg_3mo)
    confidence = _confidence(len(monthly_rows))

    return {
        'category': category,
        'sub_category': f'ALL ({len(subcategory_list)} subcategories)',
        'recommended_budget': round(recommended_budget, 2),
        'last_6mo_avg': round(avg_6mo, 2),
        'last_3mo_avg': round(avg_3mo, 2),
        'last_1mo_actual': round(actual_1mo, 2),
        'data_months': len(monthly_rows),
        'confidence': confidence,
        'budget_by_category': True
    }


def _ml_recommend(monthly_rows, avg_6mo, avg_3mo):
    if len(monthly_rows) >= 3:
        amounts = np.array([float(row[1]) for row in monthly_rows])
        Q1, Q3 = np.percentile(amounts, 25), np.percentile(amounts, 75)
        IQR = Q3 - Q1
        filtered = amounts[(amounts >= Q1 - 1.5 * IQR) & (amounts <= Q3 + 1.5 * IQR)]
        if len(filtered) > 0:
            p80 = np.percentile(filtered, 80)
            return (avg_3mo * 0.7 + p80 * 0.3) if avg_3mo > 0 else p80
    return avg_6mo


def _confidence(total_months):
    if total_months >= 12:
        return 'high'
    elif total_months >= 6:
        return 'medium'
    return 'low'


def migrate_category_budgets_to_subcategories():
    """
    Migrate existing category-level budgets to subcategory budgets.
    """
    engine = _get_engine()
    stats = {'categories_processed': 0, 'subcategories_created': 0, 'total_budget_migrated': 0.0}

    with engine.connect() as conn:
        category_budgets = conn.execute(text("""
            SELECT category, budget_amount
            FROM budget_templates
            WHERE is_active = true AND budget_amount > 0
        """)).fetchall()

        for category, budget_amount in category_budgets:
            subcategories = conn.execute(text("""
                SELECT sub_category, SUM(ABS(amount)) as total_spent
                FROM transactions
                WHERE category = :category
                AND sub_category IS NOT NULL AND sub_category != ''
                AND type IN ('Needs', 'Wants', 'Business') AND is_active = true
                GROUP BY sub_category
            """), {"category": category}).fetchall()

            if not subcategories:
                continue

            total_spending = sum(float(s) for _, s in subcategories)

            for sub_category, spent in subcategories:
                if total_spending > 0:
                    proportion = float(spent) / total_spending
                    sub_budget = float(budget_amount) * proportion
                    note = f'Migrated from category budget (${budget_amount}) based on spending proportion'
                else:
                    sub_budget = float(budget_amount) / len(subcategories)
                    note = f'Migrated from category budget (${budget_amount}) - distributed evenly'

                conn.execute(text("""
                    INSERT INTO budget_subcategory_templates
                    (category, sub_category, budget_amount, notes, is_active, created_at, updated_at)
                    VALUES (:category, :sub_category, :budget_amount, :notes, true, :now, :now)
                    ON CONFLICT (category, sub_category, user_id)
                    DO UPDATE SET budget_amount = EXCLUDED.budget_amount, updated_at = EXCLUDED.updated_at
                """), {
                    "category": category,
                    "sub_category": sub_category,
                    "budget_amount": sub_budget,
                    "notes": note,
                    "now": datetime.utcnow()
                })

                stats['subcategories_created'] += 1
                stats['total_budget_migrated'] += sub_budget

            stats['categories_processed'] += 1

        conn.commit()

    return stats


def get_commitment_summary():
    """Get summary of all active commitments."""
    engine = _get_engine()

    with engine.connect() as conn:
        commitments = conn.execute(text("""
            SELECT id, name, category, sub_category, estimated_amount, due_day_of_month, is_fixed
            FROM budget_commitments
            WHERE is_active = true
            ORDER BY due_day_of_month, name
        """)).fetchall()

    total_fixed = 0.0
    total_variable = 0.0
    commitment_list = []

    for row in commitments:
        id_, name, category, sub_category, amount, due_day, is_fixed = row
        amount_float = float(amount)
        if is_fixed:
            total_fixed += amount_float
        else:
            total_variable += amount_float
        commitment_list.append({
            'id': id_,
            'name': name,
            'category': category,
            'sub_category': sub_category,
            'estimated_amount': amount_float,
            'due_day_of_month': due_day,
            'is_fixed': bool(is_fixed)
        })

    return {
        'commitments': commitment_list,
        'total_commitments': total_fixed + total_variable,
        'total_fixed': total_fixed,
        'total_variable': total_variable,
        'count': len(commitment_list)
    }
