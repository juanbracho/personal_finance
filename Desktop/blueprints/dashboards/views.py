from flask import render_template, request
from datetime import datetime
from utils import ensure_budget_tables
import pandas as pd
import sqlite3

def dashboard_overview_view(year, month, owner, available_years, available_owners):
    """Dashboard Overview - Enhanced with additional metrics"""
    
    try:
        conn = sqlite3.connect('data/personal_finance.db')
        
        # Build filter conditions
        date_filter = "strftime('%m', date) = ? AND strftime('%Y', date) = ?"
        params = [f"{month:02d}", str(year)]
        
        if owner != 'all':
            date_filter += " AND owner = ?"
            params.append(owner)
        
        # Monthly spending by type
        monthly_spending_query = f"""
        SELECT type, SUM(amount) as total, COUNT(*) as count
        FROM transactions 
        WHERE {date_filter} AND COALESCE(is_active, 1) = 1
        GROUP BY type
        ORDER BY total DESC
        """
        monthly_spending_df = pd.read_sql_query(monthly_spending_query, conn, params=params)
        monthly_spending = [(row['type'], float(row['total']), int(row['count'])) 
                           for _, row in monthly_spending_df.iterrows()]
        
        # Top 5 categories (instead of 10 for cleaner overview)
        top_categories_query = f"""
        SELECT category, SUM(amount) as total, COUNT(*) as count
        FROM transactions 
        WHERE {date_filter} AND COALESCE(is_active, 1) = 1
        GROUP BY category 
        ORDER BY total DESC 
        LIMIT 5
        """
        top_categories_df = pd.read_sql_query(top_categories_query, conn, params=params)
        top_categories = [(row['category'], float(row['total']), int(row['count'])) 
                         for _, row in top_categories_df.iterrows()]
        
        # Month comparison - same month previous year
        prev_year_params = [f"{month:02d}", str(year - 1)]
        if owner != 'all':
            prev_year_params.append(owner)
            
        prev_year_query = f"""
        SELECT SUM(amount) as total
        FROM transactions 
        WHERE {date_filter} AND COALESCE(is_active, 1) = 1
        """
        prev_year_df = pd.read_sql_query(prev_year_query, conn, params=prev_year_params)
        prev_year_total = float(prev_year_df['total'].iloc[0]) if not prev_year_df.empty and prev_year_df['total'].iloc[0] else 0
        
        # Current month total
        current_total = sum([amount for _, amount, _ in monthly_spending])
        
        # Year-to-date comparison
        ytd_filter = "strftime('%Y', date) = ? AND strftime('%m', date) <= ?"
        ytd_params = [str(year), f"{month:02d}"]
        if owner != 'all':
            ytd_filter += " AND owner = ?"
            ytd_params.append(owner)
            
        ytd_query = f"""
        SELECT SUM(amount) as total
        FROM transactions 
        WHERE {ytd_filter} AND COALESCE(is_active, 1) = 1
        """
        ytd_df = pd.read_sql_query(ytd_query, conn, params=ytd_params)
        ytd_total = float(ytd_df['total'].iloc[0]) if not ytd_df.empty and ytd_df['total'].iloc[0] else 0
        
        # Previous YTD
        prev_ytd_params = [str(year - 1), f"{month:02d}"]
        if owner != 'all':
            prev_ytd_params.append(owner)
            
        prev_ytd_df = pd.read_sql_query(ytd_query, conn, params=prev_ytd_params)
        prev_ytd_total = float(prev_ytd_df['total'].iloc[0]) if not prev_ytd_df.empty and prev_ytd_df['total'].iloc[0] else 0
        
        # NEW: Budget Performance Summary
        ensure_budget_tables(conn)
        
        # Get budget analysis for current month
        budget_performance_query = f"""
        SELECT 
            bt.category,
            bt.budget_amount,
            COALESCE(ue.total_unexpected, 0) as unexpected_expenses,
            COALESCE(actual.actual_amount, 0) as actual_spending
        FROM budget_templates bt
        LEFT JOIN (
            SELECT category, SUM(amount) as total_unexpected
            FROM unexpected_expenses 
            WHERE month = ? AND year = ? AND is_active = 1
            GROUP BY category
        ) ue ON bt.category = ue.category
        LEFT JOIN (
            SELECT category, SUM(amount) as actual_amount
            FROM transactions 
            WHERE {date_filter} AND COALESCE(is_active, 1) = 1
            GROUP BY category
        ) actual ON bt.category = actual.category
        WHERE bt.is_active = 1
        """
        budget_params = [month, year] + params
        budget_df = pd.read_sql_query(budget_performance_query, conn, params=budget_params)
        
        # Calculate budget performance
        over_budget_count = 0
        under_budget_count = 0
        on_track_count = 0
        
        for _, row in budget_df.iterrows():
            effective_budget = float(row['budget_amount']) + float(row['unexpected_expenses'])
            actual_spending = float(row['actual_spending'])
            variance = actual_spending - effective_budget
            
            if effective_budget > 0:
                if variance > 50:  # Over by more than $50
                    over_budget_count += 1
                elif variance < -50:  # Under by more than $50
                    under_budget_count += 1
                else:
                    on_track_count += 1
        
        # NEW: Recent Transactions (last 10)
        recent_transactions_query = f"""
        SELECT date, description, amount, category, owner, account_name
        FROM transactions 
        WHERE COALESCE(is_active, 1) = 1
        ORDER BY date DESC, created_at DESC
        LIMIT 10
        """
        recent_df = pd.read_sql_query(recent_transactions_query, conn)
        recent_transactions = []
        for _, row in recent_df.iterrows():
            recent_transactions.append({
                'date': row['date'],
                'description': row['description'],
                'amount': float(row['amount']),
                'category': row['category'],
                'owner': row['owner'],
                'account_name': row['account_name']
            })
        
        # NEW: 3-Month Spending Trend
        trend_query = f"""
        SELECT 
            strftime('%Y-%m', date) as month_year,
            SUM(amount) as total
        FROM transactions 
        WHERE date >= date('now', '-3 months') AND COALESCE(is_active, 1) = 1
        {f"AND owner = '{owner}'" if owner != 'all' else ''}
        GROUP BY strftime('%Y-%m', date)
        ORDER BY month_year DESC
        LIMIT 3
        """
        trend_df = pd.read_sql_query(trend_query, conn)
        monthly_trend = []
        for _, row in trend_df.iterrows():
            monthly_trend.append({
                'month': row['month_year'],
                'total': float(row['total'])
            })
        monthly_trend.reverse()  # Show oldest to newest
        
        # NEW: Total Debt (simple overview)
        try:
            debt_query = """
            SELECT COALESCE(SUM(current_balance), 0) as total_debt
            FROM debt_accounts 
            WHERE is_active = 1
            """
            debt_df = pd.read_sql_query(debt_query, conn)
            total_debt = float(debt_df['total_debt'].iloc[0]) if not debt_df.empty else 0
        except:
            total_debt = 0  # If debt_accounts table doesn't exist
        
        # NEW: Enhanced Owner Comparison
        owner_comparison_query = f"""
        SELECT 
            owner,
            SUM(CASE WHEN strftime('%Y-%m', date) = ? THEN amount ELSE 0 END) as current_month,
            SUM(CASE WHEN strftime('%Y-%m', date) = ? THEN amount ELSE 0 END) as previous_month
        FROM transactions 
        WHERE COALESCE(is_active, 1) = 1
        GROUP BY owner
        HAVING current_month > 0 OR previous_month > 0
        ORDER BY current_month DESC
        """
        current_month_str = f"{year}-{month:02d}"
        if month == 1:
            prev_month_str = f"{year-1}-12"
        else:
            prev_month_str = f"{year}-{month-1:02d}"
        
        owner_df = pd.read_sql_query(owner_comparison_query, conn, params=[current_month_str, prev_month_str])
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
        
        conn.close()
        
        # Calculate comparisons
        month_change = ((current_total - prev_year_total) / prev_year_total * 100) if prev_year_total > 0 else 0
        ytd_change = ((ytd_total - prev_ytd_total) / prev_ytd_total * 100) if prev_ytd_total > 0 else 0
        
        return render_template('enhanced_dashboard.html',
                             view='overview',
                             current_year=year,
                             current_month=month,
                             current_owner=owner,
                             available_years=available_years,
                             available_owners=available_owners,
                             monthly_spending=monthly_spending,
                             top_categories=top_categories,
                             current_total=current_total,
                             prev_year_total=prev_year_total,
                             month_change=month_change,
                             ytd_total=ytd_total,
                             prev_ytd_total=prev_ytd_total,
                             ytd_change=ytd_change,
                             # NEW: Enhanced metrics
                             budget_performance={
                                 'over_budget_count': over_budget_count,
                                 'under_budget_count': under_budget_count,
                                 'on_track_count': on_track_count
                             },
                             recent_transactions=recent_transactions,
                             monthly_trend=monthly_trend,
                             total_debt=total_debt,
                             owner_comparison=owner_comparison,
                             # Add required defaults for other views
                             yearly_data={},
                             category_trends={},
                             monthly_data=[],
                             budget_analysis=[],
                             categories_data=[],
                             total_initial_budget=0,
                             total_effective_budget=0,
                             total_unexpected_expenses=0,
                             total_actual_spending=0)
                             
    except Exception as e:
        print(f"❌ Error in enhanced overview view: {e}")
        import traceback
        traceback.print_exc()
        return render_template('enhanced_dashboard.html', 
                             view='overview', 
                             current_year=year,
                             current_month=month,
                             current_owner=owner,
                             available_years=available_years,
                             available_owners=available_owners,
                             current_total=0,
                             prev_year_total=0,
                             month_change=0,
                             ytd_total=0,
                             prev_ytd_total=0,
                             ytd_change=0,
                             monthly_spending=[],
                             top_categories=[],
                             budget_performance={'over_budget_count': 0, 'under_budget_count': 0, 'on_track_count': 0},
                             recent_transactions=[],
                             monthly_trend=[],
                             total_debt=0,
                             owner_comparison=[],
                             yearly_data={},
                             category_trends={},
                             monthly_data=[],
                             budget_analysis=[],
                             categories_data=[],
                             total_initial_budget=0,
                             total_effective_budget=0,
                             total_unexpected_expenses=0,
                             total_actual_spending=0,
                             error=str(e))

