from flask import Blueprint, render_template, request, jsonify
from datetime import datetime
from utils import ensure_budget_tables
import pandas as pd
import sqlite3
from budget_recommender import (
    calculate_subcategory_recommendations,
    migrate_category_budgets_to_subcategories,
    get_commitment_summary
)

# Create the blueprint
budgets_bp = Blueprint('budgets', __name__, url_prefix='/budget')

def sync_budgets_from_commitments(conn):
    """
    Automatically update subcategory budgets to match total commitments.
    Ensures budget >= total commitments for each subcategory.
    """
    try:
        cursor = conn.cursor()

        # Get total commitments by category/subcategory
        commitments_query = """
        SELECT
            category,
            sub_category,
            SUM(estimated_amount) as total_commitment
        FROM budget_commitments
        WHERE is_active = 1
        GROUP BY category, sub_category
        """

        commitments_df = pd.read_sql_query(commitments_query, conn)

        print(f"🔄 Syncing budgets from {len(commitments_df)} commitment groups")

        for _, row in commitments_df.iterrows():
            category = row['category']
            sub_category = row['sub_category']
            total_commitment = float(row['total_commitment'])

            # Check if budget template exists
            cursor.execute("""
                SELECT budget_amount FROM budget_subcategory_templates
                WHERE category = ? AND sub_category = ? AND is_active = 1
            """, (category, sub_category))

            result = cursor.fetchone()

            if result:
                current_budget = float(result[0]) if result[0] else 0.0

                # Only update if commitment is higher than current budget
                if total_commitment > current_budget:
                    cursor.execute("""
                        UPDATE budget_subcategory_templates
                        SET budget_amount = ?,
                            updated_at = ?
                        WHERE category = ? AND sub_category = ? AND is_active = 1
                    """, (total_commitment, datetime.utcnow().isoformat(), category, sub_category))

                    print(f"  ✅ Updated {category} > {sub_category}: ${current_budget:.2f} → ${total_commitment:.2f}")
            else:
                # Create new budget template if it doesn't exist
                cursor.execute("""
                    INSERT INTO budget_subcategory_templates
                    (category, sub_category, budget_amount, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, 1, ?, ?)
                """, (category, sub_category, total_commitment,
                      datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))

                print(f"  ➕ Created {category} > {sub_category}: ${total_commitment:.2f}")

        conn.commit()
        print(f"✅ Budget sync completed")

    except Exception as e:
        print(f"❌ Error syncing budgets from commitments: {e}")
        import traceback
        traceback.print_exc()

@budgets_bp.route('/')
def budget_management():
    """Budget management page - simplified to only show initial budgets and unexpected expenses"""
    
    selected_year = request.args.get('year', datetime.now().year, type=int)
    selected_month = request.args.get('month', datetime.now().month, type=int)
    
    # Get available years
    try:
        conn = sqlite3.connect('data/personal_finance.db')
        years_df = pd.read_sql_query("""
            SELECT DISTINCT strftime('%Y', date) as year 
            FROM transactions 
            ORDER BY year DESC
        """, conn)
        available_years = [int(year) for year in years_df['year'].tolist()]
        conn.close()
    except Exception as e:
        print(f"❌ Error getting available years: {e}")
        available_years = [2022, 2023, 2024, 2025]
    
    if not available_years:
        available_years = [2022, 2023, 2024, 2025]
    
    print(f"💰 Budget management page loaded: year={selected_year}, month={selected_month}")
    
    return render_template('budget_management.html',
                         selected_year=selected_year,
                         selected_month=selected_month,
                         available_years=available_years)

