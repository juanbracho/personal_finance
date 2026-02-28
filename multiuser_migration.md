# Multi-User Migration Plan
*Finance Dashboard — drafted February 2026*

---

## Goal

Migrate the app from a single-user household tool to a proper multi-user system with real account isolation and security hardening. Immediate use case: add one second user. Architecture decisions made with future scaling in mind.

**Owners (Cacas, Cata, Suricata) are household-specific** — they belong to Juan's account only. New users define their own household members from scratch. Owners become a proper DB-backed table per user, not hardcoded strings.

---

## Cost Impact

| Service | Current | After |
|---------|---------|-------|
| Railway (Flask) | $5/month | $5/month |
| Database | SQLite on Railway volume | Neon free tier (PostgreSQL) |
| Rate limiting | — | Flask-Limiter in-memory (free) |
| **Total** | **$5/month** | **$5/month** |

Neon free tier: 0.5 GB storage, always-on, encrypted at rest. Current DB is 1.1 MB — well within limits.

---

## What Changes, Layer by Layer

### 1. Database

**New tables:**

| Table | Purpose |
|-------|---------|
| `users` | Accounts with hashed passwords, role (admin/member), is_active flag |
| `user_owners` | Household members per user (replaces hardcoded owner strings) |
| `category_seeds` | Universal default categories applied to every new account |
| `audit_logs` | Auth events + destructive actions |
| `revoked_tokens` | JWT blocklist for logout invalidation |

**Changes to existing tables:**

Every table gets a `user_id` INTEGER foreign key referencing `users.id`:
- `transactions`
- `budget_templates`
- `budget_subcategory_templates`
- `monthly_budgets`
- `unexpected_expenses`
- `debt_accounts`
- `debt_payments`
- `budget_commitments`

**Unique constraints that need `user_id` added:**

| Table | Current constraint | Fixed constraint |
|-------|--------------------|-----------------|
| `budget_templates` | `UNIQUE(category)` | `UNIQUE(category, user_id)` |
| `monthly_budgets` | `UNIQUE(category, month, year)` | `UNIQUE(category, month, year, user_id)` |
| `budget_subcategory_templates` | `UNIQUE(category, sub_category)` | `UNIQUE(category, sub_category, user_id)` |
| `unexpected_expenses` | `UNIQUE(category, month, year, description)` | `UNIQUE(category, month, year, description, user_id)` |

**Data migration:**
- Create Juan's account as `user_id = 1`, role = `admin`
- `UPDATE` all existing rows across all tables to set `user_id = 1`
- Extract distinct `owner` values from existing transactions (`Cacas`, `Cata`, `Suricata`) and insert them into `user_owners` for `user_id = 1` — no manual work needed
- No data is lost — everything is preserved under the existing account

---

### 2. Owners & Categories Per User

**Owners — `user_owners` table**

`owner` is currently a freeform string on `transactions` and `debt_accounts`. It works for one household but has no backing table, no management UI, and no isolation. The fix:

- New `user_owners` table: `id`, `user_id`, `name`, `is_active`
- `Transaction.owner` and `DebtAccount.owner` remain as strings (no FK constraint needed — keeps imports simple) but the app now reads available owners from `user_owners` filtered by `user_id`
- Juan's migration: auto-populated from distinct values in existing data → `Cacas`, `Cata`, `Suricata` created automatically for `user_id = 1`
- New users: start with zero owners, define their own during onboarding

**Categories — two-tier system**

| Tier | What | Who gets it |
|------|------|-------------|
| Universal seed | Groceries, Utilities, Housing, Transportation, Health, Entertainment, Savings | Every new account automatically |
| User-defined | Everything else (Venezuela expenses, custom subcategories, etc.) | Built by each user over time |

Seeds are stored in a `category_seeds` table (admin-managed) and copied into `budget_templates` for `user_id` on account creation. Users can delete, rename, or add to them freely — the seed is just a starting point, not locked.

Juan's existing categories are untouched — they were already user-specific and get migrated as-is.

**New user onboarding flow**

Two steps shown once after first login:

