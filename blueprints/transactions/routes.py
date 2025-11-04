from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
import pandas as pd
import sqlite3

# Create the blueprint
transactions_bp = Blueprint('transactions', __name__, url_prefix='/transactions')

@transactions_bp.route('/')
def list_transactions():
    """List all transactions with pagination"""
    
    print("📝 Loading transactions page...")
    
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 50
        offset = (page - 1) * per_page
        
        # Use raw SQL for consistency
        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()
        
        # First, ensure is_active column exists and set defaults
        try:
            cursor.execute("ALTER TABLE transactions ADD COLUMN is_active BOOLEAN DEFAULT 1")
            print("📄 Added is_active column to transactions table")
        except sqlite3.OperationalError:
            # Column already exists
            pass
        
        # Update any NULL is_active values to 1 (active)
        cursor.execute("UPDATE transactions SET is_active = 1 WHERE is_active IS NULL")
        updated_count = cursor.rowcount
        if updated_count > 0:
            print(f"📄 Updated {updated_count} transactions to set is_active = 1")
        
        conn.commit()
        
        # Debug: Check total transactions
        cursor.execute("SELECT COUNT(*) as total FROM transactions")
        total_all = cursor.fetchone()[0]
        print(f"📊 Total transactions in database: {total_all}")
        
        # Debug: Check active transactions
        cursor.execute("SELECT COUNT(*) as total FROM transactions WHERE COALESCE(is_active, 1) = 1")
        total_active = cursor.fetchone()[0]
        print(f"📊 Active transactions: {total_active}")
        
        # Debug: Check recent transactions
        cursor.execute("SELECT id, description, date, is_active FROM transactions ORDER BY date DESC, id DESC LIMIT 5")
        recent = cursor.fetchall()
        print(f"📊 Recent transactions: {recent}")
        
        # Get total count of active transactions
        count_query = "SELECT COUNT(*) as total FROM transactions WHERE COALESCE(is_active, 1) = 1"
        cursor.execute(count_query)
        total = cursor.fetchone()[0]
        print(f"📊 Total active transactions for pagination: {total}")
        
        # Get paginated transactions
        transactions_query = """
        SELECT * FROM transactions 
        WHERE COALESCE(is_active, 1) = 1
        ORDER BY date DESC, id DESC 
        LIMIT ? OFFSET ?
        """
        cursor.execute(transactions_query, [per_page, offset])
        transactions_data = cursor.fetchall()
        
        # Get column names
        column_names = [description[0] for description in cursor.description]
        print(f"📊 Found {len(transactions_data)} transactions for page {page}")
        
        conn.close()
        
        # Convert to objects for template
        transaction_items = []
        for row in transactions_data:
            transaction_obj = type('Transaction', (), {})()
            for i, col in enumerate(column_names):
                if col == 'date':
                    # Convert date string to date object
                    transaction_obj.date = datetime.strptime(row[i], '%Y-%m-%d').date()
                else:
                    setattr(transaction_obj, col, row[i])
            transaction_items.append(transaction_obj)
        
        # Calculate pagination info
        has_prev = page > 1
        has_next = offset + per_page < total
        pages = (total + per_page - 1) // per_page
        
        # Create pagination object
        pagination = type('Pagination', (), {})()
        pagination.items = transaction_items
        pagination.total = total
        pagination.page = page
        pagination.pages = pages
        pagination.has_prev = has_prev
        pagination.has_next = has_next
        pagination.prev_num = page - 1 if has_prev else None
        pagination.next_num = page + 1 if has_next else None
        
        # Add iter_pages method
        def iter_pages():
            start = max(1, page - 2)
            end = min(pages + 1, page + 3)
            for p in range(start, end):
                yield p
        pagination.iter_pages = iter_pages
        
        print(f"📝 Successfully loaded {len(transaction_items)} transactions, page {page}/{pages}")
        
        return render_template('transactions.html', transactions=pagination)
        
    except Exception as e:
        print(f"❌ Error in transactions route: {e}")
        import traceback
        traceback.print_exc()
        
        # Return empty pagination
        empty_pagination = type('Pagination', (), {})()
        empty_pagination.items = []
        empty_pagination.total = 0
        empty_pagination.page = 1
        empty_pagination.pages = 0
        empty_pagination.has_prev = False
        empty_pagination.has_next = False
        empty_pagination.iter_pages = lambda: []
        
        return render_template('transactions.html', transactions=empty_pagination)

