# Finance Dashboard — Full Project Status
*Last updated: February 21, 2026*

---

## What Is This Project?

A personal finance dashboard built for one user (Juan Bracho) to track spending,
budgets, and debts across a household with multiple owners (Cacas, Cata, Suricata).

**Three surfaces, one SQLite database:**

| Surface | What It Is | Status |
|---|---|---|
| macOS Desktop App | PyWebView wrapper around Flask — local, no auth | ✅ Live |
| Web / Cloud Dashboard | Same Flask app deployed on Railway, browser login | ✅ Live |
| Mobile App (Flutter/iOS) | Flutter app hitting the Railway API via Bearer token | ✅ Connected, polish pending |

**Database facts:**
- Transaction types in DB: `Needs`, `Wants`, `Business`, `Savings` (NOT Expense/Income)
- Owners: `Cacas`, `Cata`, `Suricata`
- Live data as of Feb 21 2026: $10,323.57 monthly spending, $93,898.37 active debts
- Local DB: `~/Library/Application Support/FinanceDashboard/data/personal_finance.db`
- Railway DB: `/app/data/personal_finance.db` (persistent volume)
- Local backup copy: `Desktop/Finance Dashboard/Data backup/backup_20260221_084303.db`

---

## App Philosophy (defined Feb 21 2026 — expand next session)

### Mobile (Flutter) — Quick Glance & Quick Add
- "How's my budget doing this month?"
- "How are we tracking on debts?"
- Add a transaction on the spot (receipt in hand)
- Lightweight, fast, thumb-friendly
- NO deep editing, NO complex analytics

### Web / Cloud Dashboard — Power User Hub
- Edit & correct transactions
- Deep analytics (trends, category drilldown, year-over-year)
- Budget management (set budgets, add unexpected expenses)
- Debt tracking & payoff planning
- Settings, backups, data management

> **Next session:** flesh this philosophy out fully before any design work begins.
> It should drive every screen-level decision on both platforms.

---

## URLs & Access

| | URL |
|---|---|
| Railway (direct) | `https://personalfinance-production-0e5b.up.railway.app` |
| Custom domain | `https://finance.juanbracho.com` |
| Flutter baseUrl | `https://finance.juanbracho.com` |
| Flask port on Railway | `8080` (Railway `$PORT`) |

**DNS (Cloudflare — juanbracho.com):**
| Type | Name | Value |
|---|---|---|
| `CNAME` | `finance` | `4vdt6k0y.up.railway.app` — Proxied (orange cloud ON) |
| `TXT` | `_railway-verify.finance` | `railway-verify=88a651f5158d008ecfd39a88abd9ede01719f17511f135a140f80a1b1648ca91` |

Cloudflare proxy handles HTTP → HTTPS redirect automatically.

---

## Auth Architecture

| Layer | Mechanism | When Active |
|---|---|---|
| Web UI | Session cookie — `DASHBOARD_USERNAME` / `DASHBOARD_PASSWORD` env vars | Railway only |
| Web session expiry | 1 hour — `login_time` stored in session, checked on every request | Railway only |
| Flutter API | Bearer token — `API_SECRET_KEY` env var | Railway only |
| Flutter login | `POST /api/login` with dashboard credentials → returns Bearer token | Railway only |
| Flutter token storage | `flutter_secure_storage` (iOS Keychain) — persists across app switches | Always |
| Local desktop | No auth — all env vars empty = bypass | Local only |

**Flutter login flow:**
1. App starts → checks Keychain for stored token
2. No token → shows Login screen (username + password)
3. POST `/api/login` → Flask validates against `DASHBOARD_USERNAME`/`DASHBOARD_PASSWORD`
4. Returns `API_SECRET_KEY` as Bearer token → stored in Keychain
5. All subsequent `/api/*` calls send `Authorization: Bearer <token>`
6. Login NOT required on app switch — only on first install or after logout

---

## Railway Environment Variables

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | `sqlite:////app/data/personal_finance.db` |
| `SECRET_KEY` | Flask session signing key |
| `API_SECRET_KEY` | Bearer token for Flutter API auth |
| `CORS_ORIGINS` | `https://finance.juanbracho.com` |
| `DASHBOARD_USERNAME` | Web + Flutter login username |
| `DASHBOARD_PASSWORD` | Web + Flutter login password |

---

## CORS

Manual `after_request` handler in `app.py` (replaced Flask-CORS which leaked non-matching origins).
Only adds `Access-Control-Allow-Origin` header when requesting origin exactly matches `CORS_ORIGINS`.
Verified: foreign origins receive no ACAO header.

---

## Flask API Endpoints

All `/api/*` routes require `Authorization: Bearer <token>` **except** `/api/login`.

