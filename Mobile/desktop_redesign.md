# Kanso — Web Dashboard Redesign Tracker
*Started: February 21, 2026*

---

## What This File Is

Session-by-session tracker for the web dashboard redesign.
One page (or system) gets redesigned per session. Nothing gets coded until understood and approved here first.

The backend is complete and stable. This file is web-only (Flask + HTML/CSS/JS).

---

## Core Decisions (Locked)

| Decision | Choice |
|---|---|
| Brand name | **Kanso** (renamed from "Personal Finance") |
| Tagline | **"Mindful money tracking"** |
| Logo | Static SVG file served from `static/img/kanso-icon.svg` used as `<img>` in navbar |
| Theme system | Same 3-way cycle as mobile: **Warm Ink** (dark) → **Indigo** (dark) → **Washi Paper** (light) |
| Theme toggle | 3-button pill in navbar top-right, persistent via `localStorage` |
| Default theme | Warm Ink |
| CSS approach | New `kanso.css` design system alongside Bootstrap (Bootstrap kept for grid/JS only) |
| Page width | Narrow pages (settings, forms): max 860px · Wide pages (dashboard, analytics, transactions, debts): max 1120px |
| List pattern | Expandable rows: collapsed = key info only · expanded = full details (used in Debts, Transactions) |
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
- `.btn-kanso` variants: primary / ghost / danger / danger-solid
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

---

## Redesign Backlog

Status: `[ ]` pending · `[~]` in progress · `[x]` done

---

### 0. Design System + Base Layout  `[x]`

- `kanso.css` — full token system, all components listed above
- `base.html` — Kanso navbar (static SVG icon + wordmark), 3-theme toggle, nav links, footer
- Theme applied via `data-theme` on `<html>`, saved to `localStorage`, applied before first paint (no flash)
- `setTheme()` defined globally in `base.html` — syncs nav toggle AND settings picker cards

---

### 1. Settings Page  `[x]`

**After:**
- Status strip at top: version · DB status (dot indicator) · size · last modified
- Appearance: 3 `.theme-option` cards with color swatches, `data-theme-pick` attribute
- Data Management: 3 `.kanso-row` rows (Export / Import / Create Backup) with SVG icons
- Backup History: `.backup-list` / `.backup-item` with monospace filenames
- Updates section: removed from UI (backend routes preserved)
- Danger Zone: `.kanso-danger-card`, type-to-confirm input

---

### 2. Debts Page  `[x]`

**After:**
- Info strip: 2 items — Total Debt (`#totalDebtValue`) + Monthly Minimums (`#totalMinimumsValue`)
- Debt list: `<ul class="debt-list">` / `<li class="debt-item">` with `data-*` attributes
  - Collapsed: name + last4 + type badge | owner | balance | mini progress bar | min payment | expand + edit + delete
  - Expanded (`#debt-details-{id}`): Original Balance, Interest Rate, Amount Paid, full progress bar
- Charts: 2-col grid — By Type + By Owner (Plotly, theme-aware via `document.documentElement.dataset.theme`)
- Insights: 3-col — Highest Balance, Lowest Rate, Highest Rate
- 3 modals: Payment, Edit, History — all use `class="modal fade kanso-modal"`
- `debts.js` updated: `data-*` selectors, `toggleDebtDetails()`, `updateDebtSummaryCards()`, theme-aware charts, Kanso toast notifications

---

### 3. Add Debt Account Page  `[x]`

**After:**
- 3 `kanso-card` sections: Basic Info, Financial Details, Payment & Category
- 2-col layout: form (col-md-8) + help sidebar (col-md-4)
- `kanso-input` / `kanso-select` / `kanso-input-group` throughout
- Help sidebar: `.kanso-tip-box` + `.kanso-note-box`
- All JS logic preserved (balance validation, interest % → decimal, category auto-suggest)

---

### 4. Transactions  `[x]`