@transactions_bp.route('/add', methods=['GET', 'POST'])
def add_transaction():
    """Add new transaction with dynamic category/account/owner handling"""
    
    print("💰 Loading add transaction page...")
    
    if request.method == 'POST':
        try:
            print("📥 Processing transaction form submission...")
            
            # Get form data with validation
            account_name = request.form.get('account_name', '').strip()
            date_str = request.form.get('date', '').strip()
            description = request.form.get('description', '').strip()
            amount_str = request.form.get('amount', '').strip()
            sub_category = request.form.get('sub_category', '').strip()
            category = request.form.get('category', '').strip()
            transaction_type = request.form.get('type', '').strip()
            owner = request.form.get('owner', '').strip()
            is_business = request.form.get('is_business') == 'on'
            is_credit = request.form.get('is_credit') == 'on'  # NEW: Credit transaction flag
            save_and_add_another = request.form.get('save_and_add_another') == 'true'

            print(f"📋 Form data: {description}, ${amount_str}, {category}, {owner}")
            print(f"📋 Save and add another: {save_and_add_another}")
            print(f"💳 Is credit: {is_credit}")
            
            # Validation
            if not all([account_name, date_str, description, amount_str, category, transaction_type, owner]):
                flash('All required fields must be filled out', 'error')
                raise ValueError("Missing required fields")
            
            # Convert and validate data types
            try:
                amount = float(amount_str)
                transaction_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except (ValueError, TypeError) as e:
                flash(f'Invalid data format: {str(e)}', 'error')
                raise
            
            # Allow negative numbers, only reject zero
            if amount == 0:
                flash('Amount cannot be zero', 'error')
                raise ValueError("Amount cannot be zero")
            
            # Log transaction type for debugging
            if amount < 0:
                print(f"💚 Adding INCOME transaction: {description} = ${amount}")
            else:
                print(f"🔴 Adding EXPENSE transaction: {description} = ${amount}")

            conn = sqlite3.connect('data/personal_finance.db')
            cursor = conn.cursor()

            # NEW: Check if this is a credit transaction
            if is_credit:
                print(f"💳 Processing credit transaction...")

                # Find debt account by name
                cursor.execute("""
                    SELECT id, current_balance
                    FROM debt_accounts
                    WHERE name = ? AND is_active = 1
                """, (account_name,))

                debt_result = cursor.fetchone()
                if not debt_result:
                    # Try to find any debt account with this name
                    cursor.execute("""
                        SELECT id, current_balance
                        FROM debt_accounts
                        WHERE name = ?
                    """, (account_name,))
                    debt_result = cursor.fetchone()

                if not debt_result:
                    flash(f'Debt account "{account_name}" not found', 'error')
                    raise ValueError(f"Debt account not found: {account_name}")

                debt_account_id, current_balance = debt_result

                # Create debt charge record
                cursor.execute("""
                    INSERT INTO debt_charges
                    (debt_account_id, charge_amount, charge_date, description, category, charge_type, is_paid, notes, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
                """, (
                    debt_account_id,
                    amount,
                    transaction_date.strftime('%Y-%m-%d'),
                    description,
                    category,
                    'Purchase',
                    sub_category if sub_category else None,
                    datetime.utcnow().isoformat()
                ))

                charge_id = cursor.lastrowid

                # Update debt balance and reopen if paid off
                new_balance = float(current_balance) + amount
                cursor.execute("""
                    UPDATE debt_accounts
                    SET current_balance = ?,
                        is_active = 1,
                        updated_at = ?
                    WHERE id = ?
                """, (new_balance, datetime.utcnow().isoformat(), debt_account_id))

                conn.commit()
                conn.close()

                print(f"✅ Added debt charge ID {charge_id}: {description} - ${amount:.2f}")
                print(f"💳 Debt balance updated: ${current_balance:.2f} → ${new_balance:.2f}")

                # Success message
                amount_display = f"${abs(amount):.2f}"
                success_msg = f'Credit charge added successfully! {amount_display} - {description} on {account_name}'

            else:
                # REGULAR TRANSACTION (existing flow)
                # Handle new category - add to budget templates if not exists
                if category:
                    cursor.execute("SELECT id FROM budget_templates WHERE category = ?", (category,))
                    if not cursor.fetchone():
                        print(f"➕ Adding new category to budget templates: {category}")
                        cursor.execute("""
                            INSERT INTO budget_templates (category, budget_amount, notes, is_active, created_at, updated_at)
                            VALUES (?, 0.00, 'Added from transaction form', 1, ?, ?)
                        """, (category, datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))

                # Insert transaction
                cursor.execute("""
                    INSERT INTO transactions
                    (account_name, date, description, amount, sub_category, category, type, owner, is_business, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """, (
                    account_name,
                    transaction_date.strftime('%Y-%m-%d'),
                    description,
                    amount,
                    sub_category if sub_category else None,
                    category,
                    transaction_type,
                    owner,
                    is_business,
                    datetime.utcnow().isoformat(),
                    datetime.utcnow().isoformat()
                ))

                transaction_id = cursor.lastrowid
                conn.commit()
                conn.close()

                # Success message
                transaction_display = "Income" if amount < 0 else "Expense"
                amount_display = f"${abs(amount):.2f}"
                success_msg = f'{transaction_display} added successfully! {amount_display} - {description}'

                print(f"✅ Added transaction ID {transaction_id}: {description} - {transaction_display} {amount_display}")
            
            # Handle redirect based on save_and_add_another parameter
            if save_and_add_another:
                flash(f'{success_msg} Add another transaction below.', 'success')
                return redirect(url_for('transactions.add_transaction'))
            else:
                flash(success_msg, 'success')
                return redirect(url_for('transactions.list_transactions') if not is_credit else url_for('debts.list_debts'))
            
        except Exception as e:
            print(f"❌ Error adding transaction: {e}")
            import traceback
            traceback.print_exc()
            flash(f'Error adding transaction: {str(e)}', 'error')
    
    # GET request - load form data
    try:
        print("📊 Loading form dropdown data...")
        
        conn = sqlite3.connect('data/personal_finance.db')
        
        # Get categories from budget templates (this ensures we have categories even in fresh DB)
        categories_df = pd.read_sql_query("""
            SELECT DISTINCT category FROM budget_templates 
            WHERE is_active = 1 AND category IS NOT NULL 
            UNION
            SELECT DISTINCT category FROM transactions 
            WHERE category IS NOT NULL
            ORDER BY category
        """, conn)
        
        # Get subcategories, accounts, and owners from existing transactions
        sub_categories_df = pd.read_sql_query("""
            SELECT DISTINCT sub_category FROM transactions 
            WHERE sub_category IS NOT NULL AND sub_category != '' 
            ORDER BY sub_category
        """, conn)
        
        accounts_df = pd.read_sql_query("""
            SELECT DISTINCT account_name FROM transactions 
            WHERE account_name IS NOT NULL 
            ORDER BY account_name
        """, conn)
        
        owners_df = pd.read_sql_query("""
            SELECT DISTINCT owner FROM transactions 
            WHERE owner IS NOT NULL 
            ORDER BY owner
        """, conn)
        
        conn.close()
        
        # Convert to lists for template
        categories_list = categories_df['category'].tolist()
        sub_categories_list = sub_categories_df['sub_category'].tolist()
        accounts_list = accounts_df['account_name'].tolist()
        owners_list = owners_df['owner'].tolist()
        
        # Add default options if empty (for fresh database)
        if not accounts_list:
            accounts_list = ['Venture', 'Cacas', 'Cata']
        
        if not owners_list:
            owners_list = ['Cata', 'Suricata', 'Cacas']
        
        print(f"📊 Dropdown data loaded:")
        print(f"   - Categories: {len(categories_list)} ({categories_list[:5]}...)")
        print(f"   - Sub-categories: {len(sub_categories_list)}")
        print(f"   - Accounts: {len(accounts_list)} ({accounts_list})")
        print(f"   - Owners: {len(owners_list)} ({owners_list})")
        
        return render_template('add_transaction.html',
                             categories=categories_list,
                             sub_categories=sub_categories_list,
                             accounts=accounts_list,
                             owners=owners_list)
                             
    except Exception as e:
        print(f"❌ Error loading form data: {e}")
        import traceback
        traceback.print_exc()
        
        # Return form with default lists
        return render_template('add_transaction.html',
                             categories=[],
                             sub_categories=[],
                             accounts=['Venture', 'Cacas', 'Cata'],
                             owners=['Cata', 'Suricata', 'Cacas'])

