from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
import pandas as pd
import sqlite3

# Create the blueprint
debts_bp = Blueprint('debts', __name__, url_prefix='/debts')

@debts_bp.route('/')
def list_debts():
    """Debt accounts overview"""

    print("💳 Loading debts page...")

    try:
        # Check if user wants to see paid-off debts
        show_paid_off = request.args.get('show_paid_off', 'false').lower() == 'true'

        # Use raw SQL for reliability
        conn = sqlite3.connect('data/personal_finance.db')

        # Build query based on filter
        if show_paid_off:
            debts_query = """
            SELECT * FROM debt_accounts
            ORDER BY is_active DESC, current_balance DESC
            """
            print("💳 Loading all debts (including paid-off)...")
        else:
            debts_query = """
            SELECT * FROM debt_accounts
            WHERE is_active = 1
            ORDER BY current_balance DESC
            """
            print("💳 Loading active debts only...")

        debts_df = pd.read_sql_query(debts_query, conn)
        conn.close()
        
        # Convert to objects for template
        debts = []
        for _, row in debts_df.iterrows():
            debt_obj = type('DebtAccount', (), {})()
            for col in debts_df.columns:
                setattr(debt_obj, col, row[col])
            debts.append(debt_obj)
        
        # Calculate totals only for active debts
        active_debts = [debt for debt in debts if debt.is_active == 1]
        total_debt = sum(float(debt.current_balance) for debt in active_debts)
        total_minimum_payments = sum(float(debt.minimum_payment or 0) for debt in active_debts)

        print(f"💳 Found {len(debts)} debt accounts ({len(active_debts)} active), total: ${total_debt}")

        return render_template('debts.html',
                             debts=debts,
                             total_debt=total_debt,
                             total_minimum_payments=total_minimum_payments,
                             show_paid_off=show_paid_off,
                             active_count=len(active_debts))
                             
    except Exception as e:
        print(f"❌ Error in debts route: {e}")
        import traceback
        traceback.print_exc()

        return render_template('debts.html',
                             debts=[],
                             total_debt=0,
                             total_minimum_payments=0,
                             show_paid_off=False,
                             active_count=0)