**After:**
- `transactions.html` — expandable card list (`txn-list` / `txn-item`): collapsed shows date + desc + amount + type badge + edit/delete/chevron; expanded shows 4-col detail grid (category, sub-category, owner, account). `kanso-pagination` replaces Bootstrap pagination. `kanso-modal` edit modal with `modal-section-label` sections. Empty state as centered `kanso-card`.
- `add_transaction.html` — 4 `kanso-card` sections: Transaction Information (date + amount + description), Categorization (category + sub-category + type), Account & Owner, Credit Purchase (toggle + `kanso-note-box`). Sidebar: Quick Actions card (`#quickActionsContainer` preserved) + Tips card with template buttons.
- `bulk_transaction.html` — Common Fields card (3-col: category/sub/type + 2-col: account/owner). Transaction Items card with column header row + flex list (`id="itemsTableBody"` preserved, not a `<table>`). Summary strip preserved (`#summarySection`, `#itemCount`, `#totalAmount`).
- `transactions.js` — `deleteTransaction()` selector changed from `button+tr` to `.txn-item[data-txn-id]`. Added `toggleTxnDetails()` + `window.toggleTxnDetails` export.
- `bulk_transactions.js` — `addRow()` generates `<div class="bulk-item-row">` with `kanso-input` / `kanso-input-group` / `kanso-input-affix` / `debt-action-btn delete` SVG button. `updateTotals()` class names → `txn-amount income/expense`.
- `kanso.css` — appended: transaction list, pagination, bulk row, `.kanso-input.is-invalid`.
- `transactions/routes.py` — `per_page` query param (allowed: 25/50/100/150/200/250, default 50) passed to template; both render_template calls updated.
- `transactions.html` — per-page `<select>` in info strip (3rd item); all pagination links include `per_page=per_page`.

---

### 5. Dashboard (Overview)  `[ ]`

TBD

---

### 6. Budget  `[x]`

**Decisions:**
- Design-only pass — no data or logic changes
- Keep Bootstrap collapse for subcategory groups; keep Bootstrap modal JS
- Custom `.bgt-tab-nav` / `.bgt-tab-btn` replace Bootstrap nav-tabs
- `budget.css` keeps page-specific styles; `.bgt-*` + mirrored `.anl-table` classes added here (analytics.css not loaded on budget page)
- `budget_v2.js` patched in 7 targeted places + follow-up fixes in same session
- Commitment summary tables go edge-to-edge (CSS grid 1fr 1fr, no Bootstrap row/col gutter)
- Hidden Budget Items modal is JS-generated — both `createHiddenBudgetsModal()` and `renderHiddenBudgets()` patched
- Category-level budgeting info box removed entirely (looked off between rows)
- Collapse-all / Expand-all: two SVG-only icon buttons in subcategory panel header using Bootstrap Collapse API

**Files involved:**
- `budget.css` — broken CSS vars fixed; hardcoded colors replaced; modal-header gradient removed; all `.bgt-*` component classes added; `.anl-table` + `.anl-positive/negative/neutral` + `.anl-info-box` mirrored from analytics.css
- `budget_management.html` — full rewrite: kanso-page-wide, `kanso-info-item` info strip (4 items), single kanso-card with bgt-tab-nav + 3 panels, 3 kanso-modals; commitment summaries restructured edge-to-edge; collapse/expand all SVG buttons added
- `budget_v2.js` — tab listener removed; renderSubcategoryBudgets → bgt classes; renderCommitments → bgt-commitment-item; renderUnexpectedExpenses → debt-action-btn (flex-wrapped); table sort functions → inline CSS var colors (no Bootstrap text-primary/text-end); showToast → bgt-toast; chart colors theme-aware; createHiddenBudgetsModal + renderHiddenBudgets → kanso-modal + Kanso rows; category info box removed

---

### 7. Analytics  `[x]`

**Decisions:**
- Keep `analytics.css` as a separate file (not folded into kanso.css)
- Migrate all hardcoded colors in `analytics.css` → CSS variable tokens from kanso.css
- Design-only pass — no data insight changes
- Keep filtered transactions table + bulk edit (useful for finding and correcting old records)
- Keep counts in category/subcategory tables (count + avg reveal purchase pattern vs. total)

