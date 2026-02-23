# Finance Dashboard — Project Context

## What Is This?

A personal finance management system built for Juan Bracho's household. It tracks transactions, budgets, and debts across three spending owners: **Cacas**, **Cata**, and **Suricata**.

The app runs across three surfaces that all share one SQLite database:

| Surface | Tech | Status |
|---------|------|--------|
| macOS Desktop App | Flask + PyWebView | ✅ Production |
| Web Dashboard | Flask on Railway | ✅ Production |
| Mobile App (iOS/Android) | Flutter | ✅ Connected, polish pending |

**Live URL:** `https://finance.juanbracho.com` (Railway on Cloudflare)

---

## Architecture Overview

```
Finance Dashboard/
├── Desktop/        → Flask backend (serves desktop, web, and mobile)
├── Mobile/         → Flutter app + planning docs
├── Archive/        → Legacy code backups
└── Data backup/    → Database backups
```

The `Desktop/` folder is the single source of truth for backend logic — it powers all three surfaces. The Flutter mobile app connects to the Railway cloud instance via REST API.

---

## Backend — Flask (`Desktop/`)

**Stack:** Python 3.10 · Flask 3.0 · SQLAlchemy · SQLite · Gunicorn

**Key files:**

| File | Purpose |
|------|---------|
| `app.py` | App factory, blueprint registration, CORS |
| `config.py` | Three config classes: local desktop, production (Railway) |
| `auth.py` | Dual auth: Bearer token (API) + session cookies (web UI) |
| `models.py` | SQLAlchemy ORM models |
| `utils.py` | DB utilities, validation, stats |
| `desktop_app_launcher.py` | Smart launcher — detects local vs. cloud mode |
| `Procfile` + `railway.json` | Railway deployment config |

**Blueprints (modular features):**

| Blueprint | Prefix | Purpose |
|-----------|--------|---------|
| `api` | `/api/*` | REST API for Flutter + programmatic access |
| `dashboards` | `/dashboard/` | Overview, monthly, yearly, budget views |
| `transactions` | `/transactions/` | Transaction CRUD and bulk import |
| `debts` | `/debts/` | Debt tracking and payoff planning |
| `budgets` | `/budget/` | Budget management and templates |
| `analytics` | `/analytics/` | Charts and trend analysis |
| `settings` | `/settings/` | Database backup/restore |

**Authentication:**
- **Bearer token** (`Authorization: Bearer <API_SECRET_KEY>`) — for Flutter and API clients
- **Session cookies** — for web UI (username + password, 1-hour session)
- Local desktop mode bypasses auth (empty env vars)

**Database models:** `Transaction`, `BudgetTemplate`, `BudgetSubcategoryTemplate`, `MonthlyBudget`, `UnexpectedExpense`, `DebtAccount`, `DebtPayment`, `BudgetCommitment`

**Database locations:**
- Local: `Desktop/data/personal_finance.db` (1.1 MB)
- Railway: `/app/data/personal_finance.db` (persistent volume)

---

## Mobile App — Flutter (`Mobile/finance_dashboard_mobile/`)

**Stack:** Flutter 3.10.4 · Riverpod · go_router · fl_chart · flutter_secure_storage

**Screens:**

| Screen | Status |
|--------|--------|
| Home / Overview | ✅ Connected |
| Transaction History | ✅ Connected (infinite scroll, 50/page, max 250) |
| Budgets | ✅ Connected (drill-down to subcategories) |
| Debts | ✅ Connected |
| Login | ✅ Connected (token stored in Keychain/Keystore) |
| Add Transaction | Removed from nav (read-only mode) |

**Themes:** "Warm Ink" (gold/amber), "Japanese Indigo" (periwinkle), "Washi Paper" (light)

**API config (`config.dart`):**
- Base URL: `https://finance.juanbracho.com`
- Auth: Username/password → POST `/api/login` → receives `API_SECRET_KEY` → stored in secure storage

**Color coding per transaction type:**
- Needs: `#7BAF8E` (green)
- Wants: `#D4956A` (tan)
- Business: `#6A8FBF` (blue)
- Savings: `#A67FB5` (purple)
- Unexpected: `#E8761F` (orange)

---

## Cloud Deployment — Railway

**Platform:** Railway.app Hobby plan ($5/month)
**Domain:** `finance.juanbracho.com` via Cloudflare CNAME → `4vdt6k0y.up.railway.app`
**SSL:** Automatic HTTPS (Let's Encrypt)

**Required environment variables on Railway:**

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | SQLite path on persistent volume |
| `SECRET_KEY` | Flask session signing key |
| `API_SECRET_KEY` | Bearer token for Flutter auth |
| `CORS_ORIGINS` | Allowed origins |
| `DASHBOARD_USERNAME` | Login username (web + Flutter) |
| `DASHBOARD_PASSWORD` | Login password (web + Flutter) |

---

## Current State (as of February 2026)

**Data snapshot:**
- Monthly spending: ~$10,323.57
- Active debts total: ~$93,898.37
- Owners tracked: Cacas, Cata, Suricata

**What's working:**
- All three surfaces connected to the same cloud database
- Dual authentication fully functional
- Flutter app: Overview, History (pagination), Budgets (subcategory drill-down), Debts, Login
- Period selectors (month/year) on Overview and Budget screens
- Dynamic transaction types and budget bars
- "Unexpected" expenses correctly included in web overview

**Pending work (`Desktop/IMPLEMENTATION_PLAN.md`):**
1. Export database fix — JavaScript handler to properly trigger file downloads
2. Expandable transactions in budget view — 3-level hierarchy (Category → Subcategory → Individual Transactions)
3. Flutter polish — UI refinements noted in `Mobile/post_redesign_needs.md` and `Mobile/mobile_redesign.md`

---

## Planning & Documentation Files

All planning docs live under `Mobile/`:

| File | Contents |
|------|----------|
| `expansion_plan.md` | Full architecture, phases 1–5, pricing rationale |
| `mobile_development.md` | Current status, URLs, auth setup, Railway env vars |
| `planning_discussion.md` | Foundational design decisions (cloud-first, single DB, auth strategy) |
| `post_redesign_needs.md` | Feb 22 2026 session — 9 completed tasks + remaining polish |
| `mobile_redesign.md` | Mobile UI/UX refinement notes |
| `desktop_redesign.md` | Desktop UI/UX refinement notes |

Desktop planning: `Desktop/IMPLEMENTATION_PLAN.md`

---

## Branding

App name/theme: **Kanso** (Japanese aesthetic of simplicity and elimination of clutter)
Icons: `kanso_icon.png`, `kansosvg.svg` at project root and `Mobile/AppIcons/`