def dashboard_budget_view(year, month, owner, available_years, available_owners):
    """Dashboard Budget Management - Updated with subcategory budgets, commitments, and living budget"""

    try:
        conn = sqlite3.connect('data/personal_finance.db')

        # Ensure budget tables exist
        ensure_budget_tables(conn)

        # Get filter for actual spending
        spending_filter = "strftime('%m', date) = ? AND strftime('%Y', date) = ?"
        spending_params = [f"{month:02d}", str(year)]

        if owner != 'all':
            spending_filter += " AND owner = ?"
            spending_params.append(owner)

        # Get actual spending by subcategory for selected month
        actual_spending_query = f"""
        SELECT
            category,
            sub_category,
            SUM(amount) as actual_amount,
            COUNT(*) as transaction_count
        FROM transactions
        WHERE {spending_filter}
        AND sub_category IS NOT NULL
        AND sub_category != ''
        AND type IN ('Needs', 'Wants', 'Business', 'Savings')
        AND COALESCE(is_active, 1) = 1
        GROUP BY category, sub_category
        ORDER BY category, sub_category
        """
        actual_spending_df = pd.read_sql_query(actual_spending_query, conn, params=spending_params)

        # Get subcategory budgets - ONLY show budgets that have amounts set
        subcategory_budgets_query = """
        SELECT category, sub_category, budget_amount, notes, budget_by_category
        FROM budget_subcategory_templates
        WHERE is_active = 1 AND budget_amount > 0
        ORDER BY category, sub_category
        """
        subcategory_budgets_df = pd.read_sql_query(subcategory_budgets_query, conn)

        print(f"📋 Found {len(subcategory_budgets_df)} subcategory budgets with amounts > 0")

        # Group by category to check budget_by_category flag
        category_budget_mode = {}
        for _, row in subcategory_budgets_df.iterrows():
            if row['category'] not in category_budget_mode:
                category_budget_mode[row['category']] = bool(row['budget_by_category'])

        # Get commitments summary
        commitments_query = """
        SELECT COALESCE(SUM(estimated_amount), 0) as total_commitments,
               COALESCE(SUM(CASE WHEN is_fixed = 1 THEN estimated_amount ELSE 0 END), 0) as total_fixed,
               COALESCE(SUM(CASE WHEN is_fixed = 0 THEN estimated_amount ELSE 0 END), 0) as total_variable,
               COUNT(*) as count
        FROM budget_commitments
        WHERE is_active = 1
        """
        commitments_df = pd.read_sql_query(commitments_query, conn)

        # Get unexpected expenses for selected month/year (still by category for compatibility)
        unexpected_expenses_query = """
        SELECT category, SUM(amount) as total_unexpected
        FROM unexpected_expenses
        WHERE month = ? AND year = ? AND is_active = 1
        GROUP BY category
        ORDER BY category
        """
        unexpected_expenses_df = pd.read_sql_query(unexpected_expenses_query, conn, params=[month, year])

        conn.close()

        # Create budget analysis by subcategory
        budget_analysis = []

        # Create dictionaries for lookup
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

        # Get all unique subcategory combinations
        all_subcategories = set(subcategory_budget_dict.keys()) | set(actual_spending_dict.keys())

        print(f"📊 Unique subcategories to process: {len(all_subcategories)}")
        print(f"📊 Budget dict entries: {len(subcategory_budget_dict)}")
        print(f"📊 Spending dict entries: {len(actual_spending_dict)}")

        # Group by category for display
        category_groups = {}

        for subcat_key in sorted(all_subcategories):
            category, sub_category = subcat_key.split('|')

            budget_amount = subcategory_budget_dict.get(subcat_key, 0.0)
            actual_spending = actual_spending_dict.get(subcat_key, 0.0)

            # Calculate variance and status
            variance = actual_spending - budget_amount
            variance_pct = (variance / budget_amount * 100) if budget_amount > 0 else 0

            # Determine status
            if budget_amount == 0 and actual_spending > 0:
                # No budget but has spending = over budget
                status = 'over'
            elif budget_amount == 0 and actual_spending == 0:
                # No budget and no spending = no budget
                status = 'no_budget'
            elif variance > 20:  # Over by more than $20 (subcategories are more granular)
                status = 'over'
            elif variance < -20:  # Under by more than $20
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

        # Convert to list for template and format for display
        budget_analysis = []
        for cat_data in category_groups.values():
            category = cat_data['category']
            is_category_level = category_budget_mode.get(category, False)

            initial_budget = cat_data['total_budget']
            unexpected = cat_data['unexpected_expenses']
            effective_budget = initial_budget + unexpected
            actual_spending = cat_data['total_actual']
            variance = actual_spending - effective_budget

            # Determine status
            if effective_budget == 0 and actual_spending > 0:
                # No budget (even with unexpected expenses) but has spending = over budget
                status = 'over'
            elif effective_budget == 0 and actual_spending == 0:
                # No budget and no spending = no budget
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
                'budget_by_category': is_category_level  # Add flag to template
            })

        print(f"📊 Budget analysis count: {len(budget_analysis)}")
        if len(budget_analysis) > 0:
            print(f"📊 Total budget: {sum([item['initial_budget'] for item in budget_analysis])}")
            print(f"📊 First category: {budget_analysis[0]['category']}")
        else:
            print("⚠️ WARNING: budget_analysis is EMPTY!")
            print(f"⚠️ category_groups had {len(category_groups)} groups")

        # Calculate totals
        total_budget = sum([item['initial_budget'] for item in budget_analysis])
        total_unexpected_expenses = sum([item['unexpected_expenses'] for item in budget_analysis])
        total_effective_budget = total_budget + total_unexpected_expenses
        total_actual_spending = sum([item['actual_spending'] for item in budget_analysis])

        # Commitments data
        total_commitments = float(commitments_df['total_commitments'].iloc[0]) if not commitments_df.empty else 0.0
        total_fixed_commitments = float(commitments_df['total_fixed'].iloc[0]) if not commitments_df.empty else 0.0
        total_variable_commitments = float(commitments_df['total_variable'].iloc[0]) if not commitments_df.empty else 0.0
        commitment_count = int(commitments_df['count'].iloc[0]) if not commitments_df.empty else 0

        # Living budget = Total Budget - Commitments
        living_budget = total_budget - total_commitments

        return render_template('enhanced_dashboard.html',
                             view='budget',
                             current_year=year,
                             current_month=month,
                             current_owner=owner,
                             available_years=available_years,
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
                             # Add defaults for other views
                             current_total=0,
                             prev_year_total=0,
                             month_change=0,
                             ytd_total=0,
                             prev_ytd_total=0,
                             ytd_change=0,
                             monthly_spending=[],
                             top_categories=[],
                             yearly_data={},
                             category_trends={},
                             monthly_data=[],
                             categories_data=[])
                             
    except Exception as e:
        print(f"❌ Error in budget view: {e}")
        import traceback
        traceback.print_exc()
        return render_template('enhanced_dashboard.html',
                             view='budget',
                             current_year=year,
                             current_month=month,
                             current_owner=owner,
                             available_years=available_years,
                             available_owners=available_owners,
                             budget_analysis=[],
                             total_initial_budget=0,
                             total_unexpected_expenses=0,
                             total_effective_budget=0,
                             total_actual_spending=0,
                             total_commitments=0,
                             total_fixed_commitments=0,
                             total_variable_commitments=0,
                             commitment_count=0,
                             living_budget=0,
                             current_total=0,
                             prev_year_total=0,
                             month_change=0,
                             ytd_total=0,
                             prev_ytd_total=0,
                             ytd_change=0,
                             monthly_spending=[],
                             top_categories=[],
                             yearly_data={},
                             category_trends={},
                             monthly_data=[],
                             categories_data=[],
                             budget_performance={'over_budget_count': 0, 'under_budget_count': 0, 'on_track_count': 0},
                             recent_transactions=[],
                             monthly_trend=[],
                             total_debt=0,
                             owner_comparison=[],
                             error=str(e))

