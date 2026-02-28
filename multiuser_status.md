# Multi-User Migration — Status Log
*Reference: `multiuser_migration.md` (plan) · `project_context.md` (app overview)*

---

## Current State

**Active Phase:** Phase 5 — New User Onboarding Flow
**Overall Progress:** Phase 4 complete ✅
**Last Session:** February 2026

---

## Phase Tracker

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Database Migration (SQLite → PostgreSQL on Neon, schema changes) | ✅ Complete |
| 2 | Auth Overhaul (JWT, password hashing, session update) | ✅ Complete |
| 3 | Route Scoping (user_id on all queries) | ✅ Complete |
| 4 | Admin Panel & User Management | ✅ Complete |
| 5 | New User Onboarding Flow | ⏳ Pending |
| 6 | Flutter Update (JWT + 401 handling) | ⏳ Pending |

---

## Phase 1 — Database Migration

### Steps

| # | Step | Status | Notes |
|---|------|--------|-------|
| 1 | Set up Neon free tier PostgreSQL instance | ✅ Done | |
| 2 | `models.py` — new models + `user_id` on all tables | ✅ Done | AuditLog.extra_data (metadata reserved) |
| 3 | `config.py`, `requirements.txt`, `app.py` | ✅ Done | JWT_SECRET_KEY added, SQLALCHEMY_ECHO=False |
| 4 | `utils.py`, `budget_recommender.py` — remove sqlite3 | ✅ Done | |
| 5 | All 7 blueprints — SQLite SQL → PostgreSQL SQL | ✅ Done | sqlite3 → SQLAlchemy; strftime → EXTRACT |
| 6 | `migrations/migrate_to_postgres.py` | ✅ Done | --dry-run flag; _float handles bad data |
| 7 | `seeds/categories.py` | ✅ Done | 13 universal categories |
| 8 | `DATABASE_URL` + `JWT_SECRET_KEY` on Railway & local `.env` | ✅ Done | |
| 9 | Run migration — all 8 tables verified | ✅ Done | 7152 transactions; 1 bad amount (MCT→0.0) |
| 10 | Fix Railway start command (`railway.json` → gunicorn) | ✅ Done | Was pointing at desktop_app_launcher.py |
| 11 | Smoke-test all pages on Railway | ⏳ Pending | Deploy green, verify pages load |

### Notes
- Database backup taken before starting migration ✅
- Current DB: `Desktop/data/personal_finance.db` (~1.1 MB)

---

---

## Phase 2 — Auth Overhaul

### Steps

| # | Step | Status | Notes |
|---|------|--------|-------|
| 1 | `migrations/set_initial_password.py` | ✅ Done | Loads Desktop/.env automatically; handles postgres:// URLs |
| 2 | `auth.py` full rewrite | ✅ Done | check_jwt(), check_web_session(), _issue_jwt(), _log_audit() |
| 3 | `blueprints/api/routes.py` — api_login | ✅ Done | 5/min rate limit; returns {token, user_id, role, expires_in} |
| 4 | `utils.py` — current_user_id() + scoped owners | ✅ Done | Reads user_owners when user identified |
| 5 | `app.py` — Flask-Limiter init | ✅ Done | limiter = Limiter(...); limiter.init_app(app) |
| 6 | `config.py` — secure cookies | ✅ Done | Was already in ProductionConfig from Phase 1 |
| 7 | Run set_initial_password.py on Neon | ⏳ Pending | Run before removing old env vars |
| 8 | Deploy to Railway + smoke test | ⏳ Pending | Verify login, JWT, logout, rate limit |
| 9 | Remove DASHBOARD_USERNAME/PASSWORD/API_SECRET_KEY from Railway | ⏳ Pending | After deploy confirmed working |

### Auth bypass rule
- `JWT_SECRET_KEY == 'dev-jwt-secret'` (config default) → auth skipped (local dev)
- Railway sets a real key → always enforced

### Session keys
- `session['user_id']`, `session['login_time']`, `session['role']` (1 hour)

---

## Decisions & Changes from Plan

*Record any deviations from `multiuser_migration.md` here as they happen.*

| Date | Decision | Reason |
|------|----------|--------|
| — | — | — |

---

## Blockers

*None currently.*

---

## Session Notes

### February 2026 — Session 1
- Plan finalized in `multiuser_migration.md`
- Database backup confirmed
- Starting Phase 1

