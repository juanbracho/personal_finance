-- Phase 3: Debt-as-Account Migration
-- Add debt charges and accounts tables

-- 1. Create debt_charges table (credit purchases)
CREATE TABLE IF NOT EXISTS debt_charges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    debt_account_id INTEGER NOT NULL,
    charge_amount DECIMAL(10,2) NOT NULL,
    charge_date DATE NOT NULL,
    description TEXT NOT NULL,
    category TEXT,
    charge_type TEXT DEFAULT 'Purchase',
    is_paid BOOLEAN DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (debt_account_id) REFERENCES debt_accounts(id)
);

-- 2. Create accounts table (for transaction form dropdown)
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    account_type TEXT NOT NULL,
    is_debt BOOLEAN DEFAULT 0,
    debt_account_id INTEGER,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (debt_account_id) REFERENCES debt_accounts(id)
);

-- 3. Update debt_payments to link to specific charge
ALTER TABLE debt_payments ADD COLUMN debt_charge_id INTEGER;

-- 4. Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_debt_charges_account ON debt_charges(debt_account_id);
CREATE INDEX IF NOT EXISTS idx_debt_charges_paid ON debt_charges(is_paid);
CREATE INDEX IF NOT EXISTS idx_accounts_type ON accounts(account_type);
CREATE INDEX IF NOT EXISTS idx_accounts_debt ON accounts(is_debt);
