# Kanso — Web Dashboard Redesign Tracker
*Started: February 21, 2026 · Completed: February 22, 2026*

---

## What This File Is

Session-by-session tracker for the web dashboard redesign.
The backend is complete and stable. This file covers the web layer (Flask + HTML/CSS/JS).

**Status: COMPLETE ✓** — All pages redesigned. All known bugs fixed. App is stable.

---

## Core Decisions (Locked)

| Decision | Choice |
|---|---|
| Brand name | **Kanso** (renamed from "Personal Finance") |
| Tagline | **"Mindful money tracking"** |
| Logo | Static SVG file served from `static/img/kanso-icon.svg` used as `<img>` in navbar |
| Theme system | 3-way cycle: **Warm Ink** (dark) → **Indigo** (dark) → **Washi Paper** (light) |
| Theme toggle | 3-button pill in navbar top-right, persistent via `localStorage` |
| Default theme | Warm Ink |
| CSS approach | New `kanso.css` design system alongside Bootstrap (Bootstrap kept for grid/JS only) |
| Page width | Narrow (settings, forms): max 860px · Wide (dashboard, analytics, transactions, debts): max 1120px |
| List pattern | Expandable rows: collapsed = key info only · expanded = full details (Debts, Transactions) |
| Form pages | Separate pages (not modals) for Add Debt, Add Transaction, Bulk Transaction |

---

## Design System — `kanso.css`

Full CSS variable system for all 3 themes. Variables defined on `[data-theme]` attribute on `<html>`.

**Key tokens:**
- `--bg` / `--surface` / `--surface-raised` / `--surface-hover`
- `--border` / `--border-subtle`
- `--primary` / `--primary-dim` / `--primary-hover`
- `--text` / `--text-muted` / `--text-faint`
- `--needs` / `--wants` / `--business` / `--savings` / `--unexpected`
- `--danger` / `--success` / `--warning` (+ `-dim` variants)
- `--nav-bg` / `--nav-border`

**Components defined:**
- `.kanso-nav` — sticky top nav
- `.kanso-card` + `.kanso-row` — content rows with icon / label / action
- `.kanso-info-strip` / `.kanso-info-item` / `.kanso-info-label` / `.kanso-info-value` — horizontal status bar
- `.kanso-section` + `.kanso-section-label` — section grouping
- `.kanso-danger-card` — danger zone with red border
- `.backup-list` / `.backup-item` — backup history
- `.theme-picker` / `.theme-option` — settings theme selector
- `.btn-kanso` variants: primary / ghost / danger / danger-solid / sm
- `.kanso-input` — text/number/date inputs
- `.kanso-select` — styled select with custom chevron arrow
- `.kanso-input-group` / `.kanso-input-affix` — prefix/suffix wrappers ($ / %)
- `.kanso-form-label` / `.kanso-form-hint` — field labels and helper text
- `.kanso-form-grid` — 2-col form grid
- `.kanso-form-section` — uppercase section label inside cards (primary color)
- `.kanso-tip-box` / `.kanso-note-box` — themed callout boxes
- `.kanso-file-label` — file input styling
- `.kanso-feedback` — inline success/error/info messages
- `.kanso-flash` — page-level flash alerts
- `.kanso-progress-wrap` / `.kanso-progress-bar` — progress bar
- `.theme-toggle` + `.theme-btn` — navbar theme switcher
- `.kanso-modal` — Bootstrap modal override (all themed, `.modal-section-label`, `.modal-balance-strip`)
- `.kanso-badge` variants — typed badges (payment/charge/type)
- `.debt-list` / `.debt-item` / `.debt-item-main` / `.debt-item-details` — debt expandable rows
- `.debt-progress-mini-*` / `.debt-progress-full-*` — progress bars inside debt rows
- `.debt-action-btn` / `.debt-expand-btn` — icon action + chevron buttons
- `.debt-type-badge` / `.debt-paid-badge` — inline badges
- `.history-summary-strip` / `.history-toggle-btn` — payment history modal strip
- `.debt-header-toggle` — toggle checkbox in card header
- `.txn-list` / `.txn-item` / `.txn-item-main` / `.txn-item-details` — transaction expandable rows
- `.txn-date` / `.txn-desc` / `.txn-amount` / `.txn-type` / `.txn-actions` — row slots
- `.txn-type-badge` + `.txn-type-needs/wants/savings/business` — color pill badges
- `.txn-expand-btn` — chevron expand button with `.open` rotation
- `.txn-detail-label` / `.txn-detail-value` — 4-col detail grid cells
- `.txn-income-badge` / `.txn-expense-badge` — small inline pills
- `.kanso-pagination` — centered pill pagination with `.active` / `.disabled`
- `.bulk-item-row` — flex row for bulk transaction inputs
- `.kanso-input.is-invalid` — red border validation hook
- `.dsh-tab-nav` / `.dsh-tab-btn` — dashboard outer view switcher (server-side `<a>` links)
- `.dsh-stat-grid` / `.dsh-stat-item` / `.dsh-stat-value` / `.dsh-stat-label` / `.dsh-stat-sub` — 4-col stat grid
- `.dsh-recent-list` / `.dsh-recent-item` / `.dsh-recent-meta` / `.dsh-recent-amount` — recent transactions list
- `.dsh-perf-grid` / `.dsh-perf-item` / `.dsh-perf-value` / `.dsh-perf-label` — budget performance 3-col
- `.dsh-budget-progress` — budget utilization bar wrapper
- `.dsh-budget-row` / `.dsh-subcat-row` / `.dsh-txn-row` — budget table row hierarchy
- `.anl-table` / `.anl-positive` / `.anl-negative` / `.anl-neutral` — mirrored in dashboard.css and budget.css

