# Post-Redesign Fix Session — Feb 22 2026

## Overview
Three bugs identified after the mobile redesign. All fixed sequentially in one session.

---

## Task 1: History — Infinite Scroll Pagination ✅ DONE

### Problem
`transactionsProvider` was a flat `FutureProvider` that fired one call (default
`perPage=50`) with no "load more" trigger.

### Root Cause
- `transactionsProvider` had no page tracking.
- `TransactionsScreen` used a plain `ListView.builder` with no `ScrollController`.
- `TransactionsFilter` lacked `==` / `hashCode`, needed for Riverpod `.family` key.

### Fix Applied
**`app_providers.dart`**
- Removed old `transactionsProvider` (flat FutureProvider).
- Added `TransactionsPagination` state class (transactions, isInitialLoading,
  isLoadingMore, hasMore, currentPage, error).
- Added `TransactionsPaginationNotifier extends StateNotifier<TransactionsPagination>`
  with `_loadPage(page)`, `loadNextPage()` (guarded by hasMore + 250-item cap),
  and `refresh()`.
- Added `transactionsPaginationProvider` as
  `StateNotifierProvider.autoDispose.family<..., TransactionsFilter>`.
- Added `==` and `hashCode` to `TransactionsFilter` so different filter states
  map to different (auto-disposed) provider instances.

**`transactions_screen.dart`**
- Converted to `ConsumerStatefulWidget` to hold `ScrollController`.
- Scroll listener fires `loadNextPage()` when within 200 px of the bottom.
- `ListView.builder` appends a spinner as the last item while loading more,
  and a "Showing N transactions" caption when all pages are exhausted.
- Refresh button calls `notifier.refresh()` directly.
- Filter apply no longer calls `ref.invalidate` — changing the filter creates
  a new family instance which loads page 1 automatically.

**`add_transaction_screen.dart`**
- `ref.invalidate(transactionsProvider)` → `ref.invalidate(transactionsPaginationProvider)`
  (invalidates all family instances on save).

### Behaviour
- 50 transactions per page.
- Loads next page automatically as user scrolls near the bottom.
- Hard cap at 250 items (5 pages); shows end-of-list label after that.

---

## Task 2: Records (Add Transaction) — Dynamic Types Including Savings ✅ DONE

### Problem
The type-chip row showed only types that had transactions in the *current calendar
year*. Types used only in prior years (e.g. Savings) were invisible in the form.

### Root Cause
`/api/categories/types` (backend) defaults `year = datetime.now().year` and always
applies a year filter on the SQL query. The mobile `getTypes()` passes no year param,
so the backend silently filtered to this year only.

### Fix Applied
**Backend `blueprints/api/routes.py` — `api_types()`**
- Added `all_years = request.args.get('all_years', '0') == '1'` parameter.
- When `all_years=1`, `date_filter` is set to `"1=1"` with no params (no year
  restriction). All other filters (owner) still apply normally.
- Existing web-dashboard callers that don't send `all_years` retain current-year
  behaviour unchanged.

**`services/api_service.dart` — `getTypes()`**
- Now calls `_getList('/api/categories/types', {'all_years': '1'})`.
- The form therefore always shows every type ever recorded in the DB, including
  Savings and any future custom types.

---

## Task 3: Overview — Dynamic Budget Bar Segments & Legend ✅ DONE

### Problem
The Budget Health spending bar was hardcoded for exactly four types
(Needs / Wants / Business / Savings):
- Types with zero spending still appeared in the legend.
- The "Unexpected" type introduced in the redesign was completely missing from
  the bar and legend.

### Root Cause
`_BudgetCard` in `home_screen.dart` computed four named flex ints and rendered
four hardcoded `_DotLabel` widgets regardless of actual spending data.

### Fix Applied
**`home_screen.dart` — `_BudgetCard._build()`**
- Replaced four hardcoded flex variables with a `typeColorMap` (extended to
  include `Unexpected → _kUnexpected`) and a dynamic loop over
  `summary.spendingByType.entries`.
- Loop filters to types with `value > 0`, sorts largest-first, clamps each
  flex to remaining capacity, accumulates `_Seg` objects into `spendingSegments`
  and `_DotLabel` widgets into `legendDots`.
- `_SegmentedBar` receives `[...spendingSegments, remSptFlex-gray-seg]`.
- `_BarRowLabel` receives `legendDots` — only types that actually appear in
  the bar get a legend entry.
- Unknown/future custom types automatically get the orange `_kUnexpected` colour
  via the `typeColorMap[typeName] ?? _kUnexpected` fallback.

---

## Shared Color Map (reference)
```
Needs       #7BAF8E  (green)
Wants       #D4956A  (orange-tan)
Business    #6A8FBF  (blue)
Savings     #A67FB5  (purple)
Unexpected  #E8761F  (vivid orange)
default     #E8761F  (same orange for unknown custom types)
```