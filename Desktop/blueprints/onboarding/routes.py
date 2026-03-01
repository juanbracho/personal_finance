from flask import Blueprint, render_template, request, flash, redirect, url_for
from models import db, User, UserOwner
from sqlalchemy import text
from auth import _auth_disabled, _log_audit
from utils import current_user_id
from seeds.categories import CATEGORY_SEEDS

onboarding_bp = Blueprint('onboarding', __name__, url_prefix='/onboarding')


def _get_current_user():
    uid = current_user_id()
    if uid is None:
        return None
    return db.session.get(User, uid)


@onboarding_bp.route('', methods=['GET'])
def onboarding():
    if _auth_disabled():
        return redirect(url_for('dashboards.dashboard'))

    uid = current_user_id()
    if uid is None:
        return redirect(url_for('auth.login'))

    user = db.session.get(User, uid)
    if user is None or user.onboarded:
        return redirect(url_for('dashboards.dashboard'))

    return render_template('onboarding.html', user=user, category_seeds=CATEGORY_SEEDS)


@onboarding_bp.route('/complete', methods=['POST'])
def onboarding_complete():
    if _auth_disabled():
        return redirect(url_for('dashboards.dashboard'))

    uid = current_user_id()
    if uid is None:
        return redirect(url_for('auth.login'))

    user = db.session.get(User, uid)
    if user is None or user.onboarded:
        return redirect(url_for('dashboards.dashboard'))

    owner_name = request.form.get('owner_name', '').strip() or user.username

    with db.engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO user_owners (user_id, name, is_active)
            VALUES (:uid, :name, TRUE)
            ON CONFLICT (user_id, name) DO NOTHING
        """), {'uid': uid, 'name': owner_name})

        for seed in CATEGORY_SEEDS:
            conn.execute(text("""
                INSERT INTO budget_templates (user_id, category, budget_amount)
                VALUES (:uid, :category, :amount)
                ON CONFLICT (category, user_id) DO NOTHING
            """), {'uid': uid, 'category': seed['category'], 'amount': seed['budget_amount']})

        conn.execute(text("""
            UPDATE users SET onboarded = TRUE WHERE id = :uid
        """), {'uid': uid})

    _log_audit('onboarding_complete', user_id=uid, extra={'owner_name': owner_name})
    flash("You're all set!", 'success')
    return redirect(url_for('dashboards.dashboard'))