---

## Redesign Status

| # | Page | Status |
|---|---|---|
| 0 | Design System + Base Layout | ✓ Done |
| 1 | Settings | ✓ Done |
| 2 | Debts | ✓ Done |
| 3 | Add Debt Account | ✓ Done |
| 4 | Transactions + Add + Bulk | ✓ Done |
| 5 | Dashboard (all 3 views) | ✓ Done |
| 6 | Budget | ✓ Done |
| 7 | Analytics | ✓ Done |
| 8 | Login Page | — Skipped (not needed for current usage) |

---

## Page Notes

### Settings `[x]`
- Status strip: version · DB status · size · last modified
- Appearance: 3 `.theme-option` cards with color swatches
- Data Management: 3 `.kanso-row` rows (Export / Import / Create Backup)
- Backup History: `.backup-list` / `.backup-item`
- Danger Zone: `.kanso-danger-card`, type-to-confirm input
- **Cloud notice:** `.kanso-tip-box` warning added — Export/Import are the only safe flows on Railway (ephemeral filesystem). Local backup rows work only for self-hosted installs unless a Railway Volume is mounted at `data/`.

### Debts `[x]`
- Info strip: Total Debt + Monthly Minimums
- Expandable debt list: collapsed = name/last4/type/owner/balance/mini-progress/min-payment; expanded = full detail
- Charts: 2-col — By Type + By Owner (Plotly, theme-aware)
- Insights: 3-col — Highest Balance / Lowest Rate / Highest Rate
- 3 modals: Payment, Edit, History

### Add Debt Account `[x]`
- 3 kanso-card sections: Basic Info, Financial Details, Payment & Category
- 2-col layout: form (col-md-8) + help sidebar (col-md-4)

### Transactions `[x]`
- Expandable card list; per-page selector (25/50/100/150/200/250); kanso pagination; kanso-modal edit
- Add Transaction: 4 sections (Transaction Info, Categorization, Account & Owner, Credit Purchase) + sidebar (Quick Actions + Tips)
- Bulk Transaction: Common Fields card + Transaction Items card (flex list, not a table)
- Type dropdown is **dynamic** — populated from DB (`transactions` table + `custom_types` table), not hardcoded
- "+ Add new type" button on Add Transaction form — calls `POST /api/categories/types`, adds option to select

