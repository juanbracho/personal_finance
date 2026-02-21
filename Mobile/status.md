# Finance Dashboard — Mobile Expansion Status
*Last updated: February 21, 2026*

---

## Current Status: Phase 5 — Flutter connected to production, data loading ✅ charts & polish pending

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
| `services/api_service.dart` | Rewrote to match actual Flask response shapes |
| `providers/app_providers.dart` | All providers switched from mock data to real API calls |
| `models/debt.dart` | `due_date` parsed with `.toString()` — stored as int in DB, not string |
| `ios/Runner/Info.plist` | Added `NSAllowsArbitraryLoads: true` for local HTTP (removed in Phase 5) |
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
| `CORS_ORIGINS` | `https://finance.juanbracho.com` |
| `DASHBOARD_USERNAME` | Web dashboard login username |
| `DASHBOARD_PASSWORD` | Web dashboard login password |

#### Database
- Live backup uploaded via `/settings` page
- Dashboard confirmed showing real data: $10,323.57 monthly spending, $93,898.37 active debts

#### Auth summary (two layers)
| Layer | Mechanism | Covers |
|---|---|---|
| Web UI | Session login (`DASHBOARD_USERNAME` / `DASHBOARD_PASSWORD`) | All non-API, non-static routes |
| Flutter API | Bearer token (`API_SECRET_KEY`) | All `/api/*` routes |
| Local desktop | No auth (env vars not set locally) | All routes — unchanged behavior |

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
- Web sessions expire after **1 hour**
- `login_time` timestamp stored on login, checked on every request in `check_web_session()`
- Mobile app token persists in secure storage indefinitely — only cleared on logout

---

### Phase 5 — Flutter to Cloud ✅ CONNECTED (polish pending)

#### What's working
- Flutter login screen — validates with Railway credentials via `POST /api/login`
- Token stored in `flutter_secure_storage` (iOS Keychain) — survives app switches and restarts
- Login only required when token is missing (first install or logout) — not on every app switch
- Home screen stat cards loading real data from production API
- Transactions screen loading real data
- Budgets screen loading real data
- Debts screen loading real data

#### Known issues to fix next session
1. **Charts not rendering** — Home screen bar chart (fl_chart) not displaying, likely a data shape or parsing issue
2. **Design tweaks needed** — UI polish pass across all 5 screens against real data
3. **Full feature test** — Add Transaction form needs end-to-end test (submit → appears in list)

#### Code changes made
| File | What Changed |
|---|---|
| `config.dart` | `baseUrl = 'https://finance.juanbracho.com'` |
| `ios/Runner/Info.plist` | Removed `NSAllowsArbitraryLoads` — not needed on HTTPS |
| `services/api_service.dart` | Added `login()` and `logout()` methods |
| `auth_notifier.dart` | **New** — `ChangeNotifier` tracking token presence, drives GoRouter redirect |
| `screens/login_screen.dart` | **New** — Dark-themed login UI matching app style |
| `main.dart` | Added `/login` route + `refreshListenable` + `redirect` logic |
| `Desktop/auth.py` | Exempt `api.api_login` from Bearer token check |
| `Desktop/blueprints/api/routes.py` | Added `POST /api/login` endpoint + `current_app` import fix |

---

## What to Do Next Session

### Phase 5 — Finish & Polish
1. **Fix charts** — Debug fl_chart bar chart on Home screen (data shape from `GET /api/monthly_trends`)
2. **Design pass** — Go screen by screen and fix layout/spacing issues against real data
3. **Test Add Transaction** — Submit a test transaction, confirm it appears in Transactions screen and web dashboard
4. **Test filters** — Owner filter, category filter on Transactions screen

### Phase 5 — Build & Install
5. **Android APK** — `flutter build apk --release` → sideload
6. **iOS IPA** — Xcode → Product → Archive → install via Xcode / AltStore

### Phase 6 — Web Dashboard UX (optional)
- Add "Remember me" / persistent session (currently expires on browser close)
- Add password change route in settings

---

## Architecture Reference

```
Railway URL:    https://personalfinance-production-0e5b.up.railway.app
Custom domain:  https://finance.juanbracho.com
Flask port:     8080 (Railway $PORT)

Live DB location (Railway):
  /app/data/personal_finance.db  (persistent volume)

Live DB location (desktop app):
  ~/Library/Application Support/FinanceDashboard/data/personal_finance.db

API auth:
  POST /api/login  → {username, password} → {token}   ← Flutter login
  Header: Authorization: Bearer <token>                ← all /api/* calls
  Env var empty = no auth (local dev bypass)

Web auth:
  Session cookie, credentials in DASHBOARD_USERNAME / DASHBOARD_PASSWORD env vars
  Session expires after 1 hour
  Env var empty = no auth (local desktop bypass)

Flutter baseUrl:
  https://finance.juanbracho.com  ← Phase 5 (current)

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
| `POST /api/login` | `{success: bool, token: str}` — public endpoint, no Bearer required |

## Key Files Index

```
Desktop/
  app.py                          — Flask factory, manual CORS handler, auth hooks
  auth.py                         — Bearer check_api_key() + session auth_bp + _API_PUBLIC_ENDPOINTS
  config.py                       — Config, DesktopConfig, ProductionConfig
  desktop_app_launcher.py         — 3-mode launcher (local/cloud-desktop/railway)
  Procfile                        — web: python desktop_app_launcher.py
  railway.json                    — Railway build config
  requirements.txt                — Flask, SQLAlchemy, pandas, numpy, gunicorn, flask-cors, python-dateutil
  blueprints/api/routes.py        — All API endpoints incl. /api/login, /api/transactions, /api/debts
  templates/login.html            — Web dashboard login page
  templates/base.html             — Injects window.FINANCE_API_KEY, Sign Out button
  static/js/main.js               — apiCall() with auth header

Mobile/
  status.md                       — This file
  finance_dashboard_mobile/
    lib/
      main.dart                   — App root, GoRouter with auth redirect
      config.dart                 — baseUrl = https://finance.juanbracho.com
      auth_notifier.dart          — ChangeNotifier for login state
      models/                     — Transaction, BudgetCategory, DashboardSummary, DebtAccount
      services/api_service.dart   — HTTP client, login(), logout()
      providers/app_providers.dart — Riverpod FutureProviders (real API)
      screens/                    — home, add_transaction, transactions, budgets, debts, login
      widgets/                    — stat_card, budget_progress_tile
    ios/
      Runner/Info.plist           — Clean (NSAllowsArbitraryLoads removed)
      Podfile                     — platform :ios, '13.0'

Project root (gitignored):
  railway-dns.txt                 — Cloudflare DNS record values
  railway-credentials.txt         — Dashboard login credentials
```
