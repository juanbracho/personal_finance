# Kanso — Personal Finance Dashboard

A local personal finance web app built with Flask. Track transactions, budgets, and debts from your browser — no accounts, no cloud, no internet required.

![Dashboard](https://img.shields.io/badge/Python-3.10%2B-blue) ![Flask](https://img.shields.io/badge/Flask-3.0-green)

---

## Features

- **Dashboard** — monthly spending overview broken down by category
- **Transactions** — log and filter expenses/income with bulk import support
- **Budgets** — set monthly budgets per category and track progress
- **Debts** — track debt accounts and payoff progress
- **Analytics** — spending trends and category breakdowns over time
- **Settings** — backup and restore your database

All data is stored locally in a SQLite database — nothing leaves your machine.

---

## Requirements

- Python 3.10+
- pip

---

## Setup

**1. Clone the repo**

```bash
git clone https://github.com/juanbracho/FinanceDashboard.git
cd FinanceDashboard/Desktop
```

**2. Create a virtual environment and install dependencies**

```bash
python -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

**3. Run the app**

```bash
python app.py
```

Open your browser and go to `http://127.0.0.1:5000`.

No login required — the app runs in local mode with no authentication.

---

## Desktop App Mode (optional)

If you want a native desktop window instead of a browser tab, install `pywebview` and run the launcher:

```bash
pip install pywebview
python desktop_app_launcher.py
```

This opens the dashboard in its own window on port 5000.

---

## Database

The SQLite database is created automatically on first run at `Desktop/data/personal_finance.db`. It is excluded from this repo via `.gitignore` — your financial data stays local.

To back up your data, use the **Settings → Export Database** option in the app.

---

## Project Structure

```
Desktop/
├── app.py                    # Flask app factory
├── auth.py                   # Authentication (session + Bearer token)
├── config.py                 # Config classes (local, desktop, production)
├── models.py                 # SQLAlchemy database models
├── utils.py                  # Shared utilities and helpers
├── desktop_app_launcher.py   # Desktop app launcher (PyWebView)
├── budget_recommender.py     # Budget recommendation logic
├── blueprints/               # Modular feature blueprints
│   ├── api/                  # REST API endpoints
│   ├── dashboards/           # Dashboard views
│   ├── transactions/         # Transaction management
│   ├── budgets/              # Budget management
│   ├── debts/                # Debt tracking
│   ├── analytics/            # Analytics and charts
│   └── settings/             # Settings and backups
├── templates/                # Jinja2 HTML templates
├── static/                   # CSS and JS assets
└── requirements.txt
```