| Method | Endpoint | Auth | Response Shape |
|---|---|---|---|
| `POST` | `/api/login` | None | `{success, token}` |
| `GET` | `/api/dashboard_summary` | Bearer | `{summary: {total_monthly_spending, total_debt, total_minimum_payments, period}, monthly_spending: {Needs: {total,count}, Wants:..., ...}}` |
| `GET` | `/api/monthly_trends` | Bearer | `[{month: "YYYY-MM", expense: float}, ...]` — expense = sum of ALL types |
| `GET` | `/api/budget_analysis` | Bearer | `[{category, effective_budget, actual_spending, variance, status}, ...]` |
| `GET` | `/api/transactions` | Bearer | `{transactions: [...], total, page, pages}` |
| `POST` | `/api/transactions` | Bearer | `{success, id}` |
| `GET` | `/api/debts` | Bearer | `{debts: [...], total_debt, total_minimum_payments}` |
| `GET` | `/api/categories/categories` | Bearer | `[{name, type, transaction_count, ...}]` — flat list |
| `GET` | `/api/categories/owners` | Bearer | `[{name, transaction_count, ...}]` — flat list |
| `GET` | `/api/accounts/list` | Bearer | `[{name, account_type, is_debt, ...}]` — flat list |

**Important:** `monthly_trends` normalizes type keys to lowercase and sums all types
into a single `expense` field per month. The DB does NOT use `Expense`/`Income` —
it uses `Needs`, `Wants`, `Business`, `Savings`.

---

## Key Files Index

### Backend — `Desktop/` (deployed to Railway, root dir set to `Desktop/`)
```
app.py                        — Flask factory, manual CORS after_request handler, registers all blueprints + auth hooks
auth.py                       — check_api_key() Bearer validator, check_web_session() hook, auth_bp login/logout routes
                                _API_PUBLIC_ENDPOINTS = {'api.api_login'} exempts login from Bearer check
config.py                     — Config base, DesktopConfig, ProductionConfig (Railway)
desktop_app_launcher.py       — 3-mode launcher: local PyWebView / cloud desktop / Railway server
Procfile                      — web: python desktop_app_launcher.py
railway.json                  — Railway NIXPACKS build config + healthcheck
requirements.txt              — Flask, SQLAlchemy, pandas, numpy, gunicorn, flask-cors, python-dateutil

blueprints/api/routes.py      — ALL API endpoints (monthly_trends, dashboard_summary, budget_analysis,
                                transactions CRUD, debts, categories, accounts, /api/login)
blueprints/dashboards/        — Web dashboard HTML views
blueprints/transactions/      — Web transaction management
blueprints/budgets/           — Web budget management
blueprints/debts/             — Web debt management
blueprints/settings/          — Settings page (DB backup upload lives here)
blueprints/analytics/         — Web analytics views

templates/login.html          — Web dashboard login page (dark theme)
templates/base.html           — Base template, injects window.FINANCE_API_KEY, Sign Out button
static/js/main.js             — Web frontend JS, apiCall() sends Authorization: Bearer header
```

### Mobile — `Mobile/finance_dashboard_mobile/`
> ⚠️ `lib/` is in Flutter's .gitignore — Dart source files are local only, not in GitHub.
> They exist on the dev machine and are used to build the app.

```
lib/main.dart                 — App root, GoRouter with /login route + refreshListenable + redirect logic
lib/config.dart               — AppConfig: baseUrl = https://finance.juanbracho.com, apiKeyStorageKey
lib/auth_notifier.dart        — ChangeNotifier: tracks token presence, drives GoRouter auth redirect
lib/services/api_service.dart — HTTP client: all API calls, login(), logout(), _headers() with Bearer
lib/providers/app_providers.dart — Riverpod FutureProviders: dashboardSummary, monthlyTrends,
                                   budgets, transactions, debts, categories, owners, accounts
lib/models/
  transaction.dart            — Transaction model + fromJson/toJson
  budget.dart                 — BudgetCategory model
  debt.dart                   — DebtAccount model (due_date stored as int in DB)
  dashboard_summary.dart      — DashboardSummary model (budgetRemaining, budgetPercentUsed computed)
lib/screens/
  login_screen.dart           — Username/password login, calls ApiService.login()
  home_screen.dart            — Dashboard: budget health banner, 4 stat cards, 6-month bar+line chart
  add_transaction_screen.dart — Add transaction form
  transactions_screen.dart    — Scrollable transaction list + filter sheet
  budgets_screen.dart         — Budget progress bars per category
  debts_screen.dart           — Debt cards with payoff progress
lib/widgets/
  stat_card.dart              — Reusable stat card widget
  budget_progress_tile.dart   — Budget category progress row

ios/Runner/Info.plist         — Clean — NSAllowsArbitraryLoads removed (HTTPS only now)
ios/Podfile                   — platform :ios, '13.0'
```

