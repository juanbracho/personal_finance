# Multi-User Migration — Status Log
*Reference: `multiuser_migration.md` (plan) · `project_context.md` (app overview)*

---

## Current State

**Active Phase:** Phase 7 — Bug Fixes (post-Neon migration)
**Overall Progress:** Phase 6 complete ✅
**Last Session:** March 2026

---

## Phase Tracker

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Database Migration (SQLite → PostgreSQL on Neon, schema changes) | ✅ Complete |
| 2 | Auth Overhaul (JWT, password hashing, session update) | ✅ Complete |
| 3 | Route Scoping (user_id on all queries) | ✅ Complete |
| 4 | Admin Panel & User Management | ✅ Complete |
| 5 | New User Onboarding Flow | ✅ Complete |
| 6 | Flutter Update (JWT + 401 handling) | ✅ Complete |
| 7 | Debug: end-to-end test of Phases 4 + 5 + 6 together | ⏳ Pending |

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

### February 2026 — Session 8
Phase 5 (New User Onboarding Flow) implemented:
- Neon DB — `ALTER TABLE users ADD COLUMN IF NOT EXISTS onboarded BOOLEAN NOT NULL DEFAULT FALSE`; `UPDATE users SET onboarded = TRUE WHERE username = 'suricata'`
- `models.py` — `onboarded` field added to `User` model
- `auth.py` — after successful login, redirect to `/onboarding` if `not user.onboarded`; `/onboarding` and `/onboarding/complete` added to `_SKIP_ENDPOINTS` to prevent session-redirect loops
- `blueprints/onboarding/__init__.py` — new (empty)
- `blueprints/onboarding/routes.py` — GET `/onboarding` (welcome page); POST `/onboarding/complete` (seeds user_owners + budget_templates, marks onboarded=TRUE, logs audit)
- `templates/onboarding.html` — welcome page; owner-name field pre-filled with username; 13 starter categories listed; single "Get Started →" submit
- `app.py` — `onboarding_bp` imported and registered

Dev mode: `/onboarding` redirects straight to dashboard (no-op).
suricata: already marked `onboarded=TRUE` — goes straight to dashboard.

**Phase 5 complete.** Next: Phase 6 (Flutter JWT + 401 handling).

### February 2026 — Session 9
Phase 6 (Flutter JWT + 401 handling) implemented:
- `services/api_service.dart` — `static onUnauthorized` callback added; called (if set) before `throw ApiException` in both `_getRaw` and `_post` when `statusCode == 401`
- `auth_notifier.dart` — `_sessionExpiredRemotely` bool field + getter added; `logout({bool expired})` sets it; `setLoggedIn(true)` resets it
- `main.dart` — `import 'services/api_service.dart'` added; `ApiService.onUnauthorized` wired to `_authNotifier.logout(expired: true)` after `_authNotifier.init()`
- `screens/login_screen.dart` — conditional banner rendered at top of login card when `authNotifier.sessionExpiredRemotely` is true; disappears automatically on next successful login

**Phase 6 complete.** Next: Phase 7 (Bug fixes + end-to-end test of Phases 4 + 5 + 6 together).

### February 2026 — Session 10
Phase 7 — Bug fixes discovered after deploying to Railway + Neon:

**Bug 1: Web app defaulting to wrong month (UTC vs local time)**
- Root cause: Railway runs in UTC; `datetime.now()` returned March 1 for US timezones late in the evening
- Fix (part 1): Added `local_now()` to `utils.py` — reads `kanso_tz` cookie (set by browser JS) first, falls back to `APP_TIMEZONE` env var, then UTC; used as drop-in replacement for `datetime.now()` across all blueprints
- Fix (part 2): Added JS snippet to `base.html` `<head>` — (a) writes `kanso_tz=<IANA timezone>` cookie on every page load; (b) on first-ever visit (cookie not yet set), redirects date-sensitive pages (`/dashboard/*`, `/budget`) with explicit `?month=&year=` from `new Date()` before body renders — no flash of wrong content
- Files changed: `utils.py`, `config.py`, `templates/base.html`, all 5 blueprint files (`dashboards/routes.py`, `dashboards/views.py`, `budgets/routes.py`, `api/routes.py`, `analytics/routes.py`)

**Bug 2: Flutter mobile app showing wrong month (same root cause, different path)**
- Root cause: `app_providers.dart` was parsing the `period` field from the API response (UTC server time) and using it to display the month label, overriding the correct device-local month/year already stored in providers
- Fix: Removed the `period` string parsing; `monthName` and `yearStr` now derived directly from `month`/`year` provider values (device-local time)
- File changed: `Mobile/finance_dashboard_mobile/lib/providers/app_providers.dart`