1. **Define household members** — "Who's in your household?" → creates rows in `user_owners`. Can be just themselves or multiple people.
2. **Categories confirmed** — "We've set up some basic categories to get you started. You can edit or remove them anytime." → no input needed, seeds already applied.

---

### 3. Authentication

**What gets replaced:**

| Current | Replacement |
|---------|-------------|
| `DASHBOARD_USERNAME` / `DASHBOARD_PASSWORD` env vars | `users` table with hashed passwords |
| Single shared `API_SECRET_KEY` env var | JWT token issued per user at login |
| `session['logged_in'] = True` | `session['user_id'] = <id>` |

**How it works after migration:**

1. User POSTs username + password to `/api/login`
2. Server verifies against hashed password in DB
3. Server returns a signed JWT containing `user_id` and expiry (1 hour)
4. Client stores JWT (Flutter: secure storage, Web: session cookie)
5. Every subsequent request sends `Authorization: Bearer <jwt>`
6. Server decodes JWT → extracts `user_id` → scopes all queries to that user
7. On logout → JWT is added to `revoked_tokens` table → immediately invalid

**Security properties:**
- Passwords stored as pbkdf2 hashes (werkzeug, already a dependency — no new package)
- JWT signed with `JWT_SECRET_KEY` — if rotated, all sessions invalidate globally
- Tokens expire after 1 hour — relogin required
- Logout is real — revoked tokens are checked on every request

---

### 4. Security Hardening

**Rate limiting**
- Max 5 login attempts per minute per IP
- Implemented with Flask-Limiter using in-memory storage
- No Redis required — in-memory is sufficient for this scale

**Session cookies (web UI)**
- `HttpOnly` — JavaScript cannot read the cookie (XSS protection)
- `Secure` — only sent over HTTPS
- `SameSite=Strict` — not sent on cross-site requests (CSRF protection)

**Role system**

| Role | Permissions |
|------|-------------|
| `admin` | Full access, user management, full DB download |
| `member` | Own data only, personal export only |

**Audit logging**

Events logged to `audit_logs` table:

| Category | Events |
|----------|--------|
| Auth | Login success, login failure, logout, password change |
| Destructive | Transaction delete, debt account delete |

Each log entry records: `user_id`, `action`, `ip_address`, `timestamp`, optional `metadata`.

**Data export**

| Endpoint | Who | What |
|----------|-----|------|
| `/settings/export-my-data` | All users | JSON of their own rows across all tables |
| `/settings/download-database` | Admin only | Full raw database file |

---

### 5. Backend Routes

**New helper — `current_user_id()`**

A single utility function that reads `user_id` from the decoded JWT (API routes) or session (web routes). Every blueprint calls this — no user_id logic duplicated across routes.

**Every query gets scoped:**
- All `SELECT` queries: add `WHERE user_id = current_user_id()`
- All `INSERT` queries: set `user_id = current_user_id()`
- All `UPDATE`/`DELETE` queries: add `WHERE user_id = current_user_id()` to prevent cross-user writes

**New endpoints:**

| Method | Endpoint | Access | Purpose |
|--------|----------|--------|---------|
| POST | `/api/login` | Public | Returns JWT on valid credentials |
| GET | `/settings/export-my-data` | Member+ | User-scoped JSON export |
| GET | `/admin/users` | Admin | List all users |
| POST | `/admin/users/create` | Admin | Create a new user account |
| POST | `/admin/users/deactivate` | Admin | Deactivate a user |

---

### 6. Railway Environment Variables

**Remove:**
- `DASHBOARD_USERNAME`
- `DASHBOARD_PASSWORD`
- `API_SECRET_KEY`

**Add:**
- `JWT_SECRET_KEY` — long random string, used to sign all JWTs

**Keep:**
- `SECRET_KEY` — Flask session signing (unchanged)
- `CORS_ORIGINS` — unchanged
- `DATABASE_URL` — will be auto-overwritten by Neon connection string

**JWT_SECRET_KEY rotation runbook:**
If the key is ever suspected leaked (committed to git, Railway access shared with someone who leaves, etc.):
1. Generate a new key: `openssl rand -hex 32`
2. Update `JWT_SECRET_KEY` in Railway env vars
3. Redeploy
4. All active sessions across all users are immediately invalidated — everyone is forced to log in again
5. This is the correct and intended behavior in a breach scenario

