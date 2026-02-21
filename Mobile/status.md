# Finance Dashboard — Mobile Expansion Status
*Last updated: February 21, 2026*

---

## Current Status: Phase 4 — Production hardened, ready for Flutter cloud connection ✅

---

## What Has Been Done

### Phase 1 — Flutter App with Mock Data ✅ COMPLETE & APPROVED
- Flutter project created at `Mobile/finance_dashboard_mobile/`
- All 5 screens built and UI approved by user:
  - **Home** — budget health banner, 4 stat cards (spent, remaining, total debt, min payments), 6-month bar chart (fl_chart)
  - **Add Transaction** — full form with expense/income toggle, date picker, category/owner/account dropdowns, business flag
  - **Transactions** — scrollable list, filter sheet (owner, category)
  - **Budgets** — progress bars per category, over-budget warning, totals summary
  - **Debts** — per-debt cards with paid-off progress bar, APR, min payment, due date
- State management: Riverpod (`FutureProvider` per screen)
- Navigation: go_router with `StatefulShellRoute` (persistent bottom nav)
- Theme: dark navy finance theme (Material 3)
- Dependencies: flutter_riverpod, go_router, http, flutter_secure_storage, intl, fl_chart

### Phase 2 — Flask Backend Auth & API ✅ COMPLETE
Files modified in `Desktop/`:

| File | What Changed |
|---|---|
| `auth.py` | **New** — `check_api_key()` Bearer token validator. No-op when `API_SECRET_KEY` env var is empty (safe for local dev) |
| `config.py` | Added `API_SECRET_KEY`, `CORS_ORIGINS`, new `ProductionConfig` class for Railway |
| `app.py` | CORS registered, auth hook wired to api blueprint via `before_request`. Added `FLASK_HOST`/`FLASK_PORT` env var support for running on network |
| `blueprints/api/routes.py` | Added 3 Flutter-facing endpoints: `GET /api/transactions` (paginated JSON), `POST /api/transactions` (add from JSON), `GET /api/debts` (debt list JSON) |
| `templates/base.html` | Injects `window.FINANCE_API_KEY` from Flask config for web frontend auth |
| `static/js/main.js` | `apiCall()` now sends `Authorization: Bearer` header automatically |

### Phase 2 — Flutter Wired to Real API ✅ COMPLETE
Files modified in `Mobile/finance_dashboard_mobile/lib/`:

| File | What Changed |
|---|---|
| `config.dart` | `baseUrl = 'http://192.168.1.164:5001'` (Mac's LAN IP, port 5001) |
| `services/api_service.dart` | Rewrote to match actual Flask response shapes. Key detail: categories/owners/accounts return flat JSON lists, dashboard_summary returns nested map, budget_analysis returns flat list |
| `providers/app_providers.dart` | All providers switched from mock data to real API calls with correct parsing |
| `models/debt.dart` | `due_date` parsed with `.toString()` — stored as int in DB, not string |
| `ios/Runner/Info.plist` | Added `NSAllowsArbitraryLoads: true` for local HTTP (remove before App Store) |
| `ios/Podfile` | Uncommented `platform :ios, '13.0'` — fixes CocoaPods warning |

### Phase 3 — Railway Deployment ✅ COMPLETE & LIVE

#### Infrastructure
- Railway project created, connected to GitHub repo
- Root directory set to `Desktop` in Railway service settings
- Persistent volume mounted at `/app/data` — all relative `data/` paths in the app land here
- Railway auto-detects `RAILWAY_ENVIRONMENT` and runs Flask in server mode (no PyWebView)

#### Environment Variables set on Railway
| Variable | Purpose |
|---|---|
| `DATABASE_URL` | `sqlite:////app/data/personal_finance.db` |
| `SECRET_KEY` | Flask session signing key |
| `API_SECRET_KEY` | Bearer token for Flutter API auth |
| `CORS_ORIGINS` | `*` (to be locked down after Flutter connected) |
| `DASHBOARD_USERNAME` | Web dashboard login username |
| `DASHBOARD_PASSWORD` | Web dashboard login password |

#### Code changes for Railway
| File | What Changed |
|---|---|
| `requirements.txt` | Added `python-dateutil` (used by `budget_recommender.py`) |
| `auth.py` | Full rewrite — added session login Blueprint (`auth_bp`), login/logout routes, `check_web_session()` app-level hook |
| `app.py` | Registered `auth_bp`, wired `check_web_session` as `app.before_request` |
| `config.py` | Added `DASHBOARD_USERNAME` and `DASHBOARD_PASSWORD` config vars |
| `templates/login.html` | **New** — dark-themed login page matching app style |
| `templates/base.html` | Added Sign Out button to navbar (only shown when session active) |

#### Database
- Live backup from `~/Library/Application Support/FinanceDashboard/data/backups/backup_20260221_083626.db` uploaded via `/settings` page
- Dashboard confirmed showing real data: $10,323.57 monthly spending, $93,898.37 active debts

#### Auth summary (two layers)
| Layer | Mechanism | Covers |
|---|---|---|
| Web UI | Session login (`DASHBOARD_USERNAME` / `DASHBOARD_PASSWORD`) | All non-API, non-static routes |
| Flutter API | Bearer token (`API_SECRET_KEY`) | All `/api/*` routes |
| Local desktop | No auth (env vars not set locally) | All routes — unchanged behavior |

#### URLs
- Railway URL: `https://personalfinance-production-0e5b.up.railway.app`
- Custom domain: `https://finance.juanbracho.com` ← **pending DNS verification**

#### DNS records added in Cloudflare (juanbracho.com)
| Type | Name | Value |
|---|---|---|
| `CNAME` | `finance` | `4vdt6k0y.up.railway.app` (DNS only, no proxy) |
| `TXT` | `_railway-verify.finance` | `railway-verify=88a651f5158d008ecfd39a88abd9ede01719f17511f135a140f80a1b1648ca91` |

#### Credential files (gitignored, at project root)
- `railway-dns.txt` — DNS record values
- `railway-credentials.txt` — `DASHBOARD_USERNAME` / `DASHBOARD_PASSWORD`

---

### Phase 4 — Production Hardening ✅ COMPLETE

#### Custom domain
- `https://finance.juanbracho.com` live and verified (Let's Encrypt cert issued Feb 21 2026)
- Cloudflare proxy (orange cloud) enabled on `finance` CNAME — handles HTTP → HTTPS redirect

#### CORS locked down
- `CORS_ORIGINS` env var added on Railway: `https://finance.juanbracho.com`
- Replaced Flask-CORS library with a manual `after_request` handler in `app.py` for strict origin enforcement
- Verified: foreign origins receive no `Access-Control-Allow-Origin` header

#### Session expiry
- Sessions now expire after **1 hour** of inactivity
- `login_time` timestamp stored on login, checked on every request in `check_web_session()`
- Implemented in `auth.py` via `SESSION_LIFETIME_SECONDS = 3600`

---

## Current Known Issues / In Progress

None.

---

## What to Do Next Session

### Immediate

### Phase 5 — Flutter to Cloud
1. Update `config.dart`: `baseUrl = 'https://finance.juanbracho.com'`
2. Store production `API_SECRET_KEY` via `flutter_secure_storage`
3. Remove `NSAllowsArbitraryLoads` from `ios/Runner/Info.plist` (replace with specific domain exception for `finance.juanbracho.com`)
4. Test all 5 screens against production API
5. Build release APK (Android sideload)
6. Build iOS IPA (Xcode → Product → Archive → direct install)

### Phase 6 — Web Dashboard login UX (optional)
- Add "Remember me" / persistent session (currently expires on browser close)
- Add password change route in settings

---

## Architecture Reference

```
Railway URL:    https://personalfinance-production-0e5b.up.railway.app
Custom domain:  https://finance.juanbracho.com  ← pending verification
Flask port:     8080 (Railway $PORT)

Live DB location (Railway):
  /app/data/personal_finance.db  (persistent volume)

Live DB location (desktop app):
  ~/Library/Application Support/FinanceDashboard/data/personal_finance.db

API auth:
  Header: Authorization: Bearer <API_SECRET_KEY>
  Env var empty = no auth (local dev bypass)

Web auth:
  Session cookie, credentials in DASHBOARD_USERNAME / DASHBOARD_PASSWORD env vars
  Env var empty = no auth (local desktop bypass)

Flutter baseUrl:
  http://192.168.1.164:5001   ← Phase 2 (LAN, still current)
  https://finance.juanbracho.com  ← Phase 5 (next)

All Flutter API endpoints are under /api/* — Bearer token protected.
Non-API HTML routes are session-login protected (on Railway).
```

## Flask Response Shape Reference (for parsing)

| Endpoint | Response Shape |
|---|---|
| `GET /api/dashboard_summary` | `{summary: {total_monthly_spending, total_debt, total_minimum_payments, period: "YYYY-MM"}, monthly_spending: {Expense: {total, count}}}` |
| `GET /api/monthly_trends` | `[{month: "YYYY-MM", Expense: float, Income: float}, ...]` |
| `GET /api/budget_analysis` | `[{category, effective_budget, actual_spending, variance, status: "over"/"under"/"on_track"}, ...]` |
| `GET /api/transactions` | `{transactions: [...], total: int, page: int, pages: int}` |
| `POST /api/transactions` | `{success: bool, id: int}` |
| `GET /api/debts` | `{debts: [...], total_debt: float, total_minimum_payments: float}` |
| `GET /api/categories/categories` | `[{name, type, transaction_count, ...}, ...]` — flat list |
| `GET /api/categories/owners` | `[{name, transaction_count, ...}, ...]` — flat list |
| `GET /api/accounts/list` | `[{name, account_type, is_debt, ...}, ...]` — flat list |

## Key Files Index

```
Desktop/
  app.py                          — Flask factory, registers auth_bp + check_web_session
  auth.py                         — Bearer token check_api_key() + session login auth_bp
  config.py                       — Config, DesktopConfig, ProductionConfig
  desktop_app_launcher.py         — 3-mode launcher (local/cloud-desktop/railway)
  Procfile                        — web: python desktop_app_launcher.py
  railway.json                    — Railway build config (NIXPACKS, healthcheck /)
  requirements.txt                — Flask, SQLAlchemy, pandas, numpy, gunicorn, flask-cors, python-dateutil
  blueprints/api/routes.py        — All API endpoints incl. /api/transactions, /api/debts
  templates/login.html            — Web dashboard login page
  templates/base.html             — Injects window.FINANCE_API_KEY, Sign Out button
  static/js/main.js               — apiCall() with auth header

Mobile/
  expansion_plan.md               — Full architecture plan
  status.md                       — This file
  finance_dashboard_mobile/
    lib/
      main.dart                   — App root, router, themes
      config.dart                 — baseUrl (change to finance.juanbracho.com for Phase 5)
      models/                     — Transaction, BudgetCategory, DashboardSummary, DebtAccount
      services/api_service.dart   — HTTP client + MockData
      providers/app_providers.dart — Riverpod FutureProviders (real API)
      screens/                    — home, add_transaction, transactions, budgets, debts
      widgets/                    — stat_card, budget_progress_tile
    ios/
      Runner/Info.plist           — NSAllowsArbitraryLoads (replace with domain exception before production)
      Podfile                     — platform :ios, '13.0'

Project root (gitignored):
  railway-dns.txt                 — Cloudflare DNS record values
  railway-credentials.txt         — Dashboard login credentials
```