**Bug 3: Categories tab showing "No categories found" despite data existing**
- Root cause: `api_categories()` in `blueprints/api/routes.py` uses a LEFT JOIN between `transactions` and `budget_templates`; both tables have a `user_id` column; PostgreSQL threw "column reference 'user_id' is ambiguous"; exception was silently caught and returned `{error: ...}`; JS received a non-array and displayed empty state
- Fix: Introduced `joined_filter` (same as `date_filter` but with `AND t.user_id` instead of `AND user_id`) for the LEFT JOIN query; also added `AND bt.user_id = t.user_id` to the JOIN condition for proper multi-user scoping
- File changed: `blueprints/api/routes.py` — `api_categories()` function only

### March 2026 — Session 11
Phase 7 continued — Categories CRUD overhaul (Overview > Categories view):

**Bug 4: Delete with active transactions required two clicks**
- Root cause: After migration modal completed, `executeMigration()` only reloaded the tab but did not auto-call the DELETE endpoint; user had to click delete a second time
- Fix: Added `_pendingDeleteAfterMigration` flag in `dashboard.js`; set before opening migration modal; after successful migration, auto-calls DELETE endpoint and resets flag; `hidden.bs.modal` listener resets flag if user cancels
- File changed: `static/js/dashboard.js`

**Bug 5: Add Type did nothing (no error, no result)**
- Root cause: Types are not stored in their own table — they exist only as `transactions.type` column values. `add_type()` was returning 200 success without writing anything. `api_types()` queries transactions only, so a new type with 0 transactions never appeared.
- Fix: Created `custom_types` table on Neon (`id, user_id, name, created_at, UNIQUE(user_id,name)`). `add_type()` now INSERTs into it. `api_types()` UNIONs transaction-derived types with `custom_types` rows that have no transactions yet. `edit_type()` and `delete_type()` also update/remove the `custom_types` row.
- DB migration: `CREATE TABLE custom_types` applied to Neon main branch
- Files changed: `models.py` (CustomType model), `blueprints/api/routes.py` (all 4 type endpoints)

**Bug 6: Add Subcategory, Add Owner, Add Account all did nothing (same root cause)**
- Root cause: Same as Bug 5. Subcategories and accounts have no backing table (derived from transactions). Owners have `user_owners` but `add_owner()` was not inserting into it, and `api_owners()` was not querying it.
- Fix (subcategories): Created `custom_subcategories` table (`id, user_id, name, category, created_at`). `add_subcategory()` inserts into it. `api_subcategories()` UNIONs with zero-txn rows. `edit_subcategory()` / `delete_subcategory()` sync the table.
- Fix (owners): `add_owner()` now inserts into `user_owners`. `api_owners()` UNIONs `user_owners` entries with no transactions. `edit_owner()` now also updates `user_owners`.
- Fix (accounts): Created `custom_accounts` table (`id, user_id, name, created_at`). `add_account()` inserts into it. `api_accounts()` UNIONs with zero-txn rows. `edit_account()` / `delete_account()` sync the table.
- DB migrations: `CREATE TABLE custom_subcategories`, `CREATE TABLE custom_accounts` applied to Neon main branch
- Files changed: `models.py` (CustomSubcategory, CustomAccount models), `blueprints/api/routes.py` (all GET/POST/PUT/DELETE for subcategories, owners, accounts)

**Bug 7: api_categories() missed newly added categories (zero transactions)**
- Root cause: The GET query anchored on `transactions` with a LEFT JOIN to `budget_templates`; categories with 0 transactions (just added) were invisible even though their `budget_templates` row existed.
- Fix: Flipped the query — now anchors on `budget_templates` with a LEFT JOIN to a transaction aggregate subquery; zero-transaction categories appear with zeroed stats. Type falls back to `budget_templates.notes` when no transactions exist.
- File changed: `blueprints/api/routes.py` — `api_categories()` only

**Bug 8: migrate_categories() left orphaned rows in backing tables**
- Root cause: After migrating transactions from source → target, the source entry in `custom_types` / `custom_subcategories` / `custom_accounts` / `user_owners` was not cleaned up.
- Fix: `migrate_categories()` now also cleans/renames the relevant backing table row after migrating transactions (DELETE for custom_* tables; UPDATE name for user_owners).
- File changed: `blueprints/api/routes.py` — `migrate_categories()` only

**Schema summary — new tables added to Neon:**
| Table | Purpose |
|-------|---------|
| `custom_types` | Pre-created types before any transactions use them |
| `custom_subcategories` | Pre-created subcategories (name + parent category) |
| `custom_accounts` | Pre-created account names |

`user_owners` was already present — now properly used by the add/edit/list owner flow.

### March 2026 — Session 12
Phase 7 continued — Bug fixes from end-to-end Railway testing:

**Bug 9: Migration modal transaction count shows only current year**
- Root cause: `transaction_count` in category/subcategory list endpoints is year-filtered; modal header used that value but migration_preview (and actual migration) operates on all years
- Fix: `migration_preview` endpoint now runs a COUNT(*) without LIMIT to get true all-years total; returns `{total_count, transactions}` instead of bare array; JS updates modal count from `total_count` after preview loads
- Files changed: `blueprints/api/routes.py`, `static/js/dashboard.js`

