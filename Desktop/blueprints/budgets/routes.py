from flask import Blueprint, render_template, request, jsonify
from datetime import datetime
from models import db
from sqlalchemy import text
from utils import ensure_budget_tables
import pandas as pd
from budget_recommender import (
    calculate_subcategory_recommendations,
    migrate_category_budgets_to_subcategories,
    get_commitment_summary
)

budgets_bp = Blueprint('budgets', __name__, url_prefix='/budget')


def _df(conn, sql, params=None):
    return pd.read_sql_query(text(sql), conn, params=params or {})


def sync_budgets_from_commitments(conn):
    """Automatically update subcategory budgets to match total commitments."""
    try:
        commitments = conn.execute(text("""
            SELECT category, sub_category, SUM(estimated_amount) as total_commitment
            FROM budget_commitments WHERE is_active = true
            GROUP BY category, sub_category
        """)).fetchall()

        now = datetime.utcnow()
        for category, sub_category, total_commitment in commitments:
            total_commitment = float(total_commitment)

            result = conn.execute(text("""
                SELECT budget_amount FROM budget_subcategory_templates
                WHERE category = :cat AND sub_category = :sub AND is_active = true
            """), {"cat": category, "sub": sub_category}).fetchone()

            if result:
                current_budget = float(result[0]) if result[0] else 0.0
                if total_commitment > current_budget:
                    conn.execute(text("""
                        UPDATE budget_subcategory_templates
                        SET budget_amount = :amount, updated_at = :now
                        WHERE category = :cat AND sub_category = :sub AND is_active = true
                    """), {"amount": total_commitment, "now": now, "cat": category, "sub": sub_category})
            else:
                conn.execute(text("""
                    INSERT INTO budget_subcategory_templates
                    (category, sub_category, budget_amount, is_active, created_at, updated_at)
                    VALUES (:cat, :sub, :amount, true, :now, :now)
                    ON CONFLICT DO NOTHING
                """), {"cat": category, "sub": sub_category, "amount": total_commitment, "now": now})

    except Exception as e:
        print(f"Error syncing budgets from commitments: {e}")
        import traceback
        traceback.print_exc()


@budgets_bp.route('/')
def budget_management():
    """Budget management page"""
    selected_year = request.args.get('year', datetime.now().year, type=int)
    selected_month = request.args.get('month', datetime.now().month, type=int)

    try:
        with db.engine.connect() as conn:
            years_df = _df(conn, """
                SELECT DISTINCT EXTRACT(YEAR FROM date)::integer AS year
                FROM transactions ORDER BY year DESC
            """)
            available_years = [int(y) for y in years_df['year'].tolist()]
    except Exception:
        available_years = [2022, 2023, 2024, 2025]

    if not available_years:
        available_years = [2022, 2023, 2024, 2025]

    return render_template('budget_management.html',
                         selected_year=selected_year,
                         selected_month=selected_month,
                         available_years=available_years)