### Dashboard `[x]`
- **3 views** (Overview / Budget / Categories) via server-side `<a>` links styled as `.dsh-tab-nav`
- **Filters:** Year + Month + Owner selects in a `kanso-info-strip` filter bar; Overview and Budget submit via form; Categories view uses JS-driven AJAX (no page reload)
- **Overview view:** info strip (4 items) · stat grid (4 cols) · 3 charts (Plotly donut/h-bar/line) · 2-col tables (Spending Breakdown + Owner Comparison) · Recent Transactions list · Budget Performance 3-col
- **Budget view:** info strip · budget utilization progress bar · full budget table (category → subcategory → transaction drill-down with AJAX) · 2 charts · Insights card
- **Categories view:** 5 inner tabs — Categories / Sub-Categories / Owners / Accounts / **Types** — with Bootstrap tab JS for switching; each tab has Add/Edit/Delete with migration support; `anl-table` for data display
- **Types tab:** shows Needs/Wants/Savings/Business + any custom types; "Add Type" creates in `custom_types` SQLite table (persists types with 0 transactions)
- Charts: Plotly with `CHART_COLORS` theme-aware object keyed by `document.documentElement.dataset.theme`
- `dashboard.css`: all `.dsh-*` classes + `.anl-table` mirror; `dashboard.js`: theme-aware chart rendering, AJAX category/type management

### Budget `[x]`
- Custom `.bgt-tab-nav` / `.bgt-tab-btn` replaces Bootstrap nav-tabs
- `budget.css`: broken CSS vars fixed, bgt-* + anl-table added
- `budget_v2.js`: 7 patches — tab listener, renderSubcategoryBudgets, renderCommitments, renderUnexpectedExpenses, table sort colors, showToast, chart colors, createHiddenBudgetsModal, renderHiddenBudgets
- Commitment summary tables: `display:grid; grid-template-columns:1fr 1fr` edge-to-edge
- Collapse-all / Expand-all: SVG-only icon buttons using Bootstrap Collapse API

### Analytics `[x]`
- `analytics.css` migrated to CSS variable tokens
- `analytics.html` full rewrite: kanso-page-wide, kanso-card panels, kanso buttons, kanso-modal for both modals
- `analytics.js`: action buttons → `debt-action-btn`; matrix table → `anl-table`; pct-change → `anl-positive/negative/neutral`
- Type filter is **dynamic** — `available_types` from backend, not hardcoded

---

## Data / Backend Changes Made

These were required to support dynamic types and are the only backend changes made during the redesign:

### `custom_types` table
```sql
CREATE TABLE IF NOT EXISTS custom_types (name TEXT PRIMARY KEY, created_at TEXT NOT NULL)
```
Created lazily in each route that needs it. Stores user-defined types that have 0 transactions (so they appear in dropdowns before any transactions use them).

### API endpoints added (`blueprints/api/routes.py`)
- `GET /api/categories/types` — returns merged list of types from transactions + custom_types, with stats; accepts `owner`, `year` filters
- `POST /api/categories/types` — adds a new custom type
- `PUT /api/categories/types/<name>` — renames a type (in both transactions + custom_types)
- `DELETE /api/categories/types/<name>` — deletes only if 0 transactions; errors otherwise
- All category/subcategory/type/statistics endpoints accept `owner` filter param

### `transactions/routes.py` changes
- `list_transactions`, `add_transaction`, `bulk_transaction` GET: build `types` list from DB and pass to template
- Deduplication uses a `seen` set — not just `if t not in _defaults`

### `analytics/routes.py` changes
- `analytics_dashboard` GET: builds `available_types` from DB with same deduplication

---

## Gotchas to Carry Forward

