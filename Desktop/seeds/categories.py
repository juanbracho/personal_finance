"""
Universal category seeds applied to every new user account on creation.
Juan's account skips these — his categories migrate from existing SQLite data.
"""

CATEGORY_SEEDS = [
    {'category': 'Living Expenses',   'sub_category': None, 'budget_amount': 0},
    {'category': 'Dining Out',         'sub_category': None, 'budget_amount': 0},
    {'category': 'Groceries',          'sub_category': None, 'budget_amount': 0},
    {'category': 'Transport',          'sub_category': None, 'budget_amount': 0},
    {'category': 'Entertainment',      'sub_category': None, 'budget_amount': 0},
    {'category': 'Shopping',           'sub_category': None, 'budget_amount': 0},
    {'category': 'Bills & Utilities',  'sub_category': None, 'budget_amount': 0},
    {'category': 'Medical',            'sub_category': None, 'budget_amount': 0},
    {'category': 'Home',               'sub_category': None, 'budget_amount': 0},
    {'category': 'Subscriptions',      'sub_category': None, 'budget_amount': 0},
    {'category': 'Debt',               'sub_category': None, 'budget_amount': 0},
    {'category': 'Savings',            'sub_category': None, 'budget_amount': 0},
    {'category': 'Miscellaneous',      'sub_category': None, 'budget_amount': 0},
]