@debts_bp.route('/add', methods=['GET', 'POST'])
def add_debt():
    """Add new debt account"""
    
    if request.method == 'POST':
        try:
            # Use raw SQL insert for reliability
            conn = sqlite3.connect('data/personal_finance.db')
            cursor = conn.cursor()
            
            # Convert interest rate from percentage to decimal
            interest_rate = None
            if request.form.get('interest_rate'):
                interest_rate = float(request.form['interest_rate']) / 100
            
            cursor.execute("""
                INSERT INTO debt_accounts 
                (name, debt_type, original_balance, current_balance, interest_rate, 
                 minimum_payment, due_date, owner, category, account_number_last4, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                request.form['name'],
                request.form['debt_type'],
                float(request.form['original_balance']),
                float(request.form['current_balance']),
                interest_rate,
                float(request.form.get('minimum_payment', 0)) if request.form.get('minimum_payment') else None,
                int(request.form.get('due_date')) if request.form.get('due_date') else None,
                request.form['owner'],
                request.form['category'],
                request.form.get('account_number_last4')
            ))
            
            conn.commit()
            conn.close()
            
            print(f"✅ Added debt account: {request.form['name']}")
            flash('Debt account added successfully!', 'success')
            return redirect(url_for('debts.list_debts'))
            
        except Exception as e:
            print(f"❌ Error adding debt: {e}")
            import traceback
            traceback.print_exc()
            flash(f'Error adding debt account: {str(e)}', 'error')
    
    return render_template('add_debt.html')

@debts_bp.route('/api/make_payment/<int:debt_id>', methods=['POST'])
def make_payment(debt_id):
    """Process a debt payment (optionally linked to a specific charge)"""

    try:
        data = request.get_json()
        print(f"💰 Processing payment for debt ID {debt_id}")
        print(f"📝 Received data: {data}")

        # Validate required fields
        required_fields = ['date', 'amount', 'description', 'account_name', 'owner', 'type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field} is required'}), 400

        # Validate amount
        payment_amount = float(data['amount'])
        if payment_amount <= 0:
            return jsonify({'success': False, 'error': 'Payment amount must be greater than zero'}), 400

        # Get optional debt_charge_id (NEW)
        debt_charge_id = data.get('debt_charge_id')

        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()

        # Get debt account details (don't filter by is_active to allow payments on paid-off debts)
        cursor.execute("""
            SELECT name, current_balance, category, is_active
            FROM debt_accounts
            WHERE id = ?
        """, (debt_id,))

        debt_result = cursor.fetchone()
        if not debt_result:
            conn.close()
            return jsonify({'success': False, 'error': 'Debt account not found'}), 404

        debt_name, current_balance, debt_category, current_is_active = debt_result
        new_balance = float(current_balance) - payment_amount

        print(f"💳 Debt: {debt_name}, Current: ${current_balance}, Payment: ${payment_amount}, New: ${new_balance}")

        # Check if this payment will pay off the debt
        was_active = current_is_active == 1
        will_be_paid_off = new_balance <= 0

        # Warn if overpayment (but still allow it)
        if new_balance < 0:
            print(f"⚠️ Overpayment detected. New balance would be ${new_balance}")
        
        # If debt_charge_id provided, mark the charge as paid first
        if debt_charge_id:
            # Verify charge exists and is unpaid
            cursor.execute("""
                SELECT charge_amount, description
                FROM debt_charges
                WHERE id = ? AND debt_account_id = ? AND is_paid = 0
            """, (debt_charge_id, debt_id))

            charge_result = cursor.fetchone()
            if not charge_result:
                conn.close()
                return jsonify({'success': False, 'error': 'Charge not found or already paid'}), 404

            charge_amount, charge_description = charge_result
            print(f"💳 Paying charge ID {debt_charge_id}: {charge_description} - ${charge_amount}")

            # Mark charge as paid
            cursor.execute("""
                UPDATE debt_charges
                SET is_paid = 1
                WHERE id = ?
            """, (debt_charge_id,))
            print(f"✅ Marked charge ID {debt_charge_id} as paid")

        # Create debt payment record (now with debt_charge_id)
        cursor.execute("""
            INSERT INTO debt_payments
            (debt_account_id, debt_charge_id, payment_amount, payment_date, balance_after_payment, payment_type, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            debt_id,
            debt_charge_id,  # Links to specific charge (or NULL if general payment)
            payment_amount,
            data['date'],
            new_balance,
            'Regular',
            data.get('description', f'Payment to {debt_name}')
        ))

        debt_payment_id = cursor.lastrowid
        print(f"✅ Created debt payment record ID: {debt_payment_id}" +
              (f" (linked to charge {debt_charge_id})" if debt_charge_id else " (general payment)"))
        
        # Create transaction record (positive amount for expense)
        # First check if is_active column exists
        cursor.execute("PRAGMA table_info(transactions)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'is_active' in columns:
            cursor.execute("""
                INSERT INTO transactions 
                (account_name, date, description, amount, sub_category, category, type, owner, 
                 is_business, debt_payment_id, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """, (
                data['account_name'],
                data['date'],
                data['description'],
                payment_amount,  # Positive for expense
                debt_name,  # Sub-category matches debt account name
                'Debt',  # Category is always 'Debt'
                data['type'],
                data['owner'],
                data.get('is_business', False),
                debt_payment_id,
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ))
        else:
            cursor.execute("""
                INSERT INTO transactions 
                (account_name, date, description, amount, sub_category, category, type, owner, 
                 is_business, debt_payment_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data['account_name'],
                data['date'],
                data['description'],
                payment_amount,  # Positive for expense
                debt_name,  # Sub-category matches debt account name
                'Debt',  # Category is always 'Debt'
                data['type'],
                data['owner'],
                data.get('is_business', False),
                debt_payment_id,
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ))
        
        transaction_id = cursor.lastrowid
        print(f"✅ Created transaction record ID: {transaction_id}")

        # Update debt account balance and status
        # Auto-close if paid off (balance <= 0), reopen if adding to paid-off debt
        new_is_active = 1 if new_balance > 0 else 0

        cursor.execute("""
            UPDATE debt_accounts
            SET current_balance = ?, is_active = ?, updated_at = ?
            WHERE id = ?
        """, (new_balance, new_is_active, datetime.utcnow().isoformat(), debt_id))

        conn.commit()
        conn.close()

        # Create success message based on status change
        if will_be_paid_off and was_active:
            success_message = f'🎉 Congratulations! Payment of ${payment_amount:.2f} applied - Debt is now PAID OFF!'
            print(f"✅ Payment of ${payment_amount} applied to {debt_name}. DEBT PAID OFF!")
        elif not was_active and new_balance > 0:
            success_message = f'Payment of ${payment_amount:.2f} applied - Debt account reopened.'
            print(f"✅ Payment of ${payment_amount} applied to {debt_name}. Debt reopened. New balance: ${new_balance}")
        else:
            success_message = f'Payment of ${payment_amount:.2f} applied successfully!'
            print(f"✅ Payment of ${payment_amount} applied to {debt_name}. New balance: ${new_balance}")

        return jsonify({
            'success': True,
            'message': success_message,
            'new_balance': new_balance,
            'debt_payment_id': debt_payment_id,
            'is_paid_off': new_is_active == 0
        })
        
    except Exception as e:
        print(f"❌ Error processing payment: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    
@debts_bp.route('/api/get_debt/<int:debt_id>')
def get_debt(debt_id):
    """Get debt account details for editing"""
    
    try:
        print(f"📄 Getting debt account ID {debt_id}")
        
        conn = sqlite3.connect('data/personal_finance.db')
        
        debt_query = """
        SELECT * FROM debt_accounts 
        WHERE id = ? AND is_active = 1
        """
        debt_df = pd.read_sql_query(debt_query, conn, params=[debt_id])
        conn.close()
        
        if debt_df.empty:
            return jsonify({'success': False, 'error': 'Debt account not found'}), 404
        
        # Convert to dictionary
        debt = debt_df.iloc[0].to_dict()
        
        # Handle None values and format properly
        debt['account_number_last4'] = debt['account_number_last4'] if debt['account_number_last4'] else ''
        debt['minimum_payment'] = float(debt['minimum_payment']) if debt['minimum_payment'] else None
        debt['interest_rate'] = float(debt['interest_rate']) if debt['interest_rate'] else None
        debt['due_date'] = int(debt['due_date']) if debt['due_date'] else None
        debt['original_balance'] = float(debt['original_balance'])
        debt['current_balance'] = float(debt['current_balance'])
        
        print(f"📄 Returning debt account: {debt['name']}")
        return jsonify({'success': True, 'debt': debt})
        
    except Exception as e:
        print(f"❌ Error getting debt account: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@debts_bp.route('/api/update_debt/<int:debt_id>', methods=['PUT'])
def update_debt(debt_id):
    """Update debt account details"""

    try:
        data = request.get_json()
        print(f"✏️ Updating debt account ID {debt_id}")
        print(f"📝 Update data: {data}")

        # Validate required fields
        required_fields = ['name', 'debt_type', 'owner', 'original_balance', 'current_balance', 'category']
        for field in required_fields:
            value = data.get(field)
            # Check for None or empty string, but allow 0 for numeric fields
            if value is None or (isinstance(value, str) and value.strip() == ''):
                print(f"❌ Validation failed: '{field}' is missing or empty (value: {value})")
                return jsonify({'success': False, 'error': f'{field} is required'}), 400

        print("✅ All required fields validated successfully")

        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()

        # Check if debt exists
        cursor.execute("SELECT id FROM debt_accounts WHERE id = ? AND is_active = 1", (debt_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'Debt account not found'}), 404

        # Update debt account
        cursor.execute("""
            UPDATE debt_accounts
            SET name = ?, debt_type = ?, owner = ?, account_number_last4 = ?,
                original_balance = ?, current_balance = ?, interest_rate = ?,
                minimum_payment = ?, due_date = ?, category = ?, updated_at = ?
            WHERE id = ?
        """, (
            data['name'],
            data['debt_type'],
            data['owner'],
            data.get('account_number_last4'),
            float(data['original_balance']),
            float(data['current_balance']),
            float(data['interest_rate']) if data.get('interest_rate') is not None else None,
            float(data['minimum_payment']) if data.get('minimum_payment') is not None else None,
            int(data['due_date']) if data.get('due_date') is not None else None,
            data['category'],
            datetime.utcnow().isoformat(),
            debt_id
        ))

        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'success': False, 'error': 'No changes made'}), 404

        conn.commit()
        conn.close()

        print(f"✅ Updated debt account: {data['name']}")
        return jsonify({
            'success': True,
            'message': f'Debt account "{data["name"]}" updated successfully!'
        })

    except Exception as e:
        print(f"❌ Error updating debt account: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@debts_bp.route('/api/payment_history/<int:debt_id>')
def get_payment_history(debt_id):
    """Get payment history AND charges for a debt account"""

    try:
        print(f"📊 Getting payment history + charges for debt ID {debt_id}")

        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()

        # Get debt account details
        cursor.execute("""
            SELECT name, original_balance, current_balance
            FROM debt_accounts
            WHERE id = ?
        """, (debt_id,))

        debt_result = cursor.fetchone()
        if not debt_result:
            conn.close()
            return jsonify({'success': False, 'error': 'Debt account not found'}), 404

        debt_name, original_balance, current_balance = debt_result

        # Get payment history
        payments_query = """
        SELECT
            id,
            debt_charge_id,
            payment_amount,
            principal_amount,
            interest_amount,
            payment_date,
            balance_after_payment,
            payment_type,
            notes
        FROM debt_payments
        WHERE debt_account_id = ?
        ORDER BY payment_date DESC, id DESC
        """

        payments_df = pd.read_sql_query(payments_query, conn, params=[debt_id])

        # Get charges history
        charges_query = """
        SELECT
            id,
            charge_amount,
            charge_date,
            description,
            category,
            charge_type,
            is_paid,
            notes
        FROM debt_charges
        WHERE debt_account_id = ?
        ORDER BY charge_date DESC, id DESC
        """

        charges_df = pd.read_sql_query(charges_query, conn, params=[debt_id])
        conn.close()

        # Convert payments to list of dictionaries
        payments = []
        total_paid = 0

        for _, row in payments_df.iterrows():
            payment = {
                'id': int(row['id']),
                'debt_charge_id': int(row['debt_charge_id']) if pd.notna(row['debt_charge_id']) else None,
                'payment_amount': float(row['payment_amount']),
                'principal_amount': float(row['principal_amount']) if pd.notna(row['principal_amount']) else None,
                'interest_amount': float(row['interest_amount']) if pd.notna(row['interest_amount']) else None,
                'payment_date': row['payment_date'],
                'balance_after_payment': float(row['balance_after_payment']),
                'payment_type': row['payment_type'] if pd.notna(row['payment_type']) else 'Regular',
                'notes': row['notes'] if pd.notna(row['notes']) else ''
            }
            payments.append(payment)
            total_paid += float(row['payment_amount'])

        # Convert charges to list of dictionaries
        charges = []
        total_charges = 0
        unpaid_charges = 0

        for _, row in charges_df.iterrows():
            charge = {
                'id': int(row['id']),
                'charge_amount': float(row['charge_amount']),
                'charge_date': row['charge_date'],
                'description': row['description'],
                'category': row['category'] if pd.notna(row['category']) else '',
                'charge_type': row['charge_type'] if pd.notna(row['charge_type']) else 'Purchase',
                'is_paid': bool(row['is_paid']),
                'notes': row['notes'] if pd.notna(row['notes']) else ''
            }
            charges.append(charge)
            total_charges += float(row['charge_amount'])
            if not row['is_paid']:
                unpaid_charges += 1

        # Calculate summary statistics
        payment_count = len(payments)
        avg_payment = total_paid / payment_count if payment_count > 0 else 0

        print(f"📊 Found {payment_count} payments totaling ${total_paid:.2f}")
        print(f"📊 Found {len(charges)} charges totaling ${total_charges:.2f} ({unpaid_charges} unpaid)")

        return jsonify({
            'success': True,
            'debt_name': debt_name,
            'original_balance': float(original_balance),
            'current_balance': float(current_balance),
            'total_paid': round(total_paid, 2),
            'total_charges': round(total_charges, 2),
            'payment_count': payment_count,
            'charge_count': len(charges),
            'unpaid_charge_count': unpaid_charges,
            'avg_payment': round(avg_payment, 2),
            'payments': payments,
            'charges': charges
        })

    except Exception as e:
        print(f"❌ Error getting payment history: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@debts_bp.route('/api/unpaid_charges/<int:debt_id>')
def get_unpaid_charges(debt_id):
    """Get all unpaid charges for a debt account"""

    try:
        print(f"💳 Getting unpaid charges for debt ID {debt_id}")

        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()

        # Get unpaid charges
        charges_query = """
        SELECT
            id,
            charge_amount,
            charge_date,
            description,
            category,
            charge_type
        FROM debt_charges
        WHERE debt_account_id = ? AND is_paid = 0
        ORDER BY charge_date ASC, id ASC
        """

        charges_df = pd.read_sql_query(charges_query, conn, params=[debt_id])
        conn.close()

        # Convert to list of dictionaries
        charges = []
        for _, row in charges_df.iterrows():
            charge = {
                'id': int(row['id']),
                'charge_amount': float(row['charge_amount']),
                'charge_date': row['charge_date'],
                'description': row['description'],
                'category': row['category'] if pd.notna(row['category']) else '',
                'charge_type': row['charge_type'] if pd.notna(row['charge_type']) else 'Purchase'
            }
            charges.append(charge)

        print(f"💳 Found {len(charges)} unpaid charges")

        return jsonify({
            'success': True,
            'charges': charges,
            'count': len(charges)
        })

    except Exception as e:
        print(f"❌ Error getting unpaid charges: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@debts_bp.route('/api/delete_debt/<int:debt_id>', methods=['DELETE'])
def delete_debt(debt_id):
    """Delete a debt account and all associated records"""

    try:
        print(f"🗑️ Deleting debt account ID {debt_id}")

        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()

        # Check if debt exists and get name
        cursor.execute("""
            SELECT name FROM debt_accounts WHERE id = ?
        """, (debt_id,))

        debt_result = cursor.fetchone()
        if not debt_result:
            conn.close()
            return jsonify({'success': False, 'error': 'Debt account not found'}), 404

        debt_name = debt_result[0]

        # Update transactions to remove debt_payment_id reference (keep the transactions)
        cursor.execute("""
            UPDATE transactions
            SET debt_payment_id = NULL
            WHERE debt_payment_id IN (
                SELECT id FROM debt_payments WHERE debt_account_id = ?
            )
        """, (debt_id,))
        updated_transactions = cursor.rowcount
        print(f"📝 Updated {updated_transactions} transactions (removed debt payment link)")

        # Delete debt payments
        cursor.execute("""
            DELETE FROM debt_payments WHERE debt_account_id = ?
        """, (debt_id,))
        deleted_payments = cursor.rowcount
        print(f"🗑️ Deleted {deleted_payments} debt payment records")

        # Delete the debt account itself
        cursor.execute("""
            DELETE FROM debt_accounts WHERE id = ?
        """, (debt_id,))

        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'success': False, 'error': 'Failed to delete debt account'}), 500

        conn.commit()
        conn.close()

        print(f"✅ Deleted debt account: {debt_name}")
        return jsonify({
            'success': True,
            'message': f'Debt account "{debt_name}" deleted successfully! ({updated_transactions} transactions preserved)'
        })

    except Exception as e:
        print(f"❌ Error deleting debt account: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500