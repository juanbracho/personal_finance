# Post-Redesign Fix Session — Feb 22 2026

## Overview
All tasks completed in one session. App is now read-only (review mode — no Record tab).

---

## Task 1: History — Infinite Scroll Pagination ✅
- Replaced flat `transactionsProvider` with `TransactionsPaginationNotifier` (StateNotifier).
- 50 items per page, max 250. Scroll within 200 px of bottom triggers next page.
- Spinner appears as last list item while loading; end-of-list caption when cap reached.
- Filter change creates a new family provider instance → auto-resets to page 1.
- `add_transaction_screen.dart` updated to invalidate all family instances on save.
- `TransactionsFilter` got `==` / `hashCode` (required for `.family` key).

---

## Task 2: Add Transaction — Dynamic Types (dropdown) ✅
- Replaced custom chip selector with standard `DropdownButtonFormField<String>`,
  matching Category / Owner / Account pattern.
- `_selectedType` is now nullable; validation rejects submit if not chosen.
- Backend `/api/categories/types` gained `all_years=1` param: skips year filter so
  every type ever in the DB (Savings, Unexpected, etc.) appears in the form.
- `ApiService.getTypes()` passes `all_years=1`.
- Removed `_buildTypeChips`, `_TypeChip` widget, and `ref.listen` block.

---

## Task 3: Overview — Dynamic Budget Bar Segments & Legend ✅
- `_BudgetCard` spending bar was hardcoded for Needs/Wants/Business/Savings.
- Replaced with dynamic loop over `spendingByType.entries` (only types with > 0).
- Legend entries mirror exactly what is in the bar (no phantom zero-spend labels).
- Unexpected and any future custom type handled via `typeColorMap` fallback.

---

## Task 4: Budget — Correct Initial Budget Source ✅
**Root cause:** `/api/budget_analysis` and `/api/budget_subcategories` both read
initial budgets from `budget_templates` (stale, auto-generated in 2025 from
transaction averages). The web Budget page writes to `budget_subcategory_templates`.

**Fix (backend `blueprints/api/routes.py`):**
Both endpoints now query:
```sql
SELECT category, SUM(budget_amount) AS budget_amount
FROM budget_subcategory_templates
WHERE is_active = 1
GROUP BY category
```
Result: Initial = $9,392.91 ✓  Unexpected = $1,700 ✓  Effective = $11,092.91 ✓

---

## Task 5: Web Overview Budget — Unexpected Type Excluded from Spending ✅
**Root cause:** `dashboards/views.py` spending query had:
```sql
AND type IN ('Needs', 'Wants', 'Business', 'Savings')
```
Transactions with type = 'Unexpected' (or any custom type) were silently excluded.

**Fix:** Replaced with `AND COALESCE(type, '') != ''` — includes all typed transactions.

---

## Task 6: Budget Page — No-Budget Categories with Spending Show Red ✅
- Categories with `status = 'no_budget'` but `spent > 0` were showing gray/empty.
- `_CategoryTile` now checks `unbudgetedSpend = status == 'no_budget' && spent > 0`.
- When true: progress bar is full (1.0) and `statusColor` is `colorScheme.error` (red).

---

## Task 7: Overview — Month / Year Period Selector ✅
- Added `homeMonthProvider` and `homeYearProvider` (StateProvider<int>) initialized
  to current month/year.
- `dashboardSummaryProvider` and `homeMonthTransactionsProvider` watch both providers
  and re-fetch automatically when either changes.
- `ApiService.getDashboardSummary()` now accepts optional `month` and `year` params.
- Static "How are we doing this month?" text replaced with `_PeriodHeader` widget:
  **"How are we doing on [Month ▾] [Year ▾]?"**
- Tapping month or year opens a `_PickerSheet` bottom-sheet list.
- Refresh button resets period to current month/year before re-fetching.

---

## Task 8: Budget — Month / Year Period Selector ✅
- Added `budgetMonthProvider` and `budgetYearProvider` (StateProvider<int>) initialized
  to current month/year — independent from the Overview's home period providers.
- `budgetSubcategoriesProvider` now watches both providers instead of hardcoding
  `DateTime.now()` — changing either triggers an automatic re-fetch.
- Static `monthLabel` text in the summary card replaced with tappable
  **[Month ▾] [Year ▾]** chips (same visual style as the Overview header).
- Tapping a chip opens a `_PickerSheet` bottom-sheet list (added to `budgets_screen.dart`).
- Refresh button resets period to current month/year before re-fetching.
- Pull-to-refresh keeps the selected period intact.
- `year` and `month` threaded down: `BudgetsScreen` → `_CategoryTile` → `_SubcategoryTile`.
- `_SubcategoryTile._loadTransactions()` uses the selected period instead of
  `DateTime.now()`, so drilled-down transactions always match the chosen month/year.

---

## Task 9: Remove Record Tab — App is Read-Only ✅
- Removed `/add` route branch from `GoRouter`.
- Removed `Record` `NavigationDestination` from bottom nav.
- Removed `add_transaction_screen.dart` import from `main.dart`.
- App now has 4 tabs: Overview · History · Budget · Debts.

---

## Shared Color Map
```
Needs       #7BAF8E  (green)
Wants       #D4956A  (orange-tan)
Business    #6A8FBF  (blue)
Savings     #A67FB5  (purple)
Unexpected  #E8761F  (vivid orange)
default     #E8761F  (same for unknown custom types)
```