def dashboard_categories_view(available_years, available_owners):
    """Dashboard Categories Management - Complete categories management interface"""
    from flask import g
    import sqlite3
    try:
        # Get current time filters
        current_year = request.args.get('year', datetime.now().year, type=int)
        current_month = request.args.get('month', 'all')
        
        print(f"⚙️ Loading categories management view: year={current_year}, month={current_month}")
        
        # Connect to the database
        conn = sqlite3.connect('data/personal_finance.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get all active categories from budget_templates
        cursor.execute("""
            SELECT id, category, notes, budget_amount, is_active
            FROM budget_templates
            WHERE is_active = 1 AND category IS NOT NULL
            ORDER BY category
        """)
        categories = cursor.fetchall()

        categories_data = []
        for cat in categories:
            category_name = cat['category']
            # Get transaction count, total, and average for this category
            if current_month == 'all':
                cursor.execute("""
                    SELECT COUNT(*) as count, SUM(amount) as total, AVG(amount) as avg
                    FROM transactions
                    WHERE category = ? AND strftime('%Y', date) = ?
                """, (category_name, str(current_year)))
            else:
                cursor.execute("""
                    SELECT COUNT(*) as count, SUM(amount) as total, AVG(amount) as avg
                    FROM transactions
                    WHERE category = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
                """, (category_name, str(current_year), f"{int(current_month):02d}"))
            stats = cursor.fetchone()
            categories_data.append({
                'category': category_name,
                'type': cat['notes'] or '',  # Assuming 'notes' is used for type, adjust if needed
                'transactions': stats['count'] or 0,
                'total_amount': stats['total'] or 0.0,
                'average': stats['avg'] or 0.0,
                'budget': cat['budget_amount'] or 0.0
            })
        conn.close()

        print(f"[DEBUG] categories_data count: {len(categories_data)}")
        if categories_data:
            print(f"[DEBUG] First category: {categories_data[0]}")

        return render_template('enhanced_dashboard.html',
                             view='categories',
                             current_year=current_year,
                             current_month=current_month,
                             current_owner='all',
                             available_years=available_years,
                             available_owners=available_owners,
                             categories_data=categories_data,
                             # Add defaults for other views to prevent template errors
                             current_total=0,
                             prev_year_total=0,
                             month_change=0,
                             ytd_total=0,
                             prev_ytd_total=0,
                             ytd_change=0,
                             monthly_spending=[],
                             top_categories=[],
                             yearly_data={},
                             category_trends={},
                             monthly_data=[],
                             budget_analysis=[],
                             total_initial_budget=0,
                             total_effective_budget=0,
                             total_unexpected_expenses=0,
                             total_actual_spending=0)
    except Exception as e:
        print(f"❌ Error in categories view: {e}")
        import traceback
        traceback.print_exc()
        return render_template('enhanced_dashboard.html', 
                             view='categories',
                             current_year=datetime.now().year,
                             current_month='all',
                             current_owner='all',
                             available_years=available_years,
                             available_owners=available_owners,
                             categories_data=[],
                             current_total=0,
                             prev_year_total=0,
                             month_change=0,
                             ytd_total=0,
                             prev_ytd_total=0,
                             ytd_change=0,
                             monthly_spending=[],
                             top_categories=[],
                             yearly_data={},
                             category_trends={},
                             monthly_data=[],
                             budget_analysis=[],
                             total_initial_budget=0,
                             total_effective_budget=0,
                             total_unexpected_expenses=0,
                             total_actual_spending=0,
                             error=str(e))