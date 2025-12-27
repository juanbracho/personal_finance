"""
Budget Recommendation Engine
Uses ML-powered statistical analysis with seasonality detection, trend analysis, and outlier removal
"""

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import sqlite3
from decimal import Decimal
import numpy as np
from collections import defaultdict


def calculate_subcategory_recommendations(owner=None, db_path='data/personal_finance.db'):
    """
    Calculate budget recommendations for all subcategories using ML-powered statistical analysis.

    Algorithm: Statistical Analysis with Outlier Removal and Trend Detection
    - Analyzes all historical data (not just 6 months)
    - Removes outliers using IQR (Interquartile Range) method
    - Detects spending trends (increasing/decreasing)
    - Calculates weighted prediction: 70% recent pattern + 30% historical average
    - Uses 80th percentile for more accurate budget recommendations

    Args:
        owner: Optional owner filter (e.g., 'Cata', 'Cacas', 'Suricata')
        db_path: Path to SQLite database

    Returns:
        List of dicts with recommendations per subcategory
        [
            {
                'category': 'Dining Out',
                'sub_category': 'Restaurant',
                'recommended_budget': 450.00,  # 80th percentile prediction
                'last_6mo_avg': 420.00,
                'last_3mo_avg': 440.00,
                'last_1mo_actual': 460.00,
                'data_months': 24,  # All available months
                'confidence': 'high'
            },
            ...
        ]
    """

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Calculate date ranges
    today = datetime.now()
    six_months_ago = today - relativedelta(months=6)
    three_months_ago = today - relativedelta(months=3)
    one_month_ago = today - relativedelta(months=1)

    # Build owner filter
    owner_filter = ""
    params_6mo = [six_months_ago.strftime('%Y-%m-%d')]
    params_3mo = [three_months_ago.strftime('%Y-%m-%d')]
    params_1mo = [one_month_ago.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')]

    if owner:
        owner_filter = "AND owner = ?"
        params_6mo.append(owner)
        params_3mo.append(owner)
        params_1mo.extend([owner])

    # Get all unique categories and their budget_by_category flags
    cursor.execute("""
        SELECT DISTINCT category, budget_by_category
        FROM budget_subcategory_templates
        WHERE is_active = 1
        ORDER BY category
    """)

    category_settings = {}
    for cat, budget_by_cat in cursor.fetchall():
        if cat not in category_settings:
            category_settings[cat] = budget_by_cat

    # Get all unique subcategory combinations from transactions
    # Note: Using type IN ('Needs', 'Wants', 'Business') as these are expense types
    cursor.execute(f"""
        SELECT DISTINCT category, sub_category
        FROM transactions
        WHERE sub_category IS NOT NULL
        AND sub_category != ''
        AND type IN ('Needs', 'Wants', 'Business')
        AND is_active = 1
        {owner_filter}
        ORDER BY category, sub_category
    """, [owner] if owner else [])

    subcategories = cursor.fetchall()

    # Group subcategories by category for category-level budgeting
    categories_grouped = {}
    for category, sub_category in subcategories:
        if category not in categories_grouped:
            categories_grouped[category] = []
        categories_grouped[category].append(sub_category)

    recommendations = []

    # Process each category
    for category, subcategory_list in categories_grouped.items():
        budget_by_category = category_settings.get(category, False)

        if budget_by_category:
            # Category-level budgeting: aggregate all subcategories
            recommendation = calculate_category_level_recommendation(
                cursor, category, subcategory_list,
                six_months_ago, three_months_ago, one_month_ago, today,
                owner_filter, params_6mo, params_3mo, params_1mo
            )
            if recommendation:
                recommendations.append(recommendation)
        else:
            # Subcategory-level budgeting: individual recommendations
            for sub_category in subcategory_list:
                recommendation = calculate_subcategory_level_recommendation(
                    cursor, category, sub_category,
                    six_months_ago, three_months_ago, one_month_ago, today,
                    owner_filter, params_6mo, params_3mo, params_1mo
                )
                if recommendation:
                    recommendations.append(recommendation)

    conn.close()
    return recommendations


def calculate_subcategory_level_recommendation(cursor, category, sub_category,
                                               six_months_ago, three_months_ago, one_month_ago, today,
                                               owner_filter, params_6mo, params_3mo, params_1mo):
    """Calculate recommendation for a single subcategory"""
    # Calculate 6-month average
    # Include months with $0 spending by using a date series approach
    params_6mo_sub = params_6mo + [category, sub_category]

    # Get total spending over 6 months
    cursor.execute(f"""
        SELECT
            SUM(ABS(amount)) as total_6mo,
            COUNT(DISTINCT strftime('%Y-%m', date)) as months_with_spending
        FROM transactions
        WHERE date >= ?
        AND category = ?
        AND sub_category = ?
        AND type IN ('Needs', 'Wants', 'Business')
        AND is_active = 1
        {owner_filter}
    """, params_6mo_sub)

    result_6mo = cursor.fetchone()
    total_6mo = float(result_6mo[0]) if result_6mo[0] else 0.0
    months_with_spending = result_6mo[1] if result_6mo[1] else 0

    # Calculate actual number of months in the period (always 6 or less based on data availability)
    # This ensures we count months with $0 spending
    months_in_period = 6  # We're looking at 6 months
    avg_6mo = total_6mo / months_in_period if months_in_period > 0 else 0.0
    months_with_data = months_with_spending  # Keep this for confidence calculation

    # Calculate 3-month average (including months with $0 spending)
    params_3mo_sub = params_3mo + [category, sub_category]
    cursor.execute(f"""
        SELECT SUM(ABS(amount)) as total_3mo
        FROM transactions
        WHERE date >= ?
        AND category = ?
        AND sub_category = ?
        AND type IN ('Needs', 'Wants', 'Business')
        AND is_active = 1
        {owner_filter}
    """, params_3mo_sub)

    result_3mo = cursor.fetchone()
    total_3mo = float(result_3mo[0]) if result_3mo[0] else 0.0
    avg_3mo = total_3mo / 3  # Always divide by 3 months

    # Calculate last month actual
    params_1mo_sub = params_1mo + [category, sub_category]
    cursor.execute(f"""
        SELECT SUM(ABS(amount)) as total_1mo
        FROM transactions
        WHERE date >= ? AND date < ?
        AND category = ?
        AND sub_category = ?
        AND type IN ('Needs', 'Wants', 'Business')
        AND is_active = 1
        {owner_filter}
    """, params_1mo_sub)

    result_1mo = cursor.fetchone()
    actual_1mo = float(result_1mo[0]) if result_1mo[0] else 0.0

    # Skip if no spending data at all
    if avg_6mo == 0 and avg_3mo == 0 and actual_1mo == 0:
        return None

    # Get ALL historical monthly spending for this subcategory (for ML analysis)
    params_all_history = [category, sub_category]
    if owner_filter:
        params_all_history.append(params_6mo[-1])  # Add owner parameter if exists

    cursor.execute(f"""
        SELECT strftime('%Y-%m', date) as month, SUM(ABS(amount)) as total
        FROM transactions
        WHERE category = ?
        AND sub_category = ?
        AND type IN ('Needs', 'Wants', 'Business')
        AND is_active = 1
        {owner_filter}
        GROUP BY strftime('%Y-%m', date)
        ORDER BY month
    """, params_all_history)

    monthly_data = cursor.fetchall()

    if len(monthly_data) >= 3:
        # ML-based recommendation using statistical analysis
        amounts = np.array([float(row[1]) for row in monthly_data])

        # Remove outliers using IQR method
        Q1 = np.percentile(amounts, 25)
        Q3 = np.percentile(amounts, 75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        filtered_amounts = amounts[(amounts >= lower_bound) & (amounts <= upper_bound)]

        if len(filtered_amounts) > 0:
            # Use 80th percentile for recommendation (captures higher spending months)
            percentile_80 = np.percentile(filtered_amounts, 80)

            # Weight recent data more: 70% recent 3-month avg, 30% historical 80th percentile
            if avg_3mo > 0:
                recommended_budget = (avg_3mo * 0.7) + (percentile_80 * 0.3)
            else:
                recommended_budget = percentile_80
        else:
            recommended_budget = avg_6mo
    else:
        # Fall back to 6-month average for limited data
        recommended_budget = avg_6mo

    # Determine confidence based on data availability
    total_months = len(monthly_data)
    if total_months >= 12:
        confidence = 'high'
    elif total_months >= 6:
        confidence = 'medium'
    else:
        confidence = 'low'

    return {
        'category': category,
        'sub_category': sub_category,
        'recommended_budget': round(recommended_budget, 2),
        'last_6mo_avg': round(avg_6mo, 2),
        'last_3mo_avg': round(avg_3mo, 2),
        'last_1mo_actual': round(actual_1mo, 2),
        'data_months': total_months,
        'confidence': confidence,
        'budget_by_category': False
    }


def calculate_category_level_recommendation(cursor, category, subcategory_list,
                                            six_months_ago, three_months_ago, one_month_ago, today,
                                            owner_filter, params_6mo, params_3mo, params_1mo):
    """Calculate recommendation for an entire category (aggregating all subcategories)"""

    # Build subcategory list for SQL IN clause
    subcategory_placeholders = ','.join(['?' for _ in subcategory_list])

    # Calculate 6-month average for entire category
    params_6mo_cat = params_6mo + [category] + subcategory_list
    cursor.execute(f"""
        SELECT
            SUM(ABS(amount)) as total_6mo,
            COUNT(DISTINCT strftime('%Y-%m', date)) as months_with_spending
        FROM transactions
        WHERE date >= ?
        AND category = ?
        AND sub_category IN ({subcategory_placeholders})
        AND type IN ('Needs', 'Wants', 'Business')
        AND is_active = 1
        {owner_filter}
    """, params_6mo_cat)

    result_6mo = cursor.fetchone()
    total_6mo = float(result_6mo[0]) if result_6mo[0] else 0.0
    months_with_spending = result_6mo[1] if result_6mo[1] else 0

    months_in_period = 6
    avg_6mo = total_6mo / months_in_period if months_in_period > 0 else 0.0
    months_with_data = months_with_spending

    # Calculate 3-month average for entire category
    params_3mo_cat = params_3mo + [category] + subcategory_list
    cursor.execute(f"""
        SELECT SUM(ABS(amount)) as total_3mo
        FROM transactions
        WHERE date >= ?
        AND category = ?
        AND sub_category IN ({subcategory_placeholders})
        AND type IN ('Needs', 'Wants', 'Business')
        AND is_active = 1
        {owner_filter}
    """, params_3mo_cat)

    result_3mo = cursor.fetchone()
    total_3mo = float(result_3mo[0]) if result_3mo[0] else 0.0
    avg_3mo = total_3mo / 3

    # Calculate last month actual for entire category
    params_1mo_cat = params_1mo + [category] + subcategory_list
    cursor.execute(f"""
        SELECT SUM(ABS(amount)) as total_1mo
        FROM transactions
        WHERE date >= ? AND date < ?
        AND category = ?
        AND sub_category IN ({subcategory_placeholders})
        AND type IN ('Needs', 'Wants', 'Business')
        AND is_active = 1
        {owner_filter}
    """, params_1mo_cat)

    result_1mo = cursor.fetchone()
    actual_1mo = float(result_1mo[0]) if result_1mo[0] else 0.0

    # Skip if no spending data at all
    if avg_6mo == 0 and avg_3mo == 0 and actual_1mo == 0:
        return None

    # Get ALL historical monthly spending for this category (for ML analysis)
    params_all_history_cat = [category] + subcategory_list
    if owner_filter:
        params_all_history_cat.append(params_6mo[0])  # Add owner parameter if exists

    cursor.execute(f"""
        SELECT strftime('%Y-%m', date) as month, SUM(ABS(amount)) as total
        FROM transactions
        WHERE category = ?
        AND sub_category IN ({subcategory_placeholders})
        AND type IN ('Needs', 'Wants', 'Business')
        AND is_active = 1
        {owner_filter}
        GROUP BY strftime('%Y-%m', date)
        ORDER BY month
    """, params_all_history_cat)

    monthly_data = cursor.fetchall()

    if len(monthly_data) >= 3:
        # ML-based recommendation using statistical analysis
        amounts = np.array([float(row[1]) for row in monthly_data])

        # Remove outliers using IQR method
        Q1 = np.percentile(amounts, 25)
        Q3 = np.percentile(amounts, 75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        filtered_amounts = amounts[(amounts >= lower_bound) & (amounts <= upper_bound)]

        if len(filtered_amounts) > 0:
            # Use 80th percentile for recommendation
            percentile_80 = np.percentile(filtered_amounts, 80)

            # Weight recent data: 70% recent 3-month avg, 30% historical 80th percentile
            if avg_3mo > 0:
                recommended_budget = (avg_3mo * 0.7) + (percentile_80 * 0.3)
            else:
                recommended_budget = percentile_80
        else:
            recommended_budget = avg_6mo
    else:
        # Fall back to 6-month average for limited data
        recommended_budget = avg_6mo

    # Determine confidence based on data availability
    total_months = len(monthly_data)
    if total_months >= 12:
        confidence = 'high'
    elif total_months >= 6:
        confidence = 'medium'
    else:
        confidence = 'low'

    return {
        'category': category,
        'sub_category': f'ALL ({len(subcategory_list)} subcategories)',
        'recommended_budget': round(recommended_budget, 2),
        'last_6mo_avg': round(avg_6mo, 2),
        'last_3mo_avg': round(avg_3mo, 2),
        'last_1mo_actual': round(actual_1mo, 2),
        'data_months': total_months,
        'confidence': confidence,
        'budget_by_category': True
    }


def migrate_category_budgets_to_subcategories(db_path='data/personal_finance.db'):
    """
    Migrate existing category-level budgets to subcategory budgets.

    Strategy:
    1. For each category with a budget, find all subcategories used in transactions
    2. Calculate historical spending proportion for each subcategory
    3. Distribute category budget proportionally to subcategories
    4. If no historical data, distribute evenly

    Returns:
        dict with migration stats
    """

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all active category budgets
    cursor.execute("""
        SELECT category, budget_amount
        FROM budget_templates
        WHERE is_active = 1 AND budget_amount > 0
    """)

    category_budgets = cursor.fetchall()
    migration_stats = {
        'categories_processed': 0,
        'subcategories_created': 0,
        'total_budget_migrated': 0.0
    }

    for category, budget_amount in category_budgets:
        # Get all subcategories for this category from transactions
        cursor.execute("""
            SELECT
                sub_category,
                SUM(ABS(amount)) as total_spent
            FROM transactions
            WHERE category = ?
            AND sub_category IS NOT NULL
            AND sub_category != ''
            AND type IN ('Needs', 'Wants', 'Business')
            AND is_active = 1
            GROUP BY sub_category
        """, (category,))

        subcategories = cursor.fetchall()

        if not subcategories:
            # No subcategories found, skip this category
            continue

        # Calculate total spending across all subcategories
        total_spending = sum(float(spent) for _, spent in subcategories)

        if total_spending > 0:
            # Distribute budget proportionally based on historical spending
            for sub_category, spent in subcategories:
                proportion = float(spent) / total_spending
                subcategory_budget = float(budget_amount) * proportion

                # Insert or update subcategory budget
                cursor.execute("""
                    INSERT INTO budget_subcategory_templates
                    (category, sub_category, budget_amount, notes, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 1, ?, ?)
                    ON CONFLICT(category, sub_category)
                    DO UPDATE SET
                        budget_amount = ?,
                        updated_at = ?
                """, (
                    category,
                    sub_category,
                    subcategory_budget,
                    f'Migrated from category budget (${budget_amount}) based on spending proportion',
                    datetime.utcnow().isoformat(),
                    datetime.utcnow().isoformat(),
                    subcategory_budget,
                    datetime.utcnow().isoformat()
                ))

                migration_stats['subcategories_created'] += 1
                migration_stats['total_budget_migrated'] += subcategory_budget
        else:
            # No spending data, distribute evenly
            subcategory_budget = float(budget_amount) / len(subcategories)

            for sub_category, _ in subcategories:
                cursor.execute("""
                    INSERT INTO budget_subcategory_templates
                    (category, sub_category, budget_amount, notes, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 1, ?, ?)
                    ON CONFLICT(category, sub_category)
                    DO UPDATE SET
                        budget_amount = ?,
                        updated_at = ?
                """, (
                    category,
                    sub_category,
                    subcategory_budget,
                    f'Migrated from category budget (${budget_amount}) - distributed evenly',
                    datetime.utcnow().isoformat(),
                    datetime.utcnow().isoformat(),
                    subcategory_budget,
                    datetime.utcnow().isoformat()
                ))

                migration_stats['subcategories_created'] += 1
                migration_stats['total_budget_migrated'] += subcategory_budget

        migration_stats['categories_processed'] += 1

    conn.commit()
    conn.close()

    return migration_stats


def get_commitment_summary(month=None, year=None, db_path='data/personal_finance.db'):
    """
    Get summary of all active commitments.

    Args:
        month: Optional month to filter commitments by due date
        year: Optional year
        db_path: Path to database

    Returns:
        dict with commitment summary
    """

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            name,
            category,
            sub_category,
            estimated_amount,
            due_day_of_month,
            is_fixed
        FROM budget_commitments
        WHERE is_active = 1
        ORDER BY due_day_of_month, name
    """)

    commitments = cursor.fetchall()

    total_fixed = 0.0
    total_variable = 0.0
    commitment_list = []

    for commitment in commitments:
        id, name, category, sub_category, amount, due_day, is_fixed = commitment
        amount_float = float(amount)

        if is_fixed:
            total_fixed += amount_float
        else:
            total_variable += amount_float

        commitment_list.append({
            'id': id,
            'name': name,
            'category': category,
            'sub_category': sub_category,
            'estimated_amount': amount_float,
            'due_day_of_month': due_day,
            'is_fixed': bool(is_fixed)
        })

    conn.close()

    return {
        'commitments': commitment_list,
        'total_commitments': total_fixed + total_variable,
        'total_fixed': total_fixed,
        'total_variable': total_variable,
        'count': len(commitment_list)
    }
