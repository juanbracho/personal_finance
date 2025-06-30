from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# Database Models (matching your actual schema)
class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    account_name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    sub_category = db.Column(db.String(100))
    category = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20), nullable=False)
    owner = db.Column(db.String(50), nullable=False)
    is_business = db.Column(db.Boolean, default=False)
    debt_payment_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

class BudgetTemplate(db.Model):
    __tablename__ = 'budget_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False, unique=True)
    budget_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

class MonthlyBudget(db.Model):
    __tablename__ = 'monthly_budgets'
    
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    budget_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('category', 'month', 'year'),)

class UnexpectedExpense(db.Model):
    """Model for tracking unexpected expenses per month/year"""
    __tablename__ = 'unexpected_expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('category', 'month', 'year', 'description'),
        db.CheckConstraint('month >= 1 AND month <= 12')
    )

class DebtAccount(db.Model):
    __tablename__ = 'debt_accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    debt_type = db.Column(db.String(50), nullable=False)
    original_balance = db.Column(db.Numeric(10, 2), nullable=False)
    current_balance = db.Column(db.Numeric(10, 2), nullable=False)
    interest_rate = db.Column(db.Numeric(5, 4))
    minimum_payment = db.Column(db.Numeric(10, 2))
    due_date = db.Column(db.Integer)
    owner = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    account_number_last4 = db.Column(db.String(4))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

class DebtPayment(db.Model):
    __tablename__ = 'debt_payments'
    
    id = db.Column(db.Integer, primary_key=True)
    debt_account_id = db.Column(db.Integer, nullable=False)
    payment_amount = db.Column(db.Numeric(10, 2), nullable=False)
    principal_amount = db.Column(db.Numeric(10, 2))
    interest_amount = db.Column(db.Numeric(10, 2))
    payment_date = db.Column(db.Date, nullable=False)
    balance_after_payment = db.Column(db.Numeric(10, 2), nullable=False)
    payment_type = db.Column(db.String(20), default='Regular')
    notes = db.Column(db.Text)