**Bug 10: Onboarding "Get Started" → 502 Bad Gateway**
- Root cause: `INSERT INTO user_owners` in `onboarding_complete` omitted `is_active`; column is NOT NULL with no DB-level DEFAULT (SQLAlchemy `default=True` is Python-side only); Postgres rejected the INSERT, crashing the Gunicorn worker
- Fix: Added `is_active = TRUE` explicitly to the INSERT
- File changed: `blueprints/onboarding/routes.py`

**Bug 11: Onboarding page content flush against card edges**
- Fix: Added `style="padding: 20px;"` to both `.kanso-card` divs in onboarding template
- File changed: `templates/onboarding.html`

**Bug 12: Settings page → 502 Bad Gateway**
- Root cause 1: `url_for('settings.create_backup')` in template referenced a non-existent route; Jinja2 raises BuildError at render time
- Root cause 2: Route passes `db_exists=True, db_size=None`; template did `None / 1024 / 1024` → TypeError
- Fix 1: Added stub routes `create_backup`, `restore_backup`, `delete_backup` (flash "not available on cloud")
- Fix 2: Template size display now guards `db_size` with truthiness check
- Files changed: `blueprints/settings/routes.py`, `templates/settings.html`

**Bug 13: Admin panel moved into Settings page**
- Admin section now appears at the bottom of Settings (above Danger Zone) for admin users only
- `settings/routes.py` — queries `User` list when `session.role == 'admin'`, passes `users` to template
- `settings.html` — admin section conditionally rendered (`{% if users is not none %}`) with users table + create-user form (with proper `padding: 20px`)
- `admin/routes.py` — GET `/admin/` now redirects to `settings.index`; all POST action redirects changed from `admin.admin_dashboard` → `settings.index`
- `base.html` — removed standalone "Admin" nav link (admins reach admin tools via Settings)
- `admin.html` — still exists but unreachable; audit logs page at `/admin/audit-logs` still works

**Bug 14: Data Management section broken / misleading after SQLite → PostgreSQL migration**
- Root cause: The entire Data Management UI was designed around SQLite local files. When migrating to PostgreSQL (Neon), backup/restore routes were stubbed out (`flash("not available")`) but the template still rendered the old layout — "Export Database" button calling dead `downloadDatabase()` JS, "Import Database" row with a `.db` file picker, orange "Cloud Hosting Notice" that referenced the old SQLite backup flow, and "Create Local Backup" that flashedand redirected on both local and cloud. The feature was never rethought for the new stack.
- Fix: Full Data Management redesign split into two modes based on `_auth_disabled()`:
  - **Cloud mode** (Railway, real JWT): single "Export My Data" row (user-scoped JSON); neutral info note; no backup history, no import
  - **Local mode** (dev JWT, local Neon/Postgres): "Export My Data" + "Create Local Backup" rows; Backup History section with per-file Download (anchor → GET `restore_backup`) + Delete (POST form) buttons; backups saved to `Desktop/data/backups/` as timestamped JSON
- New helpers in `settings/routes.py`: `_is_local_mode()`, `_backups_dir()`, `_serial()`, `_export_all_data(uid)` (DRY; used by both `export_my_data` and `create_backup`)
- `download_database()` simplified to redirect → `export_my_data` (admin gate removed)
- Dead JS `downloadDatabase()` function removed from template
- Files changed: `blueprints/settings/routes.py`, `templates/settings.html`

**Bug 15: Flutter debt tab shows all users' debts instead of the logged-in user's**
- Root cause: `api_debts_list()` (`GET /api/debts`) was missing `uid_clause()` entirely — both query branches (normal and show_paid_off) selected from `debt_accounts` with no `user_id` filter, so every authenticated user saw the full table
- Fix: Added `uid_sql, uid_p = uid_clause()` and injected into both queries (`WHERE 1=1 {uid_sql}` for the all-statuses branch; `WHERE is_active = true {uid_sql}` for the active-only branch); params dict passed to `conn.execute()`
- File changed: `blueprints/api/routes.py` — `api_debts_list()` only

**Bug 16: Danger Zone — stale description and incomplete delete scope**
- Root cause 1: Description said "A backup is created automatically before deletion" — true in the SQLite era (file copy), false with PostgreSQL. No auto-backup exists.
- Root cause 2: `delete_all_data()` table list was missing `custom_types`, `custom_subcategories`, `custom_accounts`, `user_owners` (all added in Session 11); deleting a user's data left those rows behind.
- Root cause 3: Description was not mode-aware — always said "all financial data" regardless of whether cloud scoping meant only the user's rows would be deleted.
- Fix (backend): Added the four missing tables to the FK-safe delete list in `delete_all_data()`
- Fix (template): Removed false auto-backup claim; description now conditional (`local_mode`: "all financial data" / cloud: "all your financial data"); added "Download backup →" link pointing to `export_my_data` so users can save a copy before wiping
- Files changed: `blueprints/settings/routes.py` (`delete_all_data()` table list), `templates/settings.html` (danger zone description)
