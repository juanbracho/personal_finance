# Finance Dashboard — Mobile Expansion Status
*Last updated: February 20, 2026*

---

## Current Status: Phase 2 — Flutter connected to local Flask ✅ (mostly working)

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

### Phase 3 — Railway Deployment Files ✅ CREATED (not deployed yet)
- `Desktop/Procfile` — `web: python desktop_app_launcher.py`
- `Desktop/railway.json` — build/deploy config with healthcheck
- `Desktop/requirements.txt` — Flask, SQLAlchemy, pandas, numpy, gunicorn, flask-cors

### Phase 4 — Desktop Launcher Updated ✅ COMPLETE
`Desktop/desktop_app_launcher.py` now supports 3 modes:
1. **Local** (default) — starts Flask on 127.0.0.1:5000, opens PyWebView
2. **Cloud desktop** (`FINANCE_API_URL` set) — skips local Flask, opens PyWebView at cloud URL, reads API key from `~/.financed/config.json`
3. **Railway server** (`RAILWAY_ENVIRONMENT` set) — runs Flask on `0.0.0.0:$PORT`, no PyWebView

---

## Current Known Issues / In Progress

### 1. Flask must be started manually for Phase 2 testing
The desktop `.app` bundle writes live data to:
```
~/Library/Application Support/FinanceDashboard/data/personal_finance.db
```
But running `python app.py` from `Desktop/` reads `Desktop/data/personal_finance.db` (old/test data, stuck at Jan 2026).

**Correct start command for Phase 2:**
```bash
cd ~/Library/Application\ Support/FinanceDashboard && \
FLASK_HOST=0.0.0.0 FLASK_PORT=5001 \
python "/Users/elcacas/Desktop/Finance Dashboard/Desktop/app.py"
```

At the end of the session, the user was about to test this. It had not been confirmed working yet.

### 2. Budgets showing $0 spent — suspected cause: wrong database
Budget analysis filters by current month (February 2026). The `Desktop/data/` DB is old (Jan 2026 data). Once Flask is started from the correct directory (above), budgets should show real spending.

### 3. Transactions stopping at Jan 17 — same cause as #2
Transactions endpoint is working and returns data, but from the old database. Fix is same as above.

### 4. Add Transaction not yet tested with real API
The `POST /api/transactions` endpoint exists and is wired up in Flutter. Has not been tested end-to-end yet.

---

## What to Do Next Session

### Immediate (still Phase 2)
1. Confirm Flask starts correctly from `~/Library/Application Support/FinanceDashboard` — verify budgets and transactions show Feb 2026 data
2. Test Add Transaction: fill in the form, hit save, verify it appears in the transactions list and in the desktop app
3. Test filter by owner on transactions screen
4. Check the Home screen numbers match what the desktop app shows (sanity check)
5. Test on physical iPhone if possible (needs to be on same WiFi as Mac)

### Phase 3 — Railway Cloud (when Phase 2 fully validated)
1. Create Railway account → new project → connect GitHub repo
2. Set env vars on Railway:
   - `API_SECRET_KEY` = `openssl rand -hex 32` (generate one)
   - `DATABASE_URL` = `sqlite:////data/personal_finance.db`
   - `SECRET_KEY` = another random string
   - `CORS_ORIGINS` = `https://finance.juanbracho.com`
3. Add Railway persistent volume mounted at `/data`
4. Configure custom domain `finance.juanbracho.com`
5. Add DNS A record at registrar: `finance` → Railway IP
6. Upload live database to Railway via settings endpoint

### Phase 5 — Flutter to Cloud
1. Update `config.dart`: `baseUrl = 'https://finance.juanbracho.com'`
2. Store production API key via `flutter_secure_storage`
3. Remove `NSAllowsArbitraryLoads` from `ios/Runner/Info.plist` (replace with specific domain exception)
4. Build release APK (Android sideload)
5. Build iOS IPA (Xcode → Product → Archive → direct install)

---

## Architecture Reference

```
Mac LAN IP:     192.168.1.164
Flask port:     5001 (5000 blocked by macOS AirPlay Receiver)
Flutter baseUrl: http://192.168.1.164:5001   ← Phase 2
                 https://finance.juanbracho.com  ← Phase 5

Live DB location (desktop app):
  ~/Library/Application Support/FinanceDashboard/data/personal_finance.db

API auth:
  Header: Authorization: Bearer <API_SECRET_KEY>
  Env var empty = no auth (local dev bypass)

All Flutter API endpoints are under /api/* and auth-protected.
Non-API HTML routes are unprotected (desktop web frontend).
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
  app.py                          — Flask factory, FLASK_HOST/PORT env var support
  auth.py                         — Bearer token check_api_key()
  config.py                       — Config, DesktopConfig, ProductionConfig
  desktop_app_launcher.py         — 3-mode launcher (local/cloud-desktop/railway)
  Procfile                        — Railway start command
  railway.json                    — Railway build config
  requirements.txt                — Python deps
  blueprints/api/routes.py        — All API endpoints incl. new /api/transactions, /api/debts
  templates/base.html             — Injects window.FINANCE_API_KEY
  static/js/main.js               — apiCall() with auth header

Mobile/
  expansion_plan.md               — Full architecture plan
  status.md                       — This file
  finance_dashboard_mobile/
    lib/
      main.dart                   — App root, router, themes
      config.dart                 — baseUrl (change per phase)
      models/                     — Transaction, BudgetCategory, DashboardSummary, DebtAccount
      services/api_service.dart   — HTTP client + MockData
      providers/app_providers.dart — Riverpod FutureProviders (real API)
      screens/                    — home, add_transaction, transactions, budgets, debts
      widgets/                    — stat_card, budget_progress_tile
    ios/
      Runner/Info.plist           — NSAllowsArbitraryLoads (remove before production)
      Podfile                     — platform :ios, '13.0'
```