### Project Root (gitignored — on dev machine only)
```
railway-dns.txt               — Cloudflare DNS record values
railway-credentials.txt       — DASHBOARD_USERNAME / DASHBOARD_PASSWORD
Data backup/                  — Local DB backups
  backup_20260221_084303.db   — Last uploaded backup (used to seed Railway DB)
```

---

## Full History — What Was Built & When

### Phase 1 — Flutter App with Mock Data ✅
- Flutter project scaffolded at `Mobile/finance_dashboard_mobile/`
- 5 screens built with hardcoded mock data, UI approved
- Dark navy Material 3 theme established
- Navigation: go_router `StatefulShellRoute` with persistent bottom nav bar
- State: Riverpod `FutureProvider` per screen
- Dependencies: flutter_riverpod, go_router, http, flutter_secure_storage, intl, fl_chart

### Phase 2 — Flask API + Flutter Wired to Local API ✅
- Added Bearer token auth to Flask (`check_api_key()`)
- Added 3 Flutter endpoints: `GET /api/transactions`, `POST /api/transactions`, `GET /api/debts`
- Flutter providers switched from mock data to real API calls against LAN IP `192.168.1.164:5001`
- CORS configured, web frontend updated to send Bearer header
- `NSAllowsArbitraryLoads` added to iOS for local HTTP (removed in Phase 5)

### Phase 3 — Railway Deployment ✅
- Railway project connected to GitHub, root dir set to `Desktop/`
- Persistent volume at `/app/data/` for SQLite DB
- Session-based web login added (`auth_bp`, login/logout routes, `check_web_session()`)
- `ProductionConfig` class added to `config.py`
- Login page (`templates/login.html`) built
- Live DB backup uploaded via `/settings`, confirmed real data showing

### Phase 4 — Production Hardening ✅
- Custom domain `https://finance.juanbracho.com` verified and live
- Cloudflare proxy enabled — handles HTTP→HTTPS redirect
- CORS locked down: replaced Flask-CORS with manual `after_request` handler
  (Flask-CORS 4.x reflected non-matching origins back — manual handler fixed this)
- `CORS_ORIGINS` Railway env var set to `https://finance.juanbracho.com`
- Web session expiry: 1 hour enforced via `login_time` timestamp in session

### Phase 5 — Flutter Connected to Production ✅ (polish pending)
- `POST /api/login` endpoint added — validates dashboard credentials, returns Bearer token
- Flutter login screen built — dark themed, matches app style
- `AuthNotifier` (ChangeNotifier) drives GoRouter redirect to /login if no token stored
- `config.dart` baseUrl updated to `https://finance.juanbracho.com`
- `NSAllowsArbitraryLoads` removed from `ios/Runner/Info.plist`
- `flutter_secure_storage` stores token in iOS Keychain — survives app switches
- **Chart fix:** DB uses `Needs/Wants/Business/Savings` not `Expense/Income`
  → `monthly_trends` endpoint updated to sum all types into single `expense` field
  → Home screen chart now shows bars + curved trend line with dots
  → Tap bar to reveal amount tooltip

---

## Current Known Issues / Pending Work

### Next Session — Start Here
1. **Flesh out app philosophy** — define exactly what belongs on mobile vs web before any design
2. **Design pass — Mobile** — screen by screen with real data, guided by "quick glance/quick add" philosophy
3. **Test Add Transaction** — submit test transaction, confirm it shows in list + web dashboard
4. **Test filters** — owner filter, category filter on Transactions screen
5. **Build & install** — `flutter build apk --release` (Android) + Xcode Archive (iOS IPA)

### Phase 6 — Web Dashboard UX (future)
- "Remember me" / persistent session (currently expires on browser close)
- Password change route in settings

---

## Gotchas & Things to Know

- **DB transaction types are `Needs`, `Wants`, `Business`, `Savings`** — never `Expense`/`Income`
- **Flutter `lib/` is gitignored** — Dart files live locally on dev machine only, not in GitHub
- **Local desktop app has no auth** — env vars are empty locally, all auth is bypassed
- **Railway auto-detects `RAILWAY_ENVIRONMENT`** — launcher uses this to pick `ProductionConfig` and run as plain HTTP server
- **CORS manual handler** — Flask-CORS was replaced because v4.x reflected non-matching origins; manual `after_request` in `app.py` is strict
- **Session expiry is server-enforced** — checks `login_time` on every request, not just cookie expiry
- **Mobile token is permanent** — no expiry on the Flutter Bearer token, cleared only by explicit logout
- **`due_date` on debts** — stored as integer in DB (day of month), parsed with `.toString()` in Flutter