@transactions_bp.route('/api/get_transaction/<int:transaction_id>')
def get_transaction(transaction_id):
    """Get transaction details for editing"""
    
    try:
        print(f"📄 API: Getting transaction ID {transaction_id}")
        
        conn = sqlite3.connect('data/personal_finance.db')
        
        # Get transaction details
        transaction_query = """
        SELECT id, account_name, date, description, amount, sub_category, 
               category, type, owner, is_business, debt_payment_id,
               created_at, updated_at
        FROM transactions 
        WHERE id = ?
        """
        
        transaction_df = pd.read_sql_query(transaction_query, conn, params=[transaction_id])
        conn.close()
        
        if transaction_df.empty:
            return jsonify({'success': False, 'error': 'Transaction not found'}), 404
        
        # Convert to dictionary
        transaction = transaction_df.iloc[0].to_dict()
        
        # Convert boolean and handle None values
        transaction['is_business'] = bool(transaction['is_business'])
        transaction['sub_category'] = transaction['sub_category'] if transaction['sub_category'] else ''
        transaction['amount'] = float(transaction['amount'])
        
        print(f"📄 Returning transaction: {transaction['description']}")
        return jsonify({'success': True, 'transaction': transaction})
        
    except Exception as e:
        print(f"❌ Error getting transaction: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@transactions_bp.route('/api/update_transaction/<int:transaction_id>', methods=['PUT'])
def update_transaction(transaction_id):
    """Update an existing transaction"""
    
    try:
        data = request.get_json()
        print(f"📝 API: Updating transaction ID {transaction_id}")
        
        # Validate required fields
        required_fields = ['account_name', 'date', 'description', 'amount', 'category', 'type', 'owner']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field} is required'}), 400
        
        # Validate amount
        try:
            amount = float(data['amount'])
            if amount == 0:
                return jsonify({'success': False, 'error': 'Amount cannot be zero'}), 400
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'Invalid amount format'}), 400
        
        # Validate date
        try:
            transaction_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid date format'}), 400
        
        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()
        
        # Check if transaction exists
        cursor.execute("SELECT id FROM transactions WHERE id = ?", (transaction_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'Transaction not found'}), 404
        
        # Handle new category - add to budget templates if not exists
        category = data['category']
        if category:
            cursor.execute("SELECT id FROM budget_templates WHERE category = ?", (category,))
            if not cursor.fetchone():
                print(f"➕ Adding new category to budget templates: {category}")
                cursor.execute("""
                    INSERT INTO budget_templates (category, budget_amount, notes, is_active, created_at, updated_at)
                    VALUES (?, 0.00, 'Added from transaction update', 1, ?, ?)
                """, (category, datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
        
        # Update transaction
        cursor.execute("""
            UPDATE transactions 
            SET account_name = ?, date = ?, description = ?, amount = ?, 
                sub_category = ?, category = ?, type = ?, owner = ?, 
                is_business = ?, updated_at = ?
            WHERE id = ?
        """, (
            data['account_name'],
            transaction_date.strftime('%Y-%m-%d'),
            data['description'],
            amount,
            data.get('sub_category') if data.get('sub_category') else None,
            category,
            data['type'],
            data['owner'],
            bool(data.get('is_business', False)),
            datetime.utcnow().isoformat(),
            transaction_id
        ))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'success': False, 'error': 'Transaction not found or no changes made'}), 404
        
        conn.commit()
        conn.close()
        
        # Success message
        transaction_display = "Income" if amount < 0 else "Expense"
        amount_display = f"${abs(amount):.2f}"
        
        print(f"✅ Updated transaction ID {transaction_id}: {data['description']} - {transaction_display} {amount_display}")
        return jsonify({
            'success': True, 
            'message': f'Transaction updated successfully! {amount_display} - {data["description"]}'
        })
        
    except Exception as e:
        print(f"❌ Error updating transaction: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@transactions_bp.route('/api/delete_transaction/<int:transaction_id>', methods=['DELETE'])
def delete_transaction(transaction_id):
    """Mark transaction as inactive (soft delete)"""
    
    try:
        print(f"🗑️ API: Marking transaction ID {transaction_id} as inactive")
        
        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()
        
        # Check if transaction exists and get details for response
        cursor.execute("""
            SELECT description, amount FROM transactions 
            WHERE id = ?
        """, (transaction_id,))
        
        result = cursor.fetchone()
        if not result:
            conn.close()
            return jsonify({'success': False, 'error': 'Transaction not found'}), 404
        
        description, amount = result
        
        # Add is_active column if it doesn't exist
        try:
            cursor.execute("ALTER TABLE transactions ADD COLUMN is_active BOOLEAN DEFAULT 1")
            print("📄 Added is_active column to transactions table")
        except sqlite3.OperationalError:
            # Column already exists
            pass
        
        # Mark as inactive instead of deleting
        cursor.execute("""
            UPDATE transactions 
            SET is_active = 0, updated_at = ?
            WHERE id = ?
        """, (datetime.utcnow().isoformat(), transaction_id))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'success': False, 'error': 'Transaction not found'}), 404
        
        conn.commit()
        conn.close()
        
        transaction_display = "Income" if float(amount) < 0 else "Expense"
        amount_display = f"${abs(float(amount)):.2f}"
        
        print(f"✅ Marked transaction ID {transaction_id} as inactive: {description}")
        return jsonify({
            'success': True, 
            'message': f'Transaction marked as inactive: {amount_display} - {description}'
        })
        
    except Exception as e:
        print(f"❌ Error deleting transaction: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# API endpoints for dynamic form functionality
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
        
        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()
        
        # Check if category already exists
        cursor.execute("SELECT id FROM budget_templates WHERE category = ?", (category_name,))
        exists = cursor.fetchone() is not None
        
        conn.close()
        
        return jsonify({
            'valid': True, 
            'exists': exists,
            'message': 'Category exists' if exists else 'New category will be created'
        })
        
    except Exception as e:
        print(f"❌ Error validating category: {e}")
        return jsonify({'valid': False, 'error': str(e)})

@transactions_bp.route('/api/add_category', methods=['POST'])
def add_category():
    """Add a new category to budget templates"""
    
    try:
        data = request.get_json()
        category_name = data.get('name', '').strip()
        
        if not category_name:
            return jsonify({'success': False, 'error': 'Category name required'})
        
        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()
        
        # Check if category already exists
        cursor.execute("SELECT id FROM budget_templates WHERE category = ?", (category_name,))
        if cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'Category already exists'})
        
        # Add new category
        cursor.execute("""
            INSERT INTO budget_templates (category, budget_amount, notes, is_active, created_at, updated_at)
            VALUES (?, 0.00, 'Added via transaction form', 1, ?, ?)
        """, (category_name, datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Added new category: {category_name}")
        return jsonify({'success': True, 'message': f'Category "{category_name}" added successfully'})
        
    except Exception as e:
        print(f"❌ Error adding category: {e}")
        return jsonify({'success': False, 'error': str(e)})

@transactions_bp.route('/api/search_similar', methods=['POST'])
def search_similar_transactions():
    """Search for similar transactions based on description"""
    
    try:
        data = request.get_json()
        search_term = data.get('description', '').strip()
        
        if len(search_term) < 3:
            return jsonify([])
        
        conn = sqlite3.connect('data/personal_finance.db')
        
        # Search for similar transactions
        similar_query = """
        SELECT description, category, sub_category, amount, account_name, owner, type
        FROM transactions 
        WHERE description LIKE ? 
        ORDER BY date DESC 
        LIMIT 5
        """
        
        similar_df = pd.read_sql_query(similar_query, conn, params=[f'%{search_term}%'])
        conn.close()
        
        # Convert to list of dictionaries
        similar_transactions = []
        for _, row in similar_df.iterrows():
            similar_transactions.append({
                'description': row['description'],
                'category': row['category'],
                'sub_category': row['sub_category'] if row['sub_category'] else '',
                'amount': float(row['amount']),
                'account_name': row['account_name'],
                'owner': row['owner'],
                'type': row['type']
            })
        
        return jsonify(similar_transactions)
        
    except Exception as e:
        print(f"❌ Error searching similar transactions: {e}")
        return jsonify([])

@transactions_bp.route('/api/get_form_data')
def get_form_data():
    """Get current form data for dropdowns"""
    
    try:
        conn = sqlite3.connect('data/personal_finance.db')
        
        # Get all current options
        categories_df = pd.read_sql_query("""
            SELECT DISTINCT category FROM budget_templates 
            WHERE is_active = 1 AND category IS NOT NULL 
            UNION
            SELECT DISTINCT category FROM transactions 
            WHERE category IS NOT NULL
            ORDER BY category
        """, conn)
        
        sub_categories_df = pd.read_sql_query("""
            SELECT DISTINCT sub_category FROM transactions 
            WHERE sub_category IS NOT NULL AND sub_category != '' 
            ORDER BY sub_category
        """, conn)
        
        accounts_df = pd.read_sql_query("""
            SELECT DISTINCT account_name FROM transactions 
            WHERE account_name IS NOT NULL 
            ORDER BY account_name
        """, conn)
        
        owners_df = pd.read_sql_query("""
            SELECT DISTINCT owner FROM transactions 
            WHERE owner IS NOT NULL 
            ORDER BY owner
        """, conn)
        
        conn.close()
        
        # Prepare response
        form_data = {
            'categories': categories_df['category'].tolist(),
            'sub_categories': sub_categories_df['sub_category'].tolist(),
            'accounts': accounts_df['account_name'].tolist(),
            'owners': owners_df['owner'].tolist()
        }
        
        # Add defaults if empty
        if not form_data['accounts']:
            form_data['accounts'] = ['Venture', 'Cacas', 'Cata']
        
        if not form_data['owners']:
            form_data['owners'] = ['Cata', 'Suricata', 'Cacas']
        
        return jsonify(form_data)
        
    except Exception as e:
        print(f"❌ Error getting form data: {e}")
        return jsonify({
            'categories': [],
            'sub_categories': [],
            'accounts': ['Venture', 'Cacas', 'Cata'],
            'owners': ['Cata', 'Suricata', 'Cacas']
        })

@transactions_bp.route('/api/transactions/common_patterns')
def api_common_transaction_patterns():
    """Return the most common transaction patterns for Quick Actions (unique by category, sub_category, type)"""
    import sqlite3
    import pandas as pd
    import traceback
    print('🔍 /api/transactions/common_patterns called')
    try:
        conn = sqlite3.connect('data/personal_finance.db')
        query = '''
            SELECT category, sub_category, type, COUNT(*) as freq
            FROM transactions
            WHERE category IS NOT NULL AND category != ''
              AND date >= date('now', '-90 days')
            GROUP BY category, sub_category, type
            ORDER BY freq DESC
            LIMIT 10
        '''
        df = pd.read_sql_query(query, conn)
        conn.close()
        patterns = df.to_dict(orient='records')
        print(f'🔍 Patterns found: {patterns}')
        return jsonify(patterns)
    except Exception as e:
        print(f"❌ Error in common transaction patterns API: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500