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
        # Use raw SQL for reliability
        conn = sqlite3.connect('data/personal_finance.db')
        
        debts_query = """
        SELECT * FROM debt_accounts 
        WHERE is_active = 1 
        ORDER BY current_balance DESC
        """
        debts_df = pd.read_sql_query(debts_query, conn)
        conn.close()
        
        # Convert to objects for template
        debts = []
        for _, row in debts_df.iterrows():
            debt_obj = type('DebtAccount', (), {})()
            for col in debts_df.columns:
                setattr(debt_obj, col, row[col])
            debts.append(debt_obj)
        
        total_debt = sum(float(debt.current_balance) for debt in debts)
        total_minimum_payments = sum(float(debt.minimum_payment or 0) for debt in debts)
        
        print(f"💳 Found {len(debts)} debt accounts, total: ${total_debt}")
        
        return render_template('debts.html', 
                             debts=debts, 
                             total_debt=total_debt,
                             total_minimum_payments=total_minimum_payments)
                             
    except Exception as e:
        print(f"❌ Error in debts route: {e}")
        import traceback
        traceback.print_exc()
        
        return render_template('debts.html', 
                             debts=[], 
                             total_debt=0,
                             total_minimum_payments=0)

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
    """Process a debt payment"""
    
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
        
        conn = sqlite3.connect('data/personal_finance.db')
        cursor = conn.cursor()
        
        # Get debt account details
        cursor.execute("""
            SELECT name, current_balance, category 
            FROM debt_accounts 
            WHERE id = ? AND is_active = 1
        """, (debt_id,))
        
        debt_result = cursor.fetchone()
        if not debt_result:
            conn.close()
            return jsonify({'success': False, 'error': 'Debt account not found'}), 404
        
        debt_name, current_balance, debt_category = debt_result
        new_balance = float(current_balance) - payment_amount
        
        print(f"💳 Debt: {debt_name}, Current: ${current_balance}, Payment: ${payment_amount}, New: ${new_balance}")
        
        # Warn if overpayment (but still allow it)
        if new_balance < 0:
            print(f"⚠️ Overpayment detected. New balance would be ${new_balance}")
        
        # Create debt payment record
        cursor.execute("""
            INSERT INTO debt_payments 
            (debt_account_id, payment_amount, payment_date, balance_after_payment, payment_type, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            debt_id,
            payment_amount,
            data['date'],
            new_balance,
            'Regular',
            data.get('description', f'Payment to {debt_name}')
        ))
        
        debt_payment_id = cursor.lastrowid
        print(f"✅ Created debt payment record ID: {debt_payment_id}")
        
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
        
        # Update debt account balance
        cursor.execute("""
            UPDATE debt_accounts 
            SET current_balance = ?, updated_at = ?
            WHERE id = ?
        """, (new_balance, datetime.utcnow().isoformat(), debt_id))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Payment of ${payment_amount} applied to {debt_name}. New balance: ${new_balance}")
        
        return jsonify({
            'success': True,
            'message': f'Payment of ${payment_amount:.2f} applied successfully!',
            'new_balance': new_balance,
            'debt_payment_id': debt_payment_id
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
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field} is required'}), 400
        
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