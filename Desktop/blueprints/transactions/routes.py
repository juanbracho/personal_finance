from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
from models import db
from sqlalchemy import text
import pandas as pd
from utils import uid_clause, current_user_id

transactions_bp = Blueprint('transactions', __name__, url_prefix='/transactions')


def _df(conn, sql, params=None):
    return pd.read_sql_query(text(sql), conn, params=params or {})


@transactions_bp.route('/')
def list_transactions():
    """List all transactions with pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        _allowed_per_page = [25, 50, 100, 150, 200, 250]
        per_page = request.args.get('per_page', 50, type=int)
        if per_page not in _allowed_per_page:
            per_page = 50
        offset = (page - 1) * per_page

        uid_sql, uid_p = uid_clause()
        with db.engine.connect() as conn:
            total = conn.execute(text(
                f"SELECT COUNT(*) FROM transactions WHERE COALESCE(is_active, true) = true {uid_sql}"
            ), uid_p).scalar() or 0

            rows = conn.execute(text(f"""
                SELECT id, account_name, date, description, amount, sub_category,
                       category, type, owner, is_business, debt_payment_id, is_active,
                       created_at, updated_at
                FROM transactions
                WHERE COALESCE(is_active, true) = true {uid_sql}
                ORDER BY date DESC, id DESC
                LIMIT :limit OFFSET :offset
            """), {"limit": per_page, "offset": offset, **uid_p}).fetchall()

            # Build types list
            txn_types = [r[0] for r in conn.execute(text(
                f"SELECT DISTINCT type FROM transactions WHERE type IS NOT NULL AND type != '' {uid_sql} ORDER BY type"
            ), uid_p).fetchall()]

        _defaults = ['Needs', 'Wants', 'Savings', 'Business']
        seen = set(_defaults)
        types_list = _defaults.copy()
        for t in txn_types:
            if t not in seen:
                seen.add(t)
                types_list.append(t)

        # Convert rows to objects for template
        column_names = ['id', 'account_name', 'date', 'description', 'amount',
                        'sub_category', 'category', 'type', 'owner', 'is_business',
                        'debt_payment_id', 'is_active', 'created_at', 'updated_at']
        transaction_items = []
        for row in rows:
            obj = type('Transaction', (), {})()
            for i, col in enumerate(column_names):
                val = row[i]
                if col == 'date' and val is not None and isinstance(val, str):
                    val = datetime.strptime(val, '%Y-%m-%d').date()
                setattr(obj, col, val)
            transaction_items.append(obj)

        has_prev = page > 1
        has_next = offset + per_page < total
        pages = (total + per_page - 1) // per_page

        pagination = type('Pagination', (), {})()
        pagination.items = transaction_items
        pagination.total = total
        pagination.page = page
        pagination.pages = pages
        pagination.has_prev = has_prev
        pagination.has_next = has_next
        pagination.prev_num = page - 1 if has_prev else None
        pagination.next_num = page + 1 if has_next else None

        def iter_pages():
            start = max(1, page - 2)
            end = min(pages + 1, page + 3)
            for p in range(start, end):
                yield p
        pagination.iter_pages = iter_pages

        return render_template('transactions.html', transactions=pagination, per_page=per_page, types=types_list)

    except Exception as e:
        print(f"Error in transactions route: {e}")
        import traceback
        traceback.print_exc()
        empty_pagination = type('Pagination', (), {
            'items': [], 'total': 0, 'page': 1, 'pages': 0,
            'has_prev': False, 'has_next': False,
            'iter_pages': lambda: []
        })()
        return render_template('transactions.html', transactions=empty_pagination, per_page=50)


@transactions_bp.route('/add', methods=['GET', 'POST'])
def add_transaction():
    """Add new transaction with dynamic category/account/owner handling"""
    if request.method == 'POST':
        try:
            account_name = request.form.get('account_name', '').strip()
            date_str = request.form.get('date', '').strip()
            description = request.form.get('description', '').strip()
            amount_str = request.form.get('amount', '').strip()
            sub_category = request.form.get('sub_category', '').strip()
            category = request.form.get('category', '').strip()
            transaction_type = request.form.get('type', '').strip()
            owner = request.form.get('owner', '').strip()
            is_business = request.form.get('is_business') == 'on'
            is_credit = request.form.get('is_credit') == 'on'
            save_and_add_another = request.form.get('save_and_add_another') == 'true'

            if not all([account_name, date_str, description, amount_str, category, transaction_type, owner]):
                flash('All required fields must be filled out', 'error')
                raise ValueError("Missing required fields")

            try:
                amount = float(amount_str)
                transaction_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except (ValueError, TypeError) as e:
                flash(f'Invalid data format: {str(e)}', 'error')
                raise

            if amount == 0:
                flash('Amount cannot be zero', 'error')
                raise ValueError("Amount cannot be zero")

            now = datetime.utcnow()

            with db.engine.begin() as conn:
                if is_credit:
                    # Find debt account
                    debt_result = conn.execute(text("""
                        SELECT id, current_balance FROM debt_accounts
                        WHERE name = :name AND is_active = true
                    """), {"name": account_name}).fetchone()

                    if not debt_result:
                        debt_result = conn.execute(text("""
                            SELECT id, current_balance FROM debt_accounts WHERE name = :name
                        """), {"name": account_name}).fetchone()

                    if not debt_result:
                        flash(f'Debt account "{account_name}" not found', 'error')
                        raise ValueError(f"Debt account not found: {account_name}")

                    debt_account_id, current_balance = debt_result[0], debt_result[1]

                    conn.execute(text("""
                        INSERT INTO debt_charges
                        (debt_account_id, charge_amount, charge_date, description, category, charge_type, is_paid, notes, created_at)
                        VALUES (:debt_id, :amount, :date, :desc, :cat, 'Purchase', false, :notes, :now)
                    """), {
                        "debt_id": debt_account_id, "amount": amount,
                        "date": transaction_date, "desc": description,
                        "cat": category, "notes": sub_category or None, "now": now
                    })

                    new_balance = float(current_balance) + amount
                    conn.execute(text("""
                        UPDATE debt_accounts SET current_balance = :bal, is_active = true, updated_at = :now
                        WHERE id = :id
                    """), {"bal": new_balance, "now": now, "id": debt_account_id})

                    success_msg = f'Credit charge added! ${abs(amount):.2f} - {description} on {account_name}'
                else:
                    # Ensure category exists
                    if category:
                        exists = conn.execute(text(
                            "SELECT id FROM budget_templates WHERE category = :cat"
                        ), {"cat": category}).fetchone()
                        if not exists:
                            conn.execute(text("""
                                INSERT INTO budget_templates (category, budget_amount, notes, is_active, created_at, updated_at)
                                VALUES (:cat, 0.00, 'Added from transaction form', true, :now, :now)
                                ON CONFLICT DO NOTHING
                            """), {"cat": category, "now": now})

                    result = conn.execute(text("""
                        INSERT INTO transactions
                        (account_name, date, description, amount, sub_category, category, type, owner,
                         is_business, is_active, user_id, created_at, updated_at)
                        VALUES (:account, :date, :desc, :amount, :sub_cat, :cat, :type, :owner,
                                :is_business, true, :user_id, :now, :now)
                        RETURNING id
                    """), {
                        "account": account_name, "date": transaction_date, "desc": description,
                        "amount": amount, "sub_cat": sub_category or None, "cat": category,
                        "type": transaction_type, "owner": owner, "is_business": is_business,
                        "user_id": current_user_id(), "now": now
                    })
                    transaction_id = result.fetchone()[0]
                    transaction_display = "Income" if amount < 0 else "Expense"
                    success_msg = f'{transaction_display} added! ${abs(amount):.2f} - {description}'

            if save_and_add_another:
                flash(f'{success_msg} Add another transaction below.', 'success')
                return redirect(url_for('transactions.add_transaction'))
            else:
                flash(success_msg, 'success')
                return redirect(url_for('transactions.list_transactions') if not is_credit else url_for('debts.list_debts'))

        except Exception as e:
            print(f"Error adding transaction: {e}")
            import traceback
            traceback.print_exc()
            flash(f'Error adding transaction: {str(e)}', 'error')

    # GET request
    try:
        uid_sql, uid_p = uid_clause()
        with db.engine.connect() as conn:
            categories_df = _df(conn, f"""
                SELECT DISTINCT category FROM budget_templates
                WHERE is_active = true AND category IS NOT NULL {uid_sql}
                UNION
                SELECT DISTINCT category FROM transactions WHERE category IS NOT NULL {uid_sql}
                ORDER BY category
            """, uid_p)
            sub_categories_df = _df(conn, f"""
                SELECT DISTINCT sub_category FROM transactions
                WHERE sub_category IS NOT NULL AND sub_category != '' {uid_sql}
                ORDER BY sub_category
            """, uid_p)
            accounts_df = _df(conn, f"""
                SELECT DISTINCT account_name FROM transactions
                WHERE account_name IS NOT NULL {uid_sql} ORDER BY account_name
            """, uid_p)
            owners_df = _df(conn, f"""
                SELECT DISTINCT owner FROM transactions
                WHERE owner IS NOT NULL {uid_sql} ORDER BY owner
            """, uid_p)
            txn_types = [r[0] for r in conn.execute(text(
                f"SELECT DISTINCT type FROM transactions WHERE type IS NOT NULL AND type != '' {uid_sql} ORDER BY type"
            ), uid_p).fetchall()]

        categories_list = categories_df['category'].tolist()
        sub_categories_list = sub_categories_df['sub_category'].tolist()
        accounts_list = accounts_df['account_name'].tolist()
        owners_list = owners_df['owner'].tolist()

        _defaults = ['Needs', 'Wants', 'Savings', 'Business']
        seen = set(_defaults)
        types_list = _defaults.copy()
        for t in txn_types:
            if t not in seen:
                seen.add(t)
                types_list.append(t)

        if not accounts_list:
            accounts_list = ['Venture', 'Cacas', 'Cata']
        if not owners_list:
            owners_list = []

        return render_template('add_transaction.html',
                             categories=categories_list, sub_categories=sub_categories_list,
                             accounts=accounts_list, owners=owners_list, types=types_list)

    except Exception as e:
        print(f"Error loading form data: {e}")
        import traceback
        traceback.print_exc()
        return render_template('add_transaction.html',
                             categories=[], sub_categories=[],
                             accounts=['Venture', 'Cacas', 'Cata'],
                             owners=[], types=['Needs', 'Wants', 'Savings', 'Business'])


@transactions_bp.route('/bulk', methods=['GET', 'POST'])
def bulk_transaction():
    """Add multiple transactions with shared common fields"""
    import json

    if request.method == 'POST':
        try:
            account_name = request.form.get('account_name', '').strip()
            category = request.form.get('category', '').strip()
            sub_category = request.form.get('sub_category', '').strip()
            transaction_type = request.form.get('type', '').strip()
            owner = request.form.get('owner', '').strip()

            if not all([account_name, category, transaction_type, owner]):
                flash('All required common fields must be filled out', 'error')
                raise ValueError("Missing required common fields")

            items_json = request.form.get('transaction_items', '[]')
            items = json.loads(items_json)

            if not items:
                flash('At least one transaction item is required', 'error')
                raise ValueError("No transaction items provided")

            now = datetime.utcnow()
            success_count = error_count = 0

            with db.engine.begin() as conn:
                # Ensure category exists
                if category:
                    conn.execute(text("""
                        INSERT INTO budget_templates (category, budget_amount, notes, is_active, created_at, updated_at)
                        VALUES (:cat, 0.00, 'Added from bulk transaction form', true, :now, :now)
                        ON CONFLICT DO NOTHING
                    """), {"cat": category, "now": now})

                for item in items:
                    try:
                        item_date = item.get('date', '').strip()
                        item_description = item.get('description', '').strip()
                        item_amount = float(item.get('amount', 0))

                        if not item_date or not item_description or item_amount == 0:
                            error_count += 1
                            continue

                        transaction_date = datetime.strptime(item_date, '%Y-%m-%d').date()

                        conn.execute(text("""
                            INSERT INTO transactions
                            (account_name, date, description, amount, sub_category, category,
                             type, owner, is_business, is_active, user_id, created_at, updated_at)
                            VALUES (:account, :date, :desc, :amount, :sub_cat, :cat,
                                    :type, :owner, false, true, :user_id, :now, :now)
                        """), {
                            "account": account_name, "date": transaction_date,
                            "desc": item_description, "amount": item_amount,
                            "sub_cat": sub_category or None, "cat": category,
                            "type": transaction_type, "owner": owner,
                            "user_id": current_user_id(), "now": now
                        })
                        success_count += 1
                    except Exception:
                        error_count += 1

            if error_count == 0:
                flash(f'Successfully added {success_count} transactions!', 'success')
            else:
                flash(f'Added {success_count} transactions. {error_count} items had errors.', 'warning')

            return redirect(url_for('transactions.list_transactions'))

        except json.JSONDecodeError:
            flash('Error parsing transaction items', 'error')
            return redirect(url_for('transactions.bulk_transaction'))
        except Exception as e:
            print(f"Error in bulk transaction: {e}")
            import traceback
            traceback.print_exc()
            flash(f'Error processing bulk transaction: {str(e)}', 'error')
            return redirect(url_for('transactions.bulk_transaction'))

    # GET request
    try:
        uid_sql, uid_p = uid_clause()
        with db.engine.connect() as conn:
            categories_df = _df(conn, f"""
                SELECT DISTINCT category FROM budget_templates
                WHERE is_active = true AND category IS NOT NULL {uid_sql}
                UNION
                SELECT DISTINCT category FROM transactions WHERE category IS NOT NULL {uid_sql}
                ORDER BY category
            """, uid_p)
            sub_categories_df = _df(conn, f"""
                SELECT DISTINCT sub_category FROM transactions
                WHERE sub_category IS NOT NULL AND sub_category != '' {uid_sql}
                ORDER BY sub_category
            """, uid_p)
            accounts_df = _df(conn, f"""
                SELECT DISTINCT account_name FROM transactions
                WHERE account_name IS NOT NULL {uid_sql} ORDER BY account_name
            """, uid_p)
            owners_df = _df(conn, f"""
                SELECT DISTINCT owner FROM transactions
                WHERE owner IS NOT NULL {uid_sql} ORDER BY owner
            """, uid_p)
            txn_types = [r[0] for r in conn.execute(text(
                f"SELECT DISTINCT type FROM transactions WHERE type IS NOT NULL AND type != '' {uid_sql} ORDER BY type"
            ), uid_p).fetchall()]

        categories_list = categories_df['category'].tolist()
        sub_categories_list = sub_categories_df['sub_category'].tolist()
        accounts_list = accounts_df['account_name'].tolist()
        owners_list = owners_df['owner'].tolist()

        _defaults = ['Needs', 'Wants', 'Savings', 'Business']
        seen = set(_defaults)
        types_list = _defaults.copy()
        for t in txn_types:
            if t not in seen:
                seen.add(t)
                types_list.append(t)

        if not accounts_list:
            accounts_list = ['Venture', 'Cacas', 'Cata']

        return render_template('bulk_transaction.html',
                             categories=categories_list, sub_categories=sub_categories_list,
                             accounts=accounts_list, owners=owners_list, types=types_list)

    except Exception as e:
        print(f"Error loading bulk form data: {e}")
        import traceback
        traceback.print_exc()
        return render_template('bulk_transaction.html',
                             categories=[], sub_categories=[],
                             accounts=['Venture', 'Cacas', 'Cata'],
                             owners=[], types=['Needs', 'Wants', 'Savings', 'Business'])


@transactions_bp.route('/api/get_transaction/<int:transaction_id>')
def get_transaction(transaction_id):
    """Get transaction details for editing"""
    try:
        uid_sql, uid_p = uid_clause()
        with db.engine.connect() as conn:
            df = _df(conn, f"""
                SELECT id, account_name, date, description, amount, sub_category,
                       category, type, owner, is_business, debt_payment_id, created_at, updated_at
                FROM transactions WHERE id = :id {uid_sql}
            """, {"id": transaction_id, **uid_p})

        if df.empty:
            return jsonify({'success': False, 'error': 'Transaction not found'}), 404

        transaction = df.iloc[0].to_dict()
        transaction['is_business'] = bool(transaction['is_business'])
        transaction['sub_category'] = transaction['sub_category'] if transaction['sub_category'] else ''
        transaction['amount'] = float(transaction['amount'])
        transaction['date'] = str(transaction['date'])

        return jsonify({'success': True, 'transaction': transaction})

    except Exception as e:
        print(f"Error getting transaction: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@transactions_bp.route('/api/update_transaction/<int:transaction_id>', methods=['PUT'])
def update_transaction(transaction_id):
    """Update an existing transaction"""
    try:
        data = request.get_json()

        required_fields = ['account_name', 'date', 'description', 'amount', 'category', 'type', 'owner']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field} is required'}), 400

        try:
            amount = float(data['amount'])
            if amount == 0:
                return jsonify({'success': False, 'error': 'Amount cannot be zero'}), 400
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'Invalid amount format'}), 400

        try:
            transaction_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid date format'}), 400

        now = datetime.utcnow()

        uid_sql, uid_p = uid_clause()
        with db.engine.begin() as conn:
            exists = conn.execute(text(
                f"SELECT id FROM transactions WHERE id = :id {uid_sql}"
            ), {"id": transaction_id, **uid_p}).fetchone()
            if not exists:
                return jsonify({'success': False, 'error': 'Transaction not found'}), 404

            category = data['category']
            if category:
                conn.execute(text("""
                    INSERT INTO budget_templates (category, budget_amount, notes, is_active, created_at, updated_at)
                    VALUES (:cat, 0.00, 'Added from transaction update', true, :now, :now)
                    ON CONFLICT DO NOTHING
                """), {"cat": category, "now": now})

            result = conn.execute(text(f"""
                UPDATE transactions
                SET account_name = :account, date = :date, description = :desc, amount = :amount,
                    sub_category = :sub_cat, category = :cat, type = :type, owner = :owner,
                    is_business = :is_business, updated_at = :now
                WHERE id = :id {uid_sql}
            """), {
                "account": data['account_name'], "date": transaction_date, "desc": data['description'],
                "amount": amount, "sub_cat": data.get('sub_category') or None,
                "cat": category, "type": data['type'], "owner": data['owner'],
                "is_business": bool(data.get('is_business', False)), "now": now, "id": transaction_id,
                **uid_p
            })

            if result.rowcount == 0:
                return jsonify({'success': False, 'error': 'Transaction not found or no changes made'}), 404

        transaction_display = "Income" if amount < 0 else "Expense"
        return jsonify({
            'success': True,
            'message': f'Transaction updated! ${abs(amount):.2f} - {data["description"]}'
        })

    except Exception as e:
        print(f"Error updating transaction: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@transactions_bp.route('/api/delete_transaction/<int:transaction_id>', methods=['DELETE'])
def delete_transaction(transaction_id):
    """Mark transaction as inactive (soft delete)"""
    try:
        uid_sql, uid_p = uid_clause()
        with db.engine.begin() as conn:
            row = conn.execute(text(
                f"SELECT description, amount FROM transactions WHERE id = :id {uid_sql}"
            ), {"id": transaction_id, **uid_p}).fetchone()
            if not row:
                return jsonify({'success': False, 'error': 'Transaction not found'}), 404

            description, amount = row[0], row[1]

            result = conn.execute(text(f"""
                UPDATE transactions SET is_active = false, updated_at = :now WHERE id = :id {uid_sql}
            """), {"now": datetime.utcnow(), "id": transaction_id, **uid_p})

            if result.rowcount == 0:
                return jsonify({'success': False, 'error': 'Transaction not found'}), 404

        return jsonify({
            'success': True,
            'message': f'Transaction marked as inactive: ${abs(float(amount)):.2f} - {description}'
        })

    except Exception as e:
        print(f"Error deleting transaction: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@transactions_bp.route('/api/validate_category', methods=['POST'])
def validate_category():
    """Validate if a category exists or can be created"""
    try:
        data = request.get_json()
        category_name = data.get('name', '').strip()

        if not category_name:
            return jsonify({'valid': False, 'error': 'Category name required'})
        if len(category_name) < 2:
            return jsonify({'valid': False, 'error': 'Category name must be at least 2 characters'})

        with db.engine.connect() as conn:
            exists = conn.execute(text(
                "SELECT id FROM budget_templates WHERE category = :cat"
            ), {"cat": category_name}).fetchone() is not None

        return jsonify({
            'valid': True,
            'exists': exists,
            'message': 'Category exists' if exists else 'New category will be created'
        })

    except Exception as e:
        return jsonify({'valid': False, 'error': str(e)})


@transactions_bp.route('/api/add_category', methods=['POST'])
def add_category():
    """Add a new category to budget templates"""
    try:
        data = request.get_json()
        category_name = data.get('name', '').strip()

        if not category_name:
            return jsonify({'success': False, 'error': 'Category name required'})

        now = datetime.utcnow()
        with db.engine.begin() as conn:
            existing = conn.execute(text(
                "SELECT id FROM budget_templates WHERE category = :cat"
            ), {"cat": category_name}).fetchone()
            if existing:
                return jsonify({'success': False, 'error': 'Category already exists'})

            conn.execute(text("""
                INSERT INTO budget_templates (category, budget_amount, notes, is_active, created_at, updated_at)
                VALUES (:cat, 0.00, 'Added via transaction form', true, :now, :now)
            """), {"cat": category_name, "now": now})

        return jsonify({'success': True, 'message': f'Category "{category_name}" added successfully'})

    except Exception as e:
        print(f"Error adding category: {e}")
        return jsonify({'success': False, 'error': str(e)})


@transactions_bp.route('/api/search_similar', methods=['POST'])
def search_similar_transactions():
    """Search for similar transactions based on description"""
    try:
        data = request.get_json()
        search_term = data.get('description', '').strip()

        if len(search_term) < 3:
            return jsonify([])

        uid_sql, uid_p = uid_clause()
        with db.engine.connect() as conn:
            df = _df(conn, f"""
                SELECT description, category, sub_category, amount, account_name, owner, type
                FROM transactions
                WHERE description ILIKE :term {uid_sql}
                ORDER BY date DESC LIMIT 5
            """, {"term": f'%{search_term}%', **uid_p})

        result = [{
            'description': row['description'],
            'category': row['category'],
            'sub_category': row['sub_category'] if row['sub_category'] else '',
            'amount': float(row['amount']),
            'account_name': row['account_name'],
            'owner': row['owner'],
            'type': row['type']
        } for _, row in df.iterrows()]

        return jsonify(result)

    except Exception as e:
        print(f"Error searching similar transactions: {e}")
        return jsonify([])


@transactions_bp.route('/api/get_form_data')
def get_form_data():
    """Get current form data for dropdowns"""
    try:
        uid_sql, uid_p = uid_clause()
        with db.engine.connect() as conn:
            categories_df = _df(conn, f"""
                SELECT DISTINCT category FROM budget_templates
                WHERE is_active = true AND category IS NOT NULL {uid_sql}
                UNION
                SELECT DISTINCT category FROM transactions WHERE category IS NOT NULL {uid_sql}
                ORDER BY category
            """, uid_p)
            sub_categories_df = _df(conn, f"""
                SELECT DISTINCT sub_category FROM transactions
                WHERE sub_category IS NOT NULL AND sub_category != '' {uid_sql}
                ORDER BY sub_category
            """, uid_p)
            accounts_df = _df(conn, f"""
                SELECT DISTINCT account_name FROM transactions
                WHERE account_name IS NOT NULL {uid_sql} ORDER BY account_name
            """, uid_p)
            owners_df = _df(conn, f"""
                SELECT DISTINCT owner FROM transactions
                WHERE owner IS NOT NULL {uid_sql} ORDER BY owner
            """, uid_p)

        form_data = {
            'categories': categories_df['category'].tolist(),
            'sub_categories': sub_categories_df['sub_category'].tolist(),
            'accounts': accounts_df['account_name'].tolist(),
            'owners': owners_df['owner'].tolist()
        }

        if not form_data['accounts']:
            form_data['accounts'] = ['Venture', 'Cacas', 'Cata']

        return jsonify(form_data)

    except Exception as e:
        print(f"Error getting form data: {e}")
        return jsonify({
            'categories': [], 'sub_categories': [],
            'accounts': ['Venture', 'Cacas', 'Cata'], 'owners': []
        })


@transactions_bp.route('/api/transactions/common_patterns')
def api_common_transaction_patterns():
    """Return the most common transaction patterns for Quick Actions"""
    try:
        uid_sql, uid_p = uid_clause()
        with db.engine.connect() as conn:
            df = _df(conn, f"""
                SELECT category, sub_category, type, COUNT(*) as freq
                FROM transactions
                WHERE category IS NOT NULL AND category != ''
                  AND date >= CURRENT_DATE - INTERVAL '90 days' {uid_sql}
                GROUP BY category, sub_category, type
                ORDER BY freq DESC
                LIMIT 10
            """, uid_p)
        return jsonify(df.to_dict(orient='records'))
    except Exception as e:
        print(f"Error in common transaction patterns API: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@transactions_bp.route('/api/subcategories')
def api_get_subcategories():
    """Get distinct subcategories for a given category"""
    category = request.args.get('category')
    if not category:
        return jsonify({'error': 'Category parameter required'}), 400

    try:
        uid_sql, uid_p = uid_clause()
        with db.engine.connect() as conn:
            rows = conn.execute(text(f"""
                SELECT DISTINCT sub_category FROM transactions
                WHERE category = :cat AND sub_category IS NOT NULL AND sub_category != '' {uid_sql}
                ORDER BY sub_category
            """), {"cat": category, **uid_p}).fetchall()
        return jsonify([row[0] for row in rows])
    except Exception as e:
        print(f"Error getting subcategories: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
