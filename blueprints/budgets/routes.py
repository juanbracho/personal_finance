from flask import Blueprint, render_template, request, jsonify
from datetime import datetime
from utils import ensure_budget_tables
import pandas as pd
import sqlite3

# Create the blueprint
budgets_bp = Blueprint('budgets', __name__, url_prefix='/budget')

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