@budgets_bp.route('/api/templates')
def api_budget_templates():
    """Get all budget templates (initial budgets)"""
    
    try:
        print("📋 API: Loading budget templates...")
        
        conn = sqlite3.connect('data/personal_finance.db')
        ensure_budget_tables(conn)
        
        # Get existing templates
        templates_df = pd.read_sql_query("""
            SELECT category, budget_amount, notes, is_active
            FROM budget_templates 
            WHERE is_active = 1
            ORDER BY category
        """, conn)
        
        print(f"📋 Found {len(templates_df)} existing templates")
        
        # If no templates exist, create them from transaction categories
        if templates_df.empty:
            print("📋 No budget templates found, creating from transaction categories...")
            
            categories_df = pd.read_sql_query("""
                SELECT DISTINCT category
                FROM transactions 
                WHERE category IS NOT NULL AND category != ''
                ORDER BY category
            """, conn)
            
            cursor = conn.cursor()
            for _, row in categories_df.iterrows():
                cursor.execute("""
                    INSERT OR IGNORE INTO budget_templates (category, budget_amount, notes, is_active, created_at, updated_at)
                    VALUES (?, 0.00, '', 1, ?, ?)
                """, (row['category'], datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
            
            conn.commit()
            
            # Re-fetch templates
            templates_df = pd.read_sql_query("""
                SELECT category, budget_amount, notes, is_active
                FROM budget_templates 
                WHERE is_active = 1
                ORDER BY category
            """, conn)
        
        conn.close()
        
        result = [{
            'category': str(row['category']),
            'budget_amount': float(row['budget_amount']),
            'notes': str(row['notes']) if row['notes'] else '',
            'is_active': bool(row['is_active'])
        } for _, row in templates_df.iterrows()]
        
        print(f"📋 Returning {len(result)} budget templates")
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Error getting budget templates: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@budgets_bp.route('/api/unexpected_expenses')
def api_unexpected_expenses():
    """Get unexpected expenses for specific month/year"""
    
    try:
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)
        
        print(f"💸 API: Loading unexpected expenses for {year}-{month:02d}")
        
        if not month or not year:
            return jsonify({'error': 'Month and year required'}), 400
        
        conn = sqlite3.connect('data/personal_finance.db')
        ensure_budget_tables(conn)
        
        # Get unexpected expenses for the month
        unexpected_df = pd.read_sql_query("""
            SELECT id, category, amount, description, is_active, created_at
            FROM unexpected_expenses 
            WHERE month = ? AND year = ? AND is_active = 1
            ORDER BY category, description
        """, conn, params=[month, year])
        
        conn.close()
        
        result = [{
            'id': int(row['id']),
            'category': str(row['category']),
            'amount': float(row['amount']),
            'description': str(row['description']),
            'is_active': bool(row['is_active']),
            'created_at': str(row['created_at'])
        } for _, row in unexpected_df.iterrows()]
        
        print(f"💸 Returning {len(result)} unexpected expenses")
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Error getting unexpected expenses: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@budgets_bp.route('/api/unexpected_expenses', methods=['POST'])
def add_unexpected_expense():
    """Add a new unexpected expense"""
    
    try:
        data = request.get_json()
        category = data['category']
        month = data['month']
        year = data['year']
        amount = float(data['amount'])
        description = data['description']
        
        print(f"💸 API: Adding unexpected expense: {description} - ${amount} for {category}")
        
        conn = sqlite3.connect('data/personal_finance.db')
        ensure_budget_tables(conn)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO unexpected_expenses 
            (category, month, year, amount, description, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?)
        """, (category, month, year, amount, description, 
              datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
        
        expense_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"💸 Successfully added unexpected expense with ID {expense_id}")
        return jsonify({'success': True, 'id': expense_id, 'message': 'Unexpected expense added successfully'})
        
    except Exception as e:
        print(f"❌ Error adding unexpected expense: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@budgets_bp.route('/api/unexpected_expenses/<int:expense_id>', methods=['PUT'])
def update_unexpected_expense(expense_id):
    """Update an existing unexpected expense"""
    
    try:
        data = request.get_json()
        amount = float(data['amount'])
        description = data['description']
        
        print(f"💸 API: Updating unexpected expense ID {expense_id}: {description} - ${amount}")
        
        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE unexpected_expenses 
            SET amount = ?, description = ?, updated_at = ?
            WHERE id = ? AND is_active = 1
        """, (amount, description, datetime.utcnow().isoformat(), expense_id))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'success': False, 'error': 'Unexpected expense not found'}), 404
        
        conn.commit()
        conn.close()
        
        print(f"💸 Successfully updated unexpected expense ID {expense_id}")
        return jsonify({'success': True, 'message': 'Unexpected expense updated successfully'})
        
    except Exception as e:
        print(f"❌ Error updating unexpected expense: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@budgets_bp.route('/api/unexpected_expenses/<int:expense_id>', methods=['DELETE'])
def delete_unexpected_expense(expense_id):
    """Delete (deactivate) an unexpected expense"""
    
    try:
        print(f"💸 API: Deleting unexpected expense ID {expense_id}")
        
        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE unexpected_expenses 
            SET is_active = 0, updated_at = ?
            WHERE id = ? AND is_active = 1
        """, (datetime.utcnow().isoformat(), expense_id))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'success': False, 'error': 'Unexpected expense not found'}), 404
        
        conn.commit()
        conn.close()
        
        print(f"💸 Successfully deleted unexpected expense ID {expense_id}")
        return jsonify({'success': True, 'message': 'Unexpected expense deleted successfully'})
        
    except Exception as e:
        print(f"❌ Error deleting unexpected expense: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@budgets_bp.route('/api/actual_spending')
def api_actual_spending():
    """Get actual spending for specific month/year"""
    
    try:
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)
        owner = request.args.get('owner', 'all')
        
        print(f"💰 API: Loading actual spending for {year}-{month:02d}, owner={owner}")
        
        if not month or not year:
            return jsonify({'error': 'Month and year required'}), 400
        
        conn = sqlite3.connect('data/personal_finance.db')
        
        # Build filter conditions
        date_filter = "strftime('%m', date) = ? AND strftime('%Y', date) = ?"
        params = [f"{month:02d}", str(year)]
        
        if owner != 'all':
            date_filter += " AND owner = ?"
            params.append(owner)
        
        # Get actual spending by category
        actual_spending_query = f"""
        SELECT 
            category,
            SUM(amount) as actual_amount,
            COUNT(*) as transaction_count
        FROM transactions 
        WHERE {date_filter} AND COALESCE(is_active, 1) = 1
        GROUP BY category
        ORDER BY actual_amount DESC
        """
        
        actual_df = pd.read_sql_query(actual_spending_query, conn, params=params)
        conn.close()
        
        result = [{
            'category': str(row['category']),
            'actual_amount': float(row['actual_amount']),
            'transaction_count': int(row['transaction_count'])
        } for _, row in actual_df.iterrows()]
        
        print(f"💰 Returning actual spending for {len(result)} categories")
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Error getting actual spending: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@budgets_bp.route('/api/update_template', methods=['POST'])
def update_budget_template():
    """Update initial budget template"""
    
    try:
        data = request.get_json()
        category = data['category']
        budget_amount = float(data['budget_amount'])
        notes = data.get('notes', '')
        
        print(f"💾 API: Updating template budget for {category}: ${budget_amount}")
        
        conn = sqlite3.connect('data/personal_finance.db')
        ensure_budget_tables(conn)
        cursor = conn.cursor()
        
        # Update or insert template budget
        cursor.execute("""
            INSERT OR REPLACE INTO budget_templates 
            (category, budget_amount, notes, is_active, created_at, updated_at)
            VALUES (?, ?, ?, 1, 
                COALESCE((SELECT created_at FROM budget_templates WHERE category = ?), ?), 
                ?)
        """, (category, budget_amount, notes, category, datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
        
        conn.commit()
        conn.close()
        
        print(f"💾 Successfully updated template budget for {category}")
        return jsonify({'success': True, 'message': 'Budget template updated successfully'})

    except Exception as e:
        print(f"❌ Error updating budget template: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# SUBCATEGORY BUDGET ENDPOINTS
# ============================================================================

@budgets_bp.route('/api/subcategory_templates')
def api_subcategory_templates():
    """Get all subcategory budget templates with commitment minimums enforced"""

    try:
        print("📋 API: Loading subcategory budget templates...")

        conn = sqlite3.connect('data/personal_finance.db')
        ensure_budget_tables(conn)

        # Get all subcategory templates (including hidden ones)
        templates_df = pd.read_sql_query("""
            SELECT category, sub_category, budget_amount, notes, budget_by_category, is_active
            FROM budget_subcategory_templates
            ORDER BY category, sub_category
        """, conn)

        print(f"📋 Found {len(templates_df)} subcategory templates")

        # If no templates exist, create them from transaction subcategories
        if templates_df.empty:
            print("📋 No subcategory templates found, creating from transactions...")

            subcategories_df = pd.read_sql_query("""
                SELECT DISTINCT category, sub_category
                FROM transactions
                WHERE sub_category IS NOT NULL AND sub_category != ''
                ORDER BY category, sub_category
            """, conn)

            cursor = conn.cursor()
            for _, row in subcategories_df.iterrows():
                cursor.execute("""
                    INSERT OR IGNORE INTO budget_subcategory_templates
                    (category, sub_category, budget_amount, notes, is_active, created_at, updated_at)
                    VALUES (?, ?, 0.00, '', 1, ?, ?)
                """, (row['category'], row['sub_category'],
                      datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))

            conn.commit()

            # Re-fetch templates
            templates_df = pd.read_sql_query("""
                SELECT category, sub_category, budget_amount, notes, is_active
                FROM budget_subcategory_templates
                WHERE is_active = 1
                ORDER BY category, sub_category
            """, conn)

        # Get commitment totals for each subcategory
        commitments_df = pd.read_sql_query("""
            SELECT
                category,
                sub_category,
                COALESCE(SUM(estimated_amount), 0) as total_commitment
            FROM budget_commitments
            WHERE is_active = 1
            GROUP BY category, sub_category
        """, conn)

        conn.close()

        # Create result list with enforced minimums
        result = []
        for _, row in templates_df.iterrows():
            category = str(row['category'])
            sub_category = str(row['sub_category'])
            budget_amount = float(row['budget_amount'])

            # Check if there's a commitment for this subcategory
            commitment_row = commitments_df[
                (commitments_df['category'] == category) &
                (commitments_df['sub_category'] == sub_category)
            ]

            commitment_minimum = 0.0
            if not commitment_row.empty:
                commitment_minimum = float(commitment_row.iloc[0]['total_commitment'])

            # Enforce minimum: budget should be at least the commitment total
            effective_budget = max(budget_amount, commitment_minimum)

            result.append({
                'category': category,
                'sub_category': sub_category,
                'budget_amount': effective_budget,
                'commitment_minimum': commitment_minimum,  # Add this info for frontend
                'notes': str(row['notes']) if row['notes'] else '',
                'budget_by_category': bool(row['budget_by_category']),
                'is_active': bool(row['is_active'])
            })

        print(f"📋 Returning {len(result)} subcategory budget templates (with commitment minimums enforced)")
        return jsonify(result)

    except Exception as e:
        print(f"❌ Error getting subcategory templates: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@budgets_bp.route('/api/subcategory_templates/sync', methods=['POST'])
def sync_subcategory_templates():
    """Sync budget templates with current transaction subcategories - add new ones and remove unused ones"""

    try:
        print("🔄 API: Syncing subcategory templates with transactions...")

        conn = sqlite3.connect('data/personal_finance.db')
        ensure_budget_tables(conn)
        cursor = conn.cursor()

        # Get all distinct category/subcategory pairs from transactions
        subcategories_df = pd.read_sql_query("""
            SELECT DISTINCT category, sub_category
            FROM transactions
            WHERE sub_category IS NOT NULL AND sub_category != ''
            ORDER BY category, sub_category
        """, conn)

        # Get existing budget templates
        existing_df = pd.read_sql_query("""
            SELECT category, sub_category
            FROM budget_subcategory_templates
        """, conn)

        # Create sets for comparison
        transaction_pairs = set(
            (row['category'], row['sub_category'])
            for _, row in subcategories_df.iterrows()
        )

        existing_pairs = set(
            (row['category'], row['sub_category'])
            for _, row in existing_df.iterrows()
        )

        # Find pairs to add (in transactions but not in budget templates)
        to_add = transaction_pairs - existing_pairs

        # Find pairs to remove (in budget templates but not in transactions)
        to_remove = existing_pairs - transaction_pairs

        # Add new subcategories
        added_count = 0
        for category, sub_category in to_add:
            cursor.execute("""
                INSERT INTO budget_subcategory_templates
                (category, sub_category, budget_amount, notes, budget_by_category, is_active, created_at, updated_at)
                VALUES (?, ?, 0.00, '', 0, 1, ?, ?)
            """, (category, sub_category,
                  datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
            added_count += 1

        # Remove obsolete subcategories
        removed_count = 0
        for category, sub_category in to_remove:
            cursor.execute("""
                DELETE FROM budget_subcategory_templates
                WHERE category = ? AND sub_category = ?
            """, (category, sub_category))
            removed_count += 1

        conn.commit()
        conn.close()

        message = f'Sync complete: {added_count} added, {removed_count} removed'
        print(f"🔄 {message}")
        return jsonify({
            'success': True,
            'message': message,
            'added_count': added_count,
            'removed_count': removed_count
        })

    except Exception as e:
        print(f"❌ Error syncing subcategory templates: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@budgets_bp.route('/api/subcategory_templates/update', methods=['POST'])
def update_subcategory_template():
    """Update or create subcategory budget template"""

    try:
        data = request.get_json()
        category = data['category']
        sub_category = data['sub_category']
        budget_amount = float(data.get('budget_amount', 0))
        notes = data.get('notes', '')
        budget_by_category = data.get('budget_by_category', False)
        is_active = data.get('is_active', True)

        print(f"💾 API: Updating subcategory budget for {category} > {sub_category}: ${budget_amount}, by_category={budget_by_category}, active={is_active}")

        conn = sqlite3.connect('data/personal_finance.db')
        ensure_budget_tables(conn)
        cursor = conn.cursor()

        # Check total commitments for this subcategory
        cursor.execute("""
            SELECT COALESCE(SUM(estimated_amount), 0) as total_commitment
            FROM budget_commitments
            WHERE category = ? AND sub_category = ? AND is_active = 1
        """, (category, sub_category))

        result = cursor.fetchone()
        total_commitment = float(result[0]) if result else 0.0

        # Validate budget is not less than commitments
        if budget_amount < total_commitment:
            conn.close()
            error_msg = f"Budget cannot be less than total commitments (${total_commitment:.2f}) for {category} > {sub_category}"
            print(f"❌ {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg,
                'minimum_budget': total_commitment
            }), 400

        # Update or insert subcategory budget
        cursor.execute("""
            INSERT INTO budget_subcategory_templates
            (category, sub_category, budget_amount, notes, budget_by_category, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(category, sub_category)
            DO UPDATE SET
                budget_amount = ?,
                notes = ?,
                budget_by_category = ?,
                is_active = ?,
                updated_at = ?
        """, (category, sub_category, budget_amount, notes, budget_by_category, is_active,
              datetime.utcnow().isoformat(), datetime.utcnow().isoformat(),
              budget_amount, notes, budget_by_category, is_active, datetime.utcnow().isoformat()))

        conn.commit()
        conn.close()

        print(f"💾 Successfully updated subcategory budget for {category} > {sub_category}")
        return jsonify({'success': True, 'message': 'Subcategory budget updated successfully'})

    except Exception as e:
        print(f"❌ Error updating subcategory budget: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@budgets_bp.route('/api/subcategory_templates/batch_update', methods=['POST'])
def batch_update_subcategory_templates():
    """Batch update multiple subcategory budgets at once"""

    try:
        data = request.get_json()
        budgets = data.get('budgets', [])

        print(f"💾 API: Batch updating {len(budgets)} subcategory budgets")

        conn = sqlite3.connect('data/personal_finance.db')
        ensure_budget_tables(conn)
        cursor = conn.cursor()

        for budget in budgets:
            category = budget['category']
            sub_category = budget['sub_category']
            budget_amount = float(budget['budget_amount'])
            notes = budget.get('notes', '')

            cursor.execute("""
                INSERT INTO budget_subcategory_templates
                (category, sub_category, budget_amount, notes, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(category, sub_category)
                DO UPDATE SET
                    budget_amount = ?,
                    notes = ?,
                    updated_at = ?
            """, (category, sub_category, budget_amount, notes,
                  datetime.utcnow().isoformat(), datetime.utcnow().isoformat(),
                  budget_amount, notes, datetime.utcnow().isoformat()))

        conn.commit()
        conn.close()

        print(f"💾 Successfully batch updated {len(budgets)} subcategory budgets")
        return jsonify({'success': True, 'message': f'{len(budgets)} budgets updated successfully'})

    except Exception as e:
        print(f"❌ Error batch updating subcategory budgets: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@budgets_bp.route('/api/subcategory_templates/toggle_granularity', methods=['POST'])
def toggle_category_granularity():
    """Toggle budget granularity for an entire category (category-level vs subcategory-level)"""

    try:
        data = request.get_json()
        category = data['category']
        budget_by_category = data['budget_by_category']

        print(f"🔄 API: Toggling budget granularity for {category}: budget_by_category={budget_by_category}")

        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()

        # Update all subcategories for this category
        cursor.execute("""
            UPDATE budget_subcategory_templates
            SET budget_by_category = ?, updated_at = ?
            WHERE category = ? AND is_active = 1
        """, (budget_by_category, datetime.utcnow().isoformat(), category))

        rows_updated = cursor.rowcount
        conn.commit()
        conn.close()

        print(f"🔄 Updated {rows_updated} subcategories for category {category}")
        return jsonify({
            'success': True,
            'message': f'Updated {rows_updated} subcategories',
            'rows_updated': rows_updated
        })

    except Exception as e:
        print(f"❌ Error toggling category granularity: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# BUDGET RECOMMENDATION ENDPOINTS
# ============================================================================

@budgets_bp.route('/api/recommend_budgets')
def api_recommend_budgets():
    """Calculate budget recommendations based on 6-month spending history"""

    try:
        owner = request.args.get('owner', None)
        if owner == 'all':
            owner = None

        print(f"🤖 API: Calculating budget recommendations for owner={owner}")

        recommendations = calculate_subcategory_recommendations(owner=owner)

        print(f"🤖 Generated {len(recommendations)} budget recommendations")
        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'count': len(recommendations)
        })

    except Exception as e:
        print(f"❌ Error calculating budget recommendations: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@budgets_bp.route('/api/migrate_budgets', methods=['POST'])
def api_migrate_budgets():
    """Migrate existing category budgets to subcategory budgets"""

    try:
        print("🔄 API: Starting budget migration from categories to subcategories...")

        stats = migrate_category_budgets_to_subcategories()

        print(f"🔄 Migration complete: {stats}")
        return jsonify({
            'success': True,
            'message': 'Budget migration completed successfully',
            'stats': stats
        })

    except Exception as e:
        print(f"❌ Error migrating budgets: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# COMMITMENT TRACKING ENDPOINTS
# ============================================================================

@budgets_bp.route('/api/commitments')
def api_get_commitments():
    """Get all active budget commitments"""

    try:
        print("📌 API: Loading budget commitments...")

        conn = sqlite3.connect('data/personal_finance.db')
        ensure_budget_tables(conn)

        commitments_df = pd.read_sql_query("""
            SELECT id, name, category, sub_category, estimated_amount,
                   due_day_of_month, is_fixed, created_at
            FROM budget_commitments
            WHERE is_active = 1
            ORDER BY due_day_of_month, name
        """, conn)

        conn.close()

        result = [{
            'id': int(row['id']),
            'name': str(row['name']),
            'category': str(row['category']),
            'sub_category': str(row['sub_category']),
            'estimated_amount': float(row['estimated_amount']),
            'due_day_of_month': int(row['due_day_of_month']),
            'is_fixed': bool(row['is_fixed']),
            'created_at': str(row['created_at'])
        } for _, row in commitments_df.iterrows()]

        print(f"📌 Returning {len(result)} commitments")
        return jsonify(result)

    except Exception as e:
        print(f"❌ Error getting commitments: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@budgets_bp.route('/api/commitments', methods=['POST'])
def api_add_commitment():
    """Add a new budget commitment"""

    try:
        data = request.get_json()
        name = data['name']
        category = data['category']
        sub_category = data['sub_category']
        estimated_amount = float(data['estimated_amount'])
        due_day_of_month = int(data['due_day_of_month'])
        is_fixed = data.get('is_fixed', True)

        print(f"📌 API: Adding commitment: {name} - ${estimated_amount} due on day {due_day_of_month}")

        if due_day_of_month < 1 or due_day_of_month > 31:
            return jsonify({'success': False, 'error': 'Due day must be between 1 and 31'}), 400

        conn = sqlite3.connect('data/personal_finance.db')
        ensure_budget_tables(conn)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO budget_commitments
            (name, category, sub_category, estimated_amount, due_day_of_month,
             is_fixed, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
        """, (name, category, sub_category, estimated_amount, due_day_of_month,
              is_fixed, datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))

        commitment_id = cursor.lastrowid
        conn.commit()

        # Auto-sync budgets to match commitments
        sync_budgets_from_commitments(conn)

        conn.close()

        print(f"📌 Successfully added commitment with ID {commitment_id}")
        return jsonify({'success': True, 'id': commitment_id, 'message': 'Commitment added successfully'})

    except Exception as e:
        print(f"❌ Error adding commitment: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@budgets_bp.route('/api/commitments/<int:commitment_id>', methods=['PUT'])
def api_update_commitment(commitment_id):
    """Update an existing budget commitment"""

    try:
        data = request.get_json()
        name = data['name']
        category = data['category']
        sub_category = data['sub_category']
        estimated_amount = float(data['estimated_amount'])
        due_day_of_month = int(data['due_day_of_month'])
        is_fixed = data.get('is_fixed', True)

        print(f"📌 API: Updating commitment ID {commitment_id}: {name} - ${estimated_amount}")

        if due_day_of_month < 1 or due_day_of_month > 31:
            return jsonify({'success': False, 'error': 'Due day must be between 1 and 31'}), 400

        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE budget_commitments
            SET name = ?, category = ?, sub_category = ?, estimated_amount = ?,
                due_day_of_month = ?, is_fixed = ?, updated_at = ?
            WHERE id = ? AND is_active = 1
        """, (name, category, sub_category, estimated_amount, due_day_of_month,
              is_fixed, datetime.utcnow().isoformat(), commitment_id))

        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'success': False, 'error': 'Commitment not found'}), 404

        conn.commit()

        # Auto-sync budgets to match commitments
        sync_budgets_from_commitments(conn)

        conn.close()

        print(f"📌 Successfully updated commitment ID {commitment_id}")
        return jsonify({'success': True, 'message': 'Commitment updated successfully'})

    except Exception as e:
        print(f"❌ Error updating commitment: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@budgets_bp.route('/api/commitments/<int:commitment_id>', methods=['DELETE'])
def api_delete_commitment(commitment_id):
    """Delete (deactivate) a budget commitment"""

    try:
        print(f"📌 API: Deleting commitment ID {commitment_id}")

        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE budget_commitments
            SET is_active = 0, updated_at = ?
            WHERE id = ? AND is_active = 1
        """, (datetime.utcnow().isoformat(), commitment_id))

        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'success': False, 'error': 'Commitment not found'}), 404

        conn.commit()

        # Auto-sync budgets to match remaining commitments
        sync_budgets_from_commitments(conn)

        conn.close()

        print(f"📌 Successfully deleted commitment ID {commitment_id}")
        return jsonify({'success': True, 'message': 'Commitment deleted successfully'})

    except Exception as e:
        print(f"❌ Error deleting commitment: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@budgets_bp.route('/api/commitments/summary')
def api_commitment_summary():
    """Get summary of all commitments (total fixed, variable, etc.)"""

    try:
        print("📌 API: Getting commitment summary...")

        summary = get_commitment_summary()

        print(f"📌 Commitment summary: {summary['count']} commitments, Total: ${summary['total_commitments']}")
        return jsonify(summary)

    except Exception as e:
        print(f"❌ Error getting commitment summary: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================================
# ACTUAL SPENDING BY SUBCATEGORY
# ============================================================================

@budgets_bp.route('/api/actual_spending_subcategory')
def api_actual_spending_subcategory():
    """Get actual spending by subcategory for specific month/year"""

    try:
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)
        owner = request.args.get('owner', 'all')

        print(f"💰 API: Loading actual spending by subcategory for {year}-{month:02d}, owner={owner}")

        if not month or not year:
            return jsonify({'error': 'Month and year required'}), 400

        conn = sqlite3.connect('data/personal_finance.db')

        # Build filter conditions
        date_filter = "strftime('%m', date) = ? AND strftime('%Y', date) = ?"
        params = [f"{month:02d}", str(year)]

        if owner != 'all':
            date_filter += " AND owner = ?"
            params.append(owner)

        # Get actual spending by subcategory
        actual_spending_query = f"""
        SELECT
            category,
            sub_category,
            SUM(ABS(amount)) as actual_amount,
            COUNT(*) as transaction_count
        FROM transactions
        WHERE {date_filter}
        AND sub_category IS NOT NULL
        AND sub_category != ''
        AND type IN ('Needs', 'Wants', 'Business')
        AND COALESCE(is_active, 1) = 1
        GROUP BY category, sub_category
        ORDER BY category, sub_category
        """

        actual_df = pd.read_sql_query(actual_spending_query, conn, params=params)
        conn.close()

        result = [{
            'category': str(row['category']),
            'sub_category': str(row['sub_category']),
            'actual_amount': float(row['actual_amount']),
            'transaction_count': int(row['transaction_count'])
        } for _, row in actual_df.iterrows()]

        print(f"💰 Returning actual spending for {len(result)} subcategories")
        return jsonify(result)

    except Exception as e:
        print(f"❌ Error getting actual spending by subcategory: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500