### February 2026 — Sessions 2–4
All Phase 1 code complete:
- `models.py` — User, UserOwner, CategorySeed, AuditLog, RevokedToken added; user_id FK on all existing models; unique constraints updated
- `config.py` — JWT_SECRET_KEY, removed old DASHBOARD_* vars from ProductionConfig, SQLALCHEMY_ECHO=False
- `requirements.txt` — psycopg2-binary, PyJWT, Flask-Limiter added
- `app.py` — db.create_all() in factory, no SQLite init calls
- `utils.py`, `budget_recommender.py` — all sqlite3 removed, SQLAlchemy throughout
- All 7 blueprints (dashboards, transactions, budgets, analytics, debts, settings, api) — sqlite3 → SQLAlchemy; full PostgreSQL SQL (EXTRACT, TO_CHAR, named params, RETURNING id, boolean literals)
- `settings/routes.py` — backup routes removed; download-database → JSON export; delete-all-data uses DELETE FROM
- `migrations/migrate_to_postgres.py` — one-shot migration with --dry-run flag; handles all 8 tables + user_owners + category seeds + sequence reset
- `seeds/categories.py` — 13 universal category seeds

**Phase 1 complete.** Moving to Phase 2 (Auth Overhaul).

### February 2026 — Session 5
Phase 2 (Auth Overhaul) implemented:
- `auth.py` fully rewritten — JWT Bearer auth, session auth, DB-backed login, token revocation
- `app.py` — Flask-Limiter added
- `blueprints/api/routes.py` — `/api/login` now returns real JWT (was 501 stub)
- `utils.py` — `current_user_id()` added; owners scoped to `user_owners` table
- `migrations/set_initial_password.py` — new script; auto-loads `Desktop/.env`

**Neon setup confirmed:** DATABASE_URL in Railway env vars + Desktop/.env ✅
**Phase 2 complete.** Next: run set_initial_password.py, deploy, then Phase 3 (Route Scoping).

### February 2026 — Session 6
Phase 3 (Route Scoping) implemented — all 130+ SQL statements across 7 blueprints scoped to `user_id`:
- `utils.py` — `uid_clause()` helper added; returns `('AND user_id = :_uid', {'_uid': uid})` or `('', {})` in dev mode
- `blueprints/api/routes.py` — `_year_month_owner_filter()` + all ~30 endpoints scoped; INSERTs include `user_id`
- `blueprints/analytics/routes.py` — `_build_analytics_filters()` scoped; bulk UPDATE scoped
- `blueprints/dashboards/views.py` — all 17+ queries scoped (overview, budget, categories views)
- `blueprints/transactions/routes.py` — all SELECTs/INSERTs/UPDATEs/DELETEs scoped
- `blueprints/budgets/routes.py` — all 35+ queries scoped; ON CONFLICT UPSERTs fixed to include `user_id` in INSERT columns; `sync_budgets_from_commitments` threads `uid` param
- `blueprints/debts/routes.py` — all SELECTs/INSERTs scoped; cascade delete verified via ownership check
- `blueprints/settings/routes.py` — export scoped to current user; delete-all scoped to current user's rows
- Dev mode (`JWT_SECRET_KEY == 'dev-jwt-secret'`) → `uid_clause()` returns `('', {})` → no filter → all data visible (no regression)

**Phase 3 complete.** Next: Phase 4 (Admin Panel / User Management).

### February 2026 — Session 7
Phase 4 (Admin Panel / User Management) implemented:
- `auth.py` — `require_admin()` helper added; bypassed in dev mode; redirects non-admins to dashboard with flash
- `blueprints/admin/__init__.py` — new (empty)
- `blueprints/admin/routes.py` — new; `before_request` gates all routes via `require_admin()`; endpoints: GET `/admin/` (users table + create form), POST `/admin/users/create`, POST `/admin/users/<id>/deactivate`, POST `/admin/users/<id>/activate`, GET `/admin/audit-logs` (filtered, last 200)
- `blueprints/settings/routes.py` — new `GET /settings/export-my-data` (user-scoped JSON, audit logged); `GET /settings/download-database` now admin-only, full unscoped dump, audit logged
- `templates/admin.html` — users table + create-user form
- `templates/admin_audit_logs.html` — audit log table with user/action filters
- `templates/base.html` — conditional Admin nav link (visible to `role == 'admin'` only)
- `templates/settings.html` — "Export My Data" link added to Data Management section
- `app.py` — `admin_bp` imported and registered

**Known issue:** Page loads are slow on Railway (observed Feb 2026). Investigate DB connection pooling / cold-start latency in a future session.

**Phase 4 complete.** Next: Phase 5 (New User Onboarding Flow).