- Bootstrap CSS still loaded for grid compatibility — `kanso.css` overrides visual styles on top
- Bootstrap modal JS still used for show/hide/backdrop — HTML uses `class="modal fade"` + `kanso-modal` on `.modal-dialog`
- `setTheme()` is defined in `base.html` — do NOT redefine in page `extra_js` blocks (causes infinite recursion)
- Theme is applied on `<html>` via `data-theme`; all CSS variables cascade from there
- Flash messages use Jinja2 categories: `success`, `error`, `info`, `warning`
- `kanso-page` (max 860px) vs `kanso-page-wide` (max 1120px) — use wide for data-heavy pages
- Page-specific CSS uses `{% block extra_css %}` — kanso.css is the base layer only
- Plotly: CSS variables don't work inside canvas — read `document.documentElement.dataset.theme` at render time, map to explicit hex values via `CHART_COLORS` object
- `kanso-info-strip` children must be `kanso-info-item` (not `kanso-info-strip-item`); label = `kanso-info-label`; value = `kanso-info-value`
- `anl-table` is defined in `analytics.css` — pages not loading analytics.css must mirror it in their own CSS (done in budget.css and dashboard.css)
- JS-generated modals need `kanso-modal` on `.modal-dialog`, not `.modal` wrapper
- Bootstrap `.text-primary` in JS-rendered HTML gives Bootstrap blue — use `style="color:var(--primary)"` instead
- `data-*` attributes on list items bridge HTML and JS — always add them for dynamically updated lists
- `kanso-select` uses background-image SVG arrow with hardcoded hex color — acceptable tradeoff
- Type strings (exact, locked for existing data): `Needs` / `Wants` / `Business` / `Savings`; custom types stored in `custom_types` table
- Type colors: `--needs` (green) / `--wants` (orange) / `--business` (blue) / `--savings` (purple) / `--unexpected` (warning yellow)
- SVG logo is 525KB — always `<img>` tag, never inline
- Dashboard categories view: Year/Month/Owner filters are JS-only (no form submit) — they drive `loadCategoriesManagement()` AJAX calls; form submit only applies to Overview and Budget views
- Inline `<script>` blocks in `{% block content %}` run BEFORE `{% block extra_js %}` JS files — don't put render function overrides in inline scripts if the same function exists in an external JS file (it will get clobbered)
- Railway deployment: `data/` folder resets on container restart unless a Railway Volume is mounted at `data/` — Export Database (browser download) and Import Database are the only safe backup flows
- Type deduplication: always use a `seen` set when building types_list — `if t not in _defaults` alone is insufficient if a type exists in both `transactions` and `custom_types`

---

## Session Log

| Date | What Was Built |
|---|---|
| Feb 21, 2026 | `kanso.css` design system — full token system + all base components |
| Feb 21, 2026 | `base.html` — Kanso nav, static SVG icon, 3-theme toggle, flash messages, footer |
| Feb 21, 2026 | Settings page — status strip, theme picker, data management rows, backup list, danger zone |
| Feb 21, 2026 | Debts page — expandable card list, info strip, charts, 3 modals, debts.js updated |
| Feb 21, 2026 | Add Debt Account page — Kanso form, 3 sections, help sidebar, new form CSS components |
| Feb 22, 2026 | Transactions page — expandable card list, per-page selector, kanso pagination, kanso-modal edit |
| Feb 22, 2026 | Add Transaction + Bulk Transaction pages — Kanso form redesign, bulk items as flex list |
| Feb 22, 2026 | transactions.js + bulk_transactions.js — DOM selector fixes, toggleTxnDetails, kanso class names |
| Feb 22, 2026 | Analytics page — analytics.css CSS-var migration; analytics.html full rewrite; analytics.js patches |
| Feb 22, 2026 | Budget page — budget.css overhauled; budget_management.html full rewrite; budget_v2.js 7 patches |
| Feb 22, 2026 | Dashboard — enhanced_dashboard.html wrapper + 3 sub-templates (overview/budget/categories); dashboard.css; dashboard.js theme-aware charts |
| Feb 22, 2026 | Dashboard bug fixes — Bootstrap tab active-class sync; categories view filter wiring; render function placement (inline vs external JS) |
| Feb 22, 2026 | Categories view — all 3 filters (Year/Month/Owner) JS-driven; Types tab added (5th tab) with full CRUD + migration support |
| Feb 22, 2026 | `custom_types` table + API endpoints — POST/PUT/DELETE for type management; owner filter on all category API endpoints |
| Feb 22, 2026 | Dynamic type dropdowns — all type selects (Transactions, Add Transaction, Bulk, Analytics) now DB-driven instead of hardcoded |
| Feb 22, 2026 | "+ Add new type" button on Add Transaction form — wired to `addNewType()` in transactions.js → POST /api/categories/types |
| Feb 22, 2026 | Deduplication fix — type list building changed to `seen` set in all 4 routes (add_transaction, list_transactions, bulk_transaction, analytics_dashboard) |
| Feb 22, 2026 | Settings — Railway/cloud hosting notice added |