**Files involved:**
- `analytics.css` — CSS variable migration; add `.anl-table`, `.anl-positive/negative/neutral` utilities
- `analytics.html` — full rewrite: kanso-page-wide, kanso-card panels, kanso buttons, kanso-modal for both modals, kanso-info-strip for summary stats
- `analytics.js` — targeted: action buttons in filtered table → `debt-action-btn`; matrix table class → `anl-table`; pct-change classes → `anl-positive/negative/neutral`

---

### 8. Login Page  `[ ]`

TBD

---

## Session Log

| Date | What Was Built |
|---|---|
| Feb 21, 2026 | `kanso.css` design system — full token system + all base components |
| Feb 21, 2026 | `base.html` — Kanso nav, static SVG icon, 3-theme toggle, flash messages, footer |
| Feb 21, 2026 | Settings page — status strip, theme picker, data management rows, backup list, danger zone |
| Feb 21, 2026 | Debts page — expandable card list, 2 info cards, charts, 3 styled modals, debts.js updated |
| Feb 21, 2026 | Add Debt Account page — Kanso form with 3 sections, help sidebar, new form CSS components |
| Feb 22, 2026 | Transactions page — expandable card list, per-page selector (25–250), kanso pagination, kanso-modal edit |
| Feb 22, 2026 | Add Transaction + Bulk Transaction pages — Kanso form redesign, bulk items as flex list |
| Feb 22, 2026 | transactions.js + bulk_transactions.js — DOM selector fixes, toggleTxnDetails, kanso class names |
| Feb 22, 2026 | Analytics page — analytics.css CSS-var migration; analytics.html full rewrite; analytics.js action-btn + anl-table patches |
| Feb 22, 2026 | Budget page — budget.css overhauled (broken vars fixed, bgt-* + anl-table added); budget_management.html full rewrite; budget_v2.js 7 patches + follow-ups (info strip class names, edge-to-edge commitment tables, flex action buttons, hidden-budgets modal, collapse/expand all) |

---

## Gotchas to Carry Forward

- Bootstrap CSS is still loaded for grid compatibility — `kanso.css` overrides visual styles on top
- Bootstrap modal JS still used for show/hide/backdrop — HTML uses `class="modal fade kanso-modal"`
- `setTheme()` is defined in `base.html` — do NOT redefine it in page `extra_js` blocks (causes infinite recursion via hoisting)
- Theme is applied on `<html>` via `data-theme` attribute; all CSS variables cascade from there
- Flash messages use Jinja2 categories: `success`, `error`, `info`, `warning`
- `kanso-page` (max 860px) vs `kanso-page-wide` (max 1120px) — use wide for data-heavy pages
- Page-specific CSS should still use `{% block extra_css %}` — kanso.css is the base layer only
- Plotly/Chart.js: CSS variables don't work inside canvas-rendered charts — read `document.documentElement.dataset.theme` at render time and map to explicit color values
- `kanso-info-strip` uses child class `kanso-info-item` (not `kanso-info-strip-item`) — label: `kanso-info-label`, value: `kanso-info-value`; sub-labels use inline style `font-size:11px; color:var(--text-faint)`
- `anl-table` is defined in `analytics.css` — pages that don't load analytics.css must mirror it in their own CSS file
- JS-generated modals (Bootstrap `insertAdjacentHTML`) need `kanso-modal` on the `.modal-dialog` div, not the `.modal` wrapper
- Bootstrap `.text-primary` inside JS-rendered HTML gives Bootstrap blue, not `--primary` — always use `style="color:var(--primary)"` instead
- Commitment summary tables (and any multi-column data grids): use `display:grid; grid-template-columns:1fr 1fr` directly on the panel, outside the padded inner div, so tables go edge-to-edge
- Kakeibo types (exact strings, locked): `Needs` / `Wants` / `Business` / `Savings`
- Type colors: `--needs` (green) / `--wants` (orange) / `--business` (blue) / `--savings` (purple)
- SVG icon is 525KB — always use `<img>` tag, never inline
- `data-*` attributes on list items are the bridge between HTML and JS — always add them for any dynamically updated list
- `kanso-select` uses a background-image SVG arrow — the arrow color is hardcoded `%238A8278` (hex for `--text-faint` in warm-ink) — acceptable tradeoff
