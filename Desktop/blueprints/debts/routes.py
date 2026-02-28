from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
import pandas as pd
from models import db
from sqlalchemy import text
from utils import uid_clause, current_user_id

debts_bp = Blueprint('debts', __name__, url_prefix='/debts')


def _df(conn, sql, params=None):
    return pd.read_sql_query(text(sql), conn, params=params or {})


@debts_bp.route('/')
def list_debts():
    """Debt accounts overview"""
    print("💳 Loading debts page...")
    try:
        show_paid_off = request.args.get('show_paid_off', 'false').lower() == 'true'
        uid_sql, uid_p = uid_clause()
        with db.engine.connect() as conn:
            if show_paid_off:
                debts_df = _df(conn, f"""
                    SELECT * FROM debt_accounts WHERE 1=1 {uid_sql}
                    ORDER BY is_active DESC, current_balance DESC
                """, uid_p)
                print("💳 Loading all debts (including paid-off)...")
            else:
                debts_df = _df(conn, f"""
                    SELECT * FROM debt_accounts WHERE is_active = true {uid_sql}
                    ORDER BY current_balance DESC
                """, uid_p)
                print("💳 Loading active debts only...")

        debts = []
        for _, row in debts_df.iterrows():
            debt_obj = type('DebtAccount', (), {})()
            for col in debts_df.columns:
                setattr(debt_obj, col, row[col])
            debts.append(debt_obj)

        active_debts = [debt for debt in debts if debt.is_active]
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
        return render_template('debts.html', debts=[], total_debt=0,
                             total_minimum_payments=0, show_paid_off=False, active_count=0)