@budgets_bp.route('/api/templates')
def api_budget_templates():
    """Get all budget templates (initial budgets)"""
    try:
        with db.engine.connect() as conn:
            df = _df(conn, """
                SELECT category, budget_amount, notes, is_active
                FROM budget_templates WHERE is_active = true ORDER BY category
            """)

            if df.empty:
                # Create from transaction categories
                cats_df = _df(conn, """
                    SELECT DISTINCT category FROM transactions
                    WHERE category IS NOT NULL AND category != '' ORDER BY category
                """)
                now = datetime.utcnow()
                with db.engine.begin() as write_conn:
                    for _, row in cats_df.iterrows():
                        write_conn.execute(text("""
                            INSERT INTO budget_templates (category, budget_amount, notes, is_active, created_at, updated_at)
                            VALUES (:cat, 0.00, '', true, :now, :now)
                            ON CONFLICT DO NOTHING
                        """), {"cat": row['category'], "now": now})

                with db.engine.connect() as conn2:
                    df = _df(conn2, """
                        SELECT category, budget_amount, notes, is_active
                        FROM budget_templates WHERE is_active = true ORDER BY category
                    """)

        result = [{
            'category': str(row['category']),
            'budget_amount': float(row['budget_amount']),
            'notes': str(row['notes']) if row['notes'] else '',
            'is_active': bool(row['is_active'])
        } for _, row in df.iterrows()]

        return jsonify(result)

    except Exception as e:
        print(f"Error getting budget templates: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@budgets_bp.route('/api/unexpected_expenses')
def api_unexpected_expenses():
    """Get unexpected expenses for specific month/year"""
    try:
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)

        if not month or not year:
            return jsonify({'error': 'Month and year required'}), 400

        with db.engine.connect() as conn:
            df = _df(conn, """
                SELECT id, category, amount, description, is_active, created_at
                FROM unexpected_expenses
                WHERE month = :month AND year = :year AND is_active = true
                ORDER BY category, description
            """, {"month": month, "year": year})

        result = [{
            'id': int(row['id']),
            'category': str(row['category']),
            'amount': float(row['amount']),
            'description': str(row['description']),
            'is_active': bool(row['is_active']),
            'created_at': str(row['created_at'])
        } for _, row in df.iterrows()]

        return jsonify(result)

    except Exception as e:
        print(f"Error getting unexpected expenses: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@budgets_bp.route('/api/unexpected_expenses', methods=['POST'])
def add_unexpected_expense():
    """Add a new unexpected expense"""
    try:
        data = request.get_json()
        now = datetime.utcnow()

        with db.engine.begin() as conn:
            result = conn.execute(text("""
                INSERT INTO unexpected_expenses
                (category, month, year, amount, description, is_active, created_at, updated_at)
                VALUES (:cat, :month, :year, :amount, :desc, true, :now, :now)
                RETURNING id
            """), {
                "cat": data['category'], "month": data['month'], "year": data['year'],
                "amount": float(data['amount']), "desc": data['description'], "now": now
            })
            expense_id = result.fetchone()[0]

        return jsonify({'success': True, 'id': expense_id, 'message': 'Unexpected expense added successfully'})

    except Exception as e:
        print(f"Error adding unexpected expense: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@budgets_bp.route('/api/unexpected_expenses/<int:expense_id>', methods=['PUT'])
def update_unexpected_expense(expense_id):
    """Update an existing unexpected expense"""
    try:
        data = request.get_json()

        with db.engine.begin() as conn:
            result = conn.execute(text("""
                UPDATE unexpected_expenses
                SET amount = :amount, description = :desc, category = :cat, updated_at = :now
                WHERE id = :id AND is_active = true
            """), {
                "amount": float(data['amount']), "desc": data['description'],
                "cat": data['category'], "now": datetime.utcnow(), "id": expense_id
            })
            if result.rowcount == 0:
                return jsonify({'success': False, 'error': 'Unexpected expense not found'}), 404

        return jsonify({'success': True, 'message': 'Unexpected expense updated successfully'})

    except Exception as e:
        print(f"Error updating unexpected expense: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@budgets_bp.route('/api/unexpected_expenses/<int:expense_id>', methods=['DELETE'])
def delete_unexpected_expense(expense_id):
    """Delete (deactivate) an unexpected expense"""
    try:
        with db.engine.begin() as conn:
            result = conn.execute(text("""
                UPDATE unexpected_expenses SET is_active = false, updated_at = :now
                WHERE id = :id AND is_active = true
            """), {"now": datetime.utcnow(), "id": expense_id})
            if result.rowcount == 0:
                return jsonify({'success': False, 'error': 'Unexpected expense not found'}), 404

        return jsonify({'success': True, 'message': 'Unexpected expense deleted successfully'})

    except Exception as e:
        print(f"Error deleting unexpected expense: {e}")
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

        if not month or not year:
            return jsonify({'error': 'Month and year required'}), 400

        date_filter = "EXTRACT(MONTH FROM date)::integer = :month AND EXTRACT(YEAR FROM date)::integer = :year"
        params = {"month": month, "year": year}

        if owner != 'all':
            date_filter += " AND owner = :owner"
            params["owner"] = owner

        with db.engine.connect() as conn:
            df = _df(conn, f"""
                SELECT category, SUM(amount) as actual_amount, COUNT(*) as transaction_count
                FROM transactions
                WHERE {date_filter} AND COALESCE(is_active, true) = true
                GROUP BY category ORDER BY actual_amount DESC
            """, params)

        result = [{
            'category': str(row['category']),
            'actual_amount': float(row['actual_amount']),
            'transaction_count': int(row['transaction_count'])
        } for _, row in df.iterrows()]

        return jsonify(result)

    except Exception as e:
        print(f"Error getting actual spending: {e}")
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
        now = datetime.utcnow()

        with db.engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO budget_templates (category, budget_amount, notes, is_active, created_at, updated_at)
                VALUES (:cat, :amount, :notes, true, :now, :now)
                ON CONFLICT (category, user_id) DO UPDATE
                SET budget_amount = EXCLUDED.budget_amount,
                    notes = EXCLUDED.notes,
                    updated_at = EXCLUDED.updated_at
            """), {"cat": category, "amount": budget_amount, "notes": notes, "now": now})

        return jsonify({'success': True, 'message': 'Budget template updated successfully'})

    except Exception as e:
        print(f"Error updating budget template: {e}")
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
        with db.engine.connect() as conn:
            templates_df = _df(conn, """
                SELECT category, sub_category, budget_amount, notes, budget_by_category, is_active
                FROM budget_subcategory_templates ORDER BY category, sub_category
            """)

            if templates_df.empty:
                # Auto-create from transaction subcategories
                subcats_df = _df(conn, """
                    SELECT DISTINCT category, sub_category FROM transactions
                    WHERE sub_category IS NOT NULL AND sub_category != ''
                    ORDER BY category, sub_category
                """)
                now = datetime.utcnow()
                with db.engine.begin() as write_conn:
                    for _, row in subcats_df.iterrows():
                        write_conn.execute(text("""
                            INSERT INTO budget_subcategory_templates
                            (category, sub_category, budget_amount, notes, is_active, created_at, updated_at)
                            VALUES (:cat, :sub, 0.00, '', true, :now, :now)
                            ON CONFLICT DO NOTHING
                        """), {"cat": row['category'], "sub": row['sub_category'], "now": now})

                with db.engine.connect() as conn2:
                    templates_df = _df(conn2, """
                        SELECT category, sub_category, budget_amount, notes, is_active
                        FROM budget_subcategory_templates WHERE is_active = true
                        ORDER BY category, sub_category
                    """)

            commitments_df = _df(conn, """
                SELECT category, sub_category, COALESCE(SUM(estimated_amount), 0) as total_commitment
                FROM budget_commitments WHERE is_active = true
                GROUP BY category, sub_category
            """)

        result = []
        for _, row in templates_df.iterrows():
            category = str(row['category'])
            sub_category = str(row['sub_category'])
            budget_amount = float(row['budget_amount'])

            commitment_row = commitments_df[
                (commitments_df['category'] == category) &
                (commitments_df['sub_category'] == sub_category)
            ]
            commitment_minimum = float(commitment_row.iloc[0]['total_commitment']) if not commitment_row.empty else 0.0
            effective_budget = max(budget_amount, commitment_minimum)

            result.append({
                'category': category,
                'sub_category': sub_category,
                'budget_amount': effective_budget,
                'commitment_minimum': commitment_minimum,
                'notes': str(row['notes']) if row['notes'] else '',
                'budget_by_category': bool(row.get('budget_by_category', False)),
                'is_active': bool(row['is_active'])
            })

        return jsonify(result)

    except Exception as e:
        print(f"Error getting subcategory templates: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@budgets_bp.route('/api/subcategory_templates/sync', methods=['POST'])
def sync_subcategory_templates():
    """Sync budget templates with current transaction subcategories"""
    try:
        with db.engine.connect() as conn:
            subcats_df = _df(conn, """
                SELECT DISTINCT category, sub_category FROM transactions
                WHERE sub_category IS NOT NULL AND sub_category != ''
                ORDER BY category, sub_category
            """)
            existing_df = _df(conn, """
                SELECT category, sub_category FROM budget_subcategory_templates
            """)

        transaction_pairs = set(
            (row['category'], row['sub_category']) for _, row in subcats_df.iterrows()
        )
        existing_pairs = set(
            (row['category'], row['sub_category']) for _, row in existing_df.iterrows()
        )

        to_add = transaction_pairs - existing_pairs
        to_remove = existing_pairs - transaction_pairs

        now = datetime.utcnow()
        added_count = removed_count = 0

        with db.engine.begin() as conn:
            for category, sub_category in to_add:
                conn.execute(text("""
                    INSERT INTO budget_subcategory_templates
                    (category, sub_category, budget_amount, notes, budget_by_category, is_active, created_at, updated_at)
                    VALUES (:cat, :sub, 0.00, '', false, true, :now, :now)
                    ON CONFLICT DO NOTHING
                """), {"cat": category, "sub": sub_category, "now": now})
                added_count += 1

            for category, sub_category in to_remove:
                conn.execute(text("""
                    DELETE FROM budget_subcategory_templates
                    WHERE category = :cat AND sub_category = :sub
                """), {"cat": category, "sub": sub_category})
                removed_count += 1

        message = f'Sync complete: {added_count} added, {removed_count} removed'
        return jsonify({'success': True, 'message': message, 'added_count': added_count, 'removed_count': removed_count})

    except Exception as e:
        print(f"Error syncing subcategory templates: {e}")
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
        now = datetime.utcnow()

        with db.engine.begin() as conn:
            # Check commitment minimum
            result = conn.execute(text("""
                SELECT COALESCE(SUM(estimated_amount), 0) as total_commitment
                FROM budget_commitments WHERE category = :cat AND sub_category = :sub AND is_active = true
            """), {"cat": category, "sub": sub_category}).fetchone()
            total_commitment = float(result[0]) if result else 0.0

            if budget_amount < total_commitment:
                return jsonify({
                    'success': False,
                    'error': f'Budget cannot be less than total commitments (${total_commitment:.2f})',
                    'minimum_budget': total_commitment
                }), 400

            conn.execute(text("""
                INSERT INTO budget_subcategory_templates
                (category, sub_category, budget_amount, notes, budget_by_category, is_active, created_at, updated_at)
                VALUES (:cat, :sub, :amount, :notes, :by_cat, :active, :now, :now)
                ON CONFLICT (category, sub_category, user_id) DO UPDATE SET
                    budget_amount = EXCLUDED.budget_amount,
                    notes = EXCLUDED.notes,
                    budget_by_category = EXCLUDED.budget_by_category,
                    is_active = EXCLUDED.is_active,
                    updated_at = EXCLUDED.updated_at
            """), {
                "cat": category, "sub": sub_category, "amount": budget_amount,
                "notes": notes, "by_cat": budget_by_category, "active": is_active, "now": now
            })

        return jsonify({'success': True, 'message': 'Subcategory budget updated successfully'})

    except Exception as e:
        print(f"Error updating subcategory budget: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@budgets_bp.route('/api/subcategory_templates/batch_update', methods=['POST'])
def batch_update_subcategory_templates():
    """Batch update multiple subcategory budgets at once"""
    try:
        data = request.get_json()
        budgets = data.get('budgets', [])
        now = datetime.utcnow()

        with db.engine.begin() as conn:
            for budget in budgets:
                conn.execute(text("""
                    INSERT INTO budget_subcategory_templates
                    (category, sub_category, budget_amount, notes, is_active, created_at, updated_at)
                    VALUES (:cat, :sub, :amount, :notes, true, :now, :now)
                    ON CONFLICT (category, sub_category, user_id) DO UPDATE SET
                        budget_amount = EXCLUDED.budget_amount,
                        notes = EXCLUDED.notes,
                        updated_at = EXCLUDED.updated_at
                """), {
                    "cat": budget['category'], "sub": budget['sub_category'],
                    "amount": float(budget['budget_amount']), "notes": budget.get('notes', ''),
                    "now": now
                })

        return jsonify({'success': True, 'message': f'{len(budgets)} budgets updated successfully'})

    except Exception as e:
        print(f"Error batch updating subcategory budgets: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@budgets_bp.route('/api/subcategory_templates/toggle_granularity', methods=['POST'])
def toggle_category_granularity():
    """Toggle budget granularity for an entire category"""
    try:
        data = request.get_json()
        category = data['category']
        budget_by_category = data['budget_by_category']

        with db.engine.begin() as conn:
            result = conn.execute(text("""
                UPDATE budget_subcategory_templates
                SET budget_by_category = :by_cat, updated_at = :now
                WHERE category = :cat AND is_active = true
            """), {"by_cat": budget_by_category, "now": datetime.utcnow(), "cat": category})
            rows_updated = result.rowcount

        return jsonify({'success': True, 'message': f'Updated {rows_updated} subcategories', 'rows_updated': rows_updated})

    except Exception as e:
        print(f"Error toggling category granularity: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# BUDGET RECOMMENDATION ENDPOINTS
# ============================================================================

@budgets_bp.route('/api/recommend_budgets')
def api_recommend_budgets():
    """Calculate budget recommendations based on spending history"""
    try:
        owner = request.args.get('owner', None)
        if owner == 'all':
            owner = None

        recommendations = calculate_subcategory_recommendations(owner=owner)
        return jsonify({'success': True, 'recommendations': recommendations, 'count': len(recommendations)})

    except Exception as e:
        print(f"Error calculating budget recommendations: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@budgets_bp.route('/api/migrate_budgets', methods=['POST'])
def api_migrate_budgets():
    """Migrate existing category budgets to subcategory budgets"""
    try:
        stats = migrate_category_budgets_to_subcategories()
        return jsonify({'success': True, 'message': 'Budget migration completed successfully', 'stats': stats})

    except Exception as e:
        print(f"Error migrating budgets: {e}")
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
        with db.engine.connect() as conn:
            df = _df(conn, """
                SELECT id, name, category, sub_category, estimated_amount,
                       due_day_of_month, is_fixed, created_at
                FROM budget_commitments WHERE is_active = true
                ORDER BY due_day_of_month, name
            """)

        result = [{
            'id': int(row['id']),
            'name': str(row['name']),
            'category': str(row['category']),
            'sub_category': str(row['sub_category']),
            'estimated_amount': float(row['estimated_amount']),
            'due_day_of_month': int(row['due_day_of_month']),
            'is_fixed': bool(row['is_fixed']),
            'created_at': str(row['created_at'])
        } for _, row in df.iterrows()]

        return jsonify(result)

    except Exception as e:
        print(f"Error getting commitments: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@budgets_bp.route('/api/commitments', methods=['POST'])
def api_add_commitment():
    """Add a new budget commitment"""
    try:
        data = request.get_json()
        due_day_of_month = int(data['due_day_of_month'])

        if due_day_of_month < 1 or due_day_of_month > 31:
            return jsonify({'success': False, 'error': 'Due day must be between 1 and 31'}), 400

        now = datetime.utcnow()

        with db.engine.begin() as conn:
            result = conn.execute(text("""
                INSERT INTO budget_commitments
                (name, category, sub_category, estimated_amount, due_day_of_month,
                 is_fixed, is_active, created_at, updated_at)
                VALUES (:name, :cat, :sub, :amount, :due_day, :is_fixed, true, :now, :now)
                RETURNING id
            """), {
                "name": data['name'], "cat": data['category'], "sub": data['sub_category'],
                "amount": float(data['estimated_amount']), "due_day": due_day_of_month,
                "is_fixed": data.get('is_fixed', True), "now": now
            })
            commitment_id = result.fetchone()[0]
            sync_budgets_from_commitments(conn)

        return jsonify({'success': True, 'id': commitment_id, 'message': 'Commitment added successfully'})

    except Exception as e:
        print(f"Error adding commitment: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@budgets_bp.route('/api/commitments/<int:commitment_id>', methods=['PUT'])
def api_update_commitment(commitment_id):
    """Update an existing budget commitment"""
    try:
        data = request.get_json()
        due_day_of_month = int(data['due_day_of_month'])

        if due_day_of_month < 1 or due_day_of_month > 31:
            return jsonify({'success': False, 'error': 'Due day must be between 1 and 31'}), 400

        with db.engine.begin() as conn:
            result = conn.execute(text("""
                UPDATE budget_commitments
                SET name = :name, category = :cat, sub_category = :sub, estimated_amount = :amount,
                    due_day_of_month = :due_day, is_fixed = :is_fixed, updated_at = :now
                WHERE id = :id AND is_active = true
            """), {
                "name": data['name'], "cat": data['category'], "sub": data['sub_category'],
                "amount": float(data['estimated_amount']), "due_day": due_day_of_month,
                "is_fixed": data.get('is_fixed', True), "now": datetime.utcnow(), "id": commitment_id
            })

            if result.rowcount == 0:
                return jsonify({'success': False, 'error': 'Commitment not found'}), 404

            sync_budgets_from_commitments(conn)

        return jsonify({'success': True, 'message': 'Commitment updated successfully'})

    except Exception as e:
        print(f"Error updating commitment: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@budgets_bp.route('/api/commitments/<int:commitment_id>', methods=['DELETE'])
def api_delete_commitment(commitment_id):
    """Delete (deactivate) a budget commitment"""
    try:
        with db.engine.begin() as conn:
            result = conn.execute(text("""
                UPDATE budget_commitments SET is_active = false, updated_at = :now
                WHERE id = :id AND is_active = true
            """), {"now": datetime.utcnow(), "id": commitment_id})

            if result.rowcount == 0:
                return jsonify({'success': False, 'error': 'Commitment not found'}), 404

            sync_budgets_from_commitments(conn)

        return jsonify({'success': True, 'message': 'Commitment deleted successfully'})

    except Exception as e:
        print(f"Error deleting commitment: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@budgets_bp.route('/api/commitments/summary')
def api_commitment_summary():
    """Get summary of all commitments"""
    try:
        summary = get_commitment_summary()
        return jsonify(summary)
    except Exception as e:
        print(f"Error getting commitment summary: {e}")
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

        if not month or not year:
            return jsonify({'error': 'Month and year required'}), 400

        date_filter = "EXTRACT(MONTH FROM date)::integer = :month AND EXTRACT(YEAR FROM date)::integer = :year"
        params = {"month": month, "year": year}

        if owner != 'all':
            date_filter += " AND owner = :owner"
            params["owner"] = owner

        with db.engine.connect() as conn:
            df = _df(conn, f"""
                SELECT category, sub_category, SUM(ABS(amount)) as actual_amount, COUNT(*) as transaction_count
                FROM transactions
                WHERE {date_filter}
                AND sub_category IS NOT NULL AND sub_category != ''
                AND type IN ('Needs', 'Wants', 'Business')
                AND COALESCE(is_active, true) = true
                GROUP BY category, sub_category
                ORDER BY category, sub_category
            """, params)

        result = [{
            'category': str(row['category']),
            'sub_category': str(row['sub_category']),
            'actual_amount': float(row['actual_amount']),
            'transaction_count': int(row['transaction_count'])
        } for _, row in df.iterrows()]

        return jsonify(result)

    except Exception as e:
        print(f"Error getting actual spending by subcategory: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