---

### 7. Flutter Mobile App

Minimal changes required. The app is already architected correctly.

| Thing | Changes? |
|-------|----------|
| Login screen | None — already exists |
| Token storage | None — already uses secure storage |
| Bearer header format | None — `Authorization: Bearer <token>` is identical |
| API endpoints | None — same URLs, same responses |
| Data displayed | None — just scoped to the logged-in user (same data as before for Juan) |

**One addition:** Handle `401` responses gracefully — detect an expired token and redirect to the login screen automatically instead of showing a generic error.

---

## Implementation Phases

### Phase 1 — Database Migration
1. Set up Neon free tier PostgreSQL instance
2. Write migration script: create `users`, `user_owners`, `category_seeds`, `audit_logs`, `revoked_tokens` tables
3. Add `user_id` column to all existing tables
4. Fix unique constraints
5. Insert Juan as `user_id = 1`, role = `admin`
6. Backfill all existing rows with `user_id = 1`
7. Extract distinct owner values from existing transactions → seed `user_owners` for `user_id = 1`
8. Populate `category_seeds` with universal defaults
9. Verify row counts match pre-migration

### Phase 2 — Auth Overhaul
1. Install PyJWT (new dependency)
2. Rewrite `auth.py` — replace env-var credential check with DB lookup + JWT issuance
3. Add `current_user_id()` helper to `utils.py`
4. Update session handling to store `user_id`
5. Wire JWT blocklist check on every request
6. Update Railway env vars

### Phase 3 — Route Scoping
1. Update every blueprint query to scope by `user_id`
2. Update all INSERT operations to tag with `user_id`
3. Add rate limiting to login endpoint
4. Harden session cookie config

### Phase 4 — New Features
1. Audit logging middleware
2. `/settings/export-my-data` endpoint
3. Lock down `/settings/download-database` to admin
4. `/admin/users` CRUD (create, list, deactivate)
5. Owner management UI (list, add, deactivate owners per user)

### Phase 5 — New User Onboarding Flow
1. Detect first login (no entries in `user_owners` for that user)
2. Show "Define your household members" step → creates `user_owners` rows
3. Auto-apply `category_seeds` to new account on creation
4. Show confirmation screen: "Your basic categories are ready"
5. Redirect to dashboard

### Phase 6 — Flutter Update
1. Update API service to handle JWT (same bearer format, just new token source)
2. Add 401 → redirect to login handling
3. Test login flow end to end on device

---

## Files That Will Change

| File | Change |
|------|--------|
| `Desktop/models.py` | Add User, UserOwner, CategorySeed, AuditLog, RevokedToken models; add user_id to all models |
| `Desktop/auth.py` | Full rewrite — DB-backed auth, JWT issuance, blocklist check |
| `Desktop/utils.py` | Add `current_user_id()` helper |
| `Desktop/config.py` | Add JWT_SECRET_KEY, secure cookie config, remove old credential vars |
| `Desktop/app.py` | Wire rate limiter, updated before_request hooks |
| `Desktop/blueprints/*/routes.py` | All blueprints — scope queries to user_id |
| `Desktop/blueprints/settings/routes.py` | Split export: admin full dump vs user personal export |
| `Desktop/blueprints/api/routes.py` | New /api/login JWT flow, 401 handling |
| `Mobile/.../api_service.dart` | Handle 401 → re-login redirect |
| Railway env vars | Remove 3 vars, add JWT_SECRET_KEY |

**New files:**
- `Desktop/blueprints/admin/routes.py` — user management routes
- `Desktop/blueprints/onboarding/routes.py` — new user onboarding flow
- `Desktop/migrations/001_multiuser.sql` — migration script
- `Desktop/seeds/categories.py` — universal category seed data

---

## What Does NOT Change

- Flask blueprint structure
- All existing API endpoint URLs
- Juan's owners (Cacas, Cata, Suricata) — migrated automatically, no manual work
- Juan's categories and subcategories — migrated as-is, untouched
- Flutter screens and UI
- Railway deployment setup
- Desktop app local mode (empty env vars still bypasses auth)
- Monthly cost ($5/month)