@debts_bp.route('/add', methods=['GET', 'POST'])
def add_debt():
    """Add new debt account"""
    if request.method == 'POST':
        try:
            interest_rate = None
            if request.form.get('interest_rate'):
                interest_rate = float(request.form['interest_rate']) / 100

            with db.engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO debt_accounts
                    (name, debt_type, original_balance, current_balance, interest_rate,
                     minimum_payment, due_date, owner, category, account_number_last4, is_active, user_id)
                    VALUES (:name, :debt_type, :original_balance, :current_balance, :interest_rate,
                            :minimum_payment, :due_date, :owner, :category, :account_number_last4, true, :uid)
                """), {
                    'name': request.form['name'],
                    'debt_type': request.form['debt_type'],
                    'original_balance': float(request.form['original_balance']),
                    'current_balance': float(request.form['current_balance']),
                    'interest_rate': interest_rate,
                    'minimum_payment': float(request.form['minimum_payment']) if request.form.get('minimum_payment') else None,
                    'due_date': int(request.form['due_date']) if request.form.get('due_date') else None,
                    'owner': request.form['owner'],
                    'category': request.form['category'],
                    'account_number_last4': request.form.get('account_number_last4'),
                    'uid': current_user_id(),
                })

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

        required_fields = ['date', 'amount', 'description', 'account_name', 'owner', 'type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field} is required'}), 400

        payment_amount = float(data['amount'])
        if payment_amount <= 0:
            return jsonify({'success': False, 'error': 'Payment amount must be greater than zero'}), 400

        debt_charge_id = data.get('debt_charge_id')

        uid = current_user_id()
        uid_sql, uid_p = uid_clause(uid)
        with db.engine.begin() as conn:
            debt_row = conn.execute(text(f"""
                SELECT name, current_balance, category, is_active
                FROM debt_accounts WHERE id = :id {uid_sql}
            """), {'id': debt_id, **uid_p}).fetchone()

            if not debt_row:
                return jsonify({'success': False, 'error': 'Debt account not found'}), 404

            debt_name, current_balance, debt_category, current_is_active = debt_row
            new_balance = float(current_balance) - payment_amount
            was_active = bool(current_is_active)
            will_be_paid_off = new_balance <= 0

            print(f"💳 Debt: {debt_name}, Current: ${current_balance}, Payment: ${payment_amount}, New: ${new_balance}")

            if new_balance < 0:
                print(f"⚠️ Overpayment detected. New balance would be ${new_balance}")

            if debt_charge_id:
                charge_row = conn.execute(text("""
                    SELECT charge_amount, description FROM debt_charges
                    WHERE id = :charge_id AND debt_account_id = :debt_id AND is_paid = false
                """), {'charge_id': debt_charge_id, 'debt_id': debt_id}).fetchone()

                if not charge_row:
                    return jsonify({'success': False, 'error': 'Charge not found or already paid'}), 404

                charge_amount, charge_description = charge_row
                print(f"💳 Paying charge ID {debt_charge_id}: {charge_description} - ${charge_amount}")

                conn.execute(text("UPDATE debt_charges SET is_paid = true WHERE id = :id"),
                             {'id': debt_charge_id})
                print(f"✅ Marked charge ID {debt_charge_id} as paid")

            dp_result = conn.execute(text("""
                INSERT INTO debt_payments
                (debt_account_id, debt_charge_id, payment_amount, payment_date,
                 balance_after_payment, payment_type, notes, user_id)
                VALUES (:debt_id, :charge_id, :amount, :date, :balance, :ptype, :notes, :uid)
                RETURNING id
            """), {
                'debt_id': debt_id,
                'charge_id': debt_charge_id,
                'amount': payment_amount,
                'date': data['date'],
                'balance': new_balance,
                'ptype': 'Regular',
                'notes': data.get('description', f'Payment to {debt_name}'),
                'uid': uid,
            })
            debt_payment_id = dp_result.fetchone()[0]
            print(f"✅ Created debt payment record ID: {debt_payment_id}" +
                  (f" (linked to charge {debt_charge_id})" if debt_charge_id else " (general payment)"))

            t_result = conn.execute(text("""
                INSERT INTO transactions
                (account_name, date, description, amount, sub_category, category,
                 type, owner, is_business, debt_payment_id, is_active, user_id, created_at, updated_at)
                VALUES (:account_name, :date, :description, :amount, :sub_category, :category,
                        :type, :owner, :is_business, :debt_payment_id, true, :uid, :now, :now)
                RETURNING id
            """), {
                'account_name': data['account_name'],
                'date': data['date'],
                'description': data['description'],
                'amount': payment_amount,
                'sub_category': debt_name,
                'category': 'Debt',
                'type': data['type'],
                'owner': data['owner'],
                'is_business': data.get('is_business', False),
                'debt_payment_id': debt_payment_id,
                'uid': uid,
                'now': datetime.utcnow(),
            })
            transaction_id = t_result.fetchone()[0]
            print(f"✅ Created transaction record ID: {transaction_id}")

            new_is_active = new_balance > 0
            conn.execute(text("""
                UPDATE debt_accounts
                SET current_balance = :balance, is_active = :active, updated_at = :now
                WHERE id = :id
            """), {'balance': new_balance, 'active': new_is_active, 'now': datetime.utcnow(), 'id': debt_id})

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
            'is_paid_off': not new_is_active
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
        uid_sql, uid_p = uid_clause()
        with db.engine.connect() as conn:
            df = _df(conn, f"SELECT * FROM debt_accounts WHERE id = :id AND is_active = true {uid_sql}",
                     {'id': debt_id, **uid_p})

        if df.empty:
            return jsonify({'success': False, 'error': 'Debt account not found'}), 404

        debt = df.iloc[0].to_dict()
        debt['account_number_last4'] = debt.get('account_number_last4') or ''
        debt['minimum_payment'] = float(debt['minimum_payment']) if debt.get('minimum_payment') is not None else None
        debt['interest_rate'] = float(debt['interest_rate']) if debt.get('interest_rate') is not None else None
        debt['due_date'] = int(debt['due_date']) if debt.get('due_date') is not None else None
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

        required_fields = ['name', 'debt_type', 'owner', 'original_balance', 'current_balance', 'category']
        for field in required_fields:
            value = data.get(field)
            if value is None or (isinstance(value, str) and value.strip() == ''):
                print(f"❌ Validation failed: '{field}' is missing or empty")
                return jsonify({'success': False, 'error': f'{field} is required'}), 400

        print("✅ All required fields validated successfully")

        uid_sql, uid_p = uid_clause()
        with db.engine.begin() as conn:
            exists = conn.execute(text(
                f"SELECT id FROM debt_accounts WHERE id = :id AND is_active = true {uid_sql}"
            ), {'id': debt_id, **uid_p}).fetchone()
            if not exists:
                return jsonify({'success': False, 'error': 'Debt account not found'}), 404

            upd = conn.execute(text(f"""
                UPDATE debt_accounts
                SET name = :name, debt_type = :debt_type, owner = :owner,
                    account_number_last4 = :account_number_last4,
                    original_balance = :original_balance, current_balance = :current_balance,
                    interest_rate = :interest_rate, minimum_payment = :minimum_payment,
                    due_date = :due_date, category = :category, updated_at = :now
                WHERE id = :id {uid_sql}
            """), {
                'name': data['name'],
                'debt_type': data['debt_type'],
                'owner': data['owner'],
                'account_number_last4': data.get('account_number_last4'),
                'original_balance': float(data['original_balance']),
                'current_balance': float(data['current_balance']),
                'interest_rate': float(data['interest_rate']) if data.get('interest_rate') is not None else None,
                'minimum_payment': float(data['minimum_payment']) if data.get('minimum_payment') is not None else None,
                'due_date': int(data['due_date']) if data.get('due_date') is not None else None,
                'category': data['category'],
                'now': datetime.utcnow(),
                'id': debt_id,
                **uid_p,
            })
            if upd.rowcount == 0:
                return jsonify({'success': False, 'error': 'No changes made'}), 404

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

        uid_sql, uid_p = uid_clause()
        with db.engine.connect() as conn:
            debt_row = conn.execute(text(f"""
                SELECT name, original_balance, current_balance
                FROM debt_accounts WHERE id = :id {uid_sql}
            """), {'id': debt_id, **uid_p}).fetchone()

            if not debt_row:
                return jsonify({'success': False, 'error': 'Debt account not found'}), 404

            debt_name, original_balance, current_balance = debt_row

            payments_df = _df(conn, """
                SELECT id, debt_charge_id, payment_amount, principal_amount, interest_amount,
                       payment_date, balance_after_payment, payment_type, notes
                FROM debt_payments
                WHERE debt_account_id = :id
                ORDER BY payment_date DESC, id DESC
            """, {'id': debt_id})

            charges_df = _df(conn, """
                SELECT id, charge_amount, charge_date, description,
                       category, charge_type, is_paid, notes
                FROM debt_charges
                WHERE debt_account_id = :id
                ORDER BY charge_date DESC, id DESC
            """, {'id': debt_id})

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
        with db.engine.connect() as conn:
            df = _df(conn, """
                SELECT id, charge_amount, charge_date, description, category, charge_type
                FROM debt_charges
                WHERE debt_account_id = :id AND is_paid = false
                ORDER BY charge_date ASC, id ASC
            """, {'id': debt_id})

        charges = [
            {
                'id': int(row['id']),
                'charge_amount': float(row['charge_amount']),
                'charge_date': row['charge_date'],
                'description': row['description'],
                'category': row['category'] if pd.notna(row['category']) else '',
                'charge_type': row['charge_type'] if pd.notna(row['charge_type']) else 'Purchase'
            }
            for _, row in df.iterrows()
        ]
        print(f"💳 Found {len(charges)} unpaid charges")
        return jsonify({'success': True, 'charges': charges, 'count': len(charges)})
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

        uid_sql, uid_p = uid_clause()
        with db.engine.begin() as conn:
            name_row = conn.execute(text(
                f"SELECT name FROM debt_accounts WHERE id = :id {uid_sql}"
            ), {'id': debt_id, **uid_p}).fetchone()

            if not name_row:
                return jsonify({'success': False, 'error': 'Debt account not found'}), 404

            debt_name = name_row[0]

            upd = conn.execute(text("""
                UPDATE transactions SET debt_payment_id = NULL
                WHERE debt_payment_id IN (
                    SELECT id FROM debt_payments WHERE debt_account_id = :id
                )
            """), {'id': debt_id})
            updated_transactions = upd.rowcount
            print(f"📝 Updated {updated_transactions} transactions (removed debt payment link)")

            del_pay = conn.execute(text(
                "DELETE FROM debt_payments WHERE debt_account_id = :id"
            ), {'id': debt_id})
            print(f"🗑️ Deleted {del_pay.rowcount} debt payment records")

            del_debt = conn.execute(text(
                f"DELETE FROM debt_accounts WHERE id = :id {uid_sql}"
            ), {'id': debt_id, **uid_p})
            if del_debt.rowcount == 0:
                return jsonify({'success': False, 'error': 'Failed to delete debt account'}), 500

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
