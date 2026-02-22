# Kakeibo — Mobile Redesign Tracker
*Started: February 21, 2026*

---

## What This File Is

A session-by-session tracker for the Flutter app redesign and feature work.
One item gets built per session. Nothing gets coded until it is understood and approved here first.

The backend is complete and stable. This file is mobile-only (Flutter).
Web dashboard rework is tracked separately (future).

---

## Core Decisions (Locked)

| Decision | Choice |
|---|---|
| Transaction types | Keep as-is: **Needs / Wants / Business / Savings** |
| App name | **Kakeibo** |
| Japanese subtitle | **家計簿** (kakeibo — household account book) |
| Tagline | "Mindful money tracking" |
| Theme | Both light + dark, with **in-app toggle** |
| Mobile philosophy | Read-only + Add only. No editing. Web dashboard for everything else. |

---

## Redesign Backlog

Items are listed in proposed build order.
Status: `[ ]` pending · `[~]` in progress · `[x]` done

---

### 1. Branding & Theme System  `[x]`

**What:** Rename app, add Japanese subtitle to login, implement both themes, add theme toggle.

**Scope:**
- `main.dart` — new app title, new color palettes (both options below), theme toggle wired to a persisted preference
- `login_screen.dart` — "Kakeibo" header + "家計簿" subtitle
- No other screens change yet

**Theme Option A — Warm Ink (dark, Japanese aesthetic)**
| Role | Color | Notes |
|---|---|---|
| Background | `#141210` | Warm near-black, like dark washi paper |
| Surface | `#201D18` | Slightly lifted warm dark |
| Primary | `#C49A5E` | Gold/amber — candlelight |
| Needs | `#7BAF8E` | Sage green — bamboo |
| Wants | `#D4956A` | Terracotta — warm orange |
| Business | `#6A8FBF` | Slate blue |
| Savings | `#A67FB5` | Wisteria — lavender |
| Error | `#C96060` | Vermillion — beni red |

**Theme Option B — Japanese Indigo (structured, cooler)**
| Role | Color | Notes |
|---|---|---|
| Background | `#0F1117` | Deep indigo-black |
| Surface | `#1A1F2C` | Muted indigo |
| Primary | `#7B9ED9` | Periwinkle / ai-iro indigo |
| Needs | `#7BAF8E` | Same sage green |
| Wants | `#D4956A` | Same terracotta |
| Business | `#6A8FBF` | Same slate blue |
| Savings | `#A67FB5` | Same wisteria |
| Error | `#C96060` | Same vermillion |

**Light theme (shared across both dark options)**
| Role | Color |
|---|---|
| Background | `#F7F4EF` — warm off-white (washi paper) |
| Surface | `#FFFFFF` |
| Primary | `#8C6A3F` — dark amber ink |
| Error | `#C94040` |

**Theme toggle:** small FAB (bottom-right, persistent across all tabs). Cycles Warm Ink → Indigo → Light → repeat. Icon changes to reflect current theme. Preference saved to `shared_preferences` (survives app restarts).

**Files changed:**
- `pubspec.yaml` — added `shared_preferences: ^2.3.0`
- `lib/theme_notifier.dart` — new file, `KakeiboTheme` enum + `StateNotifier`, self-initializing from disk
- `lib/main.dart` — renamed `FinanceApp` → `KakeiboApp`, 3 theme functions + shared `_buildTheme()` builder, FAB in `_ScaffoldWithNavBar`
- `lib/screens/login_screen.dart` — `menu_book_outlined` icon, Kakeibo / 家計簿 / tagline, all hardcoded colors replaced with `Theme.of(context)`
- AppBar titles: Home → "Kakeibo", Add → "Record", Transactions → "History"

---

### 2. Fix Add Transaction (Functional Bug)  `[x]`

**What:** The form currently uses a fake delay and never saves anything. Also sends wrong type values.

**Scope:**
- `add_transaction_screen.dart` — wire `_submit()` to `ApiService.addTransaction()`
- Replace "Expense / Income" segmented toggle with a **4-chip Kakeibo type selector**: Needs / Wants / Business / Savings
- Each type shows its color from the theme
- Remove the "Business expense" switch — Business is now a first-class type choice
- Build the correct `Transaction` object and post to API
- Show success/error feedback

**Not in scope:** editing transactions, deleting, any web changes.

---

### 3. Budgets Screen — Fix Hardcoded Date  `[x]`

**What:** Line 57 of `budgets_screen.dart` has `Text('February 2026')` hardcoded.

**Scope:**
- Pull current month/year dynamically from the API period or `DateTime.now()`
- One-line fix, low risk

---

### 4. Budgets Screen — Expandable Category → Sub-category → Transactions  `[x]`

**What:** 2-level accordion on the Budgets screen mirroring the web dashboard.

```
▶ Dogs                    $906 spent / $1,180 budget   [Under Budget]
  ▶ Dog Food              $111 spent / $154 budget      [Under]
      Chewy  •  Jan 31  •  Venture          $111.55
  ▶ Dog Insurance         $245 spent / $245 budget      [On Track]
      Embrace  •  Feb 19                    $174.22
      Embrace Wellness  •  Feb 19            $70.84
  ▶ Veterinary            $537 spent / $0 budget        [Over]
```

**Backend change required — B1:** New endpoint `GET /api/budget_subcategories`
- Returns category list with nested sub-category rows (budget + actual per sub)
- Fallback: categories with no sub-category templates → treated as their own single sub
- Includes unexpected_expenses at category level
- Parameters: `year`, `month`, `owner`
- **Additive only — nothing existing changes**

**Flutter changes:**
- `ApiService.getBudgetSubcategories()` method
- New Riverpod provider `budgetSubcategoriesProvider`
- `BudgetsScreen` rebuilt as 2-level accordion
- Level 3 transactions use existing `/api/transactions/by-subcategory` endpoint (already in backend)

---

### 5. Budget Calculation Fix — Web + Mobile Alignment  `[x]`

**Root cause found:**
- Web dashboard filters transactions: `type IN ('Needs', 'Wants', 'Business')` — **excludes Savings**
- Web also skips categories that have a `budget_templates` entry but no sub-category breakdown
- Mobile sums all `effective_budget` rows from `budget_analysis` including Savings → higher number

**Decision (locked):** Savings counts toward budget total. Fix web to match.

**Backend change required — B2:** Update `dashboard_budget_view` in `blueprints/dashboards/views.py`
- Remove the `type IN ('Needs', 'Wants', 'Business')` filter (add Savings)
- Include categories from `budget_templates` that have no subcategory breakdown
- **Risk:** Web budget numbers will change to reflect the correct total. This is intentional.

**Flutter change — F3:** Update `dashboardSummaryProvider` budget total calculation
- After B2 is done, verify mobile total matches web

---

### 6. Home Screen — Budget Bar Redesign  `[x]`

**Two stacked segmented bars, same scale (max of budget vs. spending):**
- Row 1 (Budget): `[Initial — primary][Unexpected — orange][Remaining — gray]`
- Row 2 (Spending): `[Needs — green][Wants — orange][Business — blue][Savings — purple][Unspent — gray]`

**Data sources (no backend changes needed):**
- `budget_analysis` → sums `initial_budget`, `unexpected_expenses`, `effective_budget`
- `dashboard_summary.monthly_spending` → keyed by Needs/Wants/Business/Savings (already type-grouped)

**Note — commitment portion:** The web dashboard tracks fixed commitments in a `budget_commitments` table (rent, subscriptions, etc). This is not yet exposed to mobile. When added, the budget bar can add a `[Committed]` first segment before `Initial`. Tracked as future work.

---

### 7. Home Screen — Remove Stat Cards, Add Insights  `[x]`

**Removed:** All 4 stat cards (Spent, Remaining, Total Debt, Min Payments). The two bars + insights replace them.

**Added:**
| Section | Source | Notes |
|---|---|---|
| Spending by Type | `dashboard_summary.monthly_spending` | 4 colored tiles (Needs/Wants/Business/Savings) |
| Top 5 Sub-categories | `getBudgetSubcategories()` flattened | Excludes any sub named "rent" (case-insensitive), 0-spend excluded |
| Spending by Owner | `getDashboardSummary(owner: x)` × n | Parallel calls via `Future.wait`, bar chart per person |

**New providers added:** `ownerSpendingProvider`, `topSubcategoriesProvider`

---

### 8. Home Screen — Kakeibo Framing + Title  `[x]`

- AppBar title: current month name (dynamic from `summary.month`, fallback "Kakeibo" while loading)
- Subheader line: `FEBRUARY 2026` in primary color + `How are we doing this month?` italic greeting
- 6-month trend chart retained

---

### 9. Transaction History — Type Color Coding  `[ ]`

**What:** Each transaction row should visually indicate its Kakeibo type (Needs/Wants/Business/Savings).

**Scope:**
- Add a colored left border or colored avatar based on `tx.type`
- Use the 4 type colors from the new theme

---

### 10. Navigation — Icons & Labels  `[x]`

**Proposed:**
| Tab | Label | Icon |
|---|---|---|
| Home | Overview | `wb_sunny_outlined` |
| Add | Record | `edit_note` |
| Transactions | History | `receipt_long_outlined` |
| Budgets | Budget | `pie_chart_outline` |
| Debts | Debts | `credit_card_outlined` |

---

### 11. Debts Screen — Polish  `[ ]`

Minor visual polish, no functional changes. Review in session.

---

### 12. Analytics — Rethink (Web + Mobile)  `[ ]`

**What:** Define what insights are actually useful for a Kakeibo-style monthly review.

**Kakeibo's four end-of-month questions:**
1. How much did I have?
2. How much did I save?
3. How much did I spend?
4. How can I improve next month?

**Ideas to explore (not committing yet):**
- Category drilldown per type
- Month-over-month comparison per type
- Savings rate trend
- Wants as % of total (mindfulness metric)
- Unexpected expenses flag

**Platform split (TBD):**
- Mobile: simple insight card on Home ("Your Wants are up 12% vs last month")
- Web: full analytics rework with filters, year-over-year, drilldowns

---

## Session Log

| Date | What Was Built |
|---|---|
| Feb 21, 2026 | Backend complete, Flutter connected to production API |
| Feb 21, 2026 | redesign.md created, core decisions locked |
| Feb 21, 2026 | Add Transaction wired to real API — Needs/Wants/Business/Savings type chips, isBusiness auto-derived |
| Feb 21, 2026 | account_name made optional in backend (removed from required fields) |
| Feb 21, 2026 | New GET /api/budget_subcategories endpoint — category + sub + transactions hierarchy |
| Feb 21, 2026 | Web dashboard budget fix — added Savings to transaction type filter |
| Feb 21, 2026 | Budgets screen rebuilt — 2-level accordion (category → sub-category → transactions) |
| Feb 21, 2026 | Hardcoded February 2026 date replaced with dynamic DateFormat |
| Feb 21, 2026 | Branding complete — app renamed Kakeibo, 家計簿 subtitle, 3-theme system (Warm Ink / Indigo / Light), theme toggle FAB, all AppBar titles updated |
| Feb 21, 2026 | Fixed Xcode build error — replaced stale counter test (MyApp ref) with placeholder; cleaned up unnecessary_underscores warnings |
| Feb 21, 2026 | Home screen rebuilt — dual-bar budget (Initial/Unexpected vs Needs/Wants/Business/Savings), type breakdown tiles, top 5 subs (excl. Rent), spending by owner; all stat cards removed |
| Feb 21, 2026 | DashboardSummary model extended — initialBudget, unexpectedBudget, spendingByType fields; two new providers: ownerSpendingProvider, topSubcategoriesProvider |
| Feb 21, 2026 | Type tiles as filters — tap Needs/Wants/Business/Savings to filter top-5 categories, owner breakdown, and 6-month trend; tap again to clear; one type active at a time |

---

## Gotchas to Carry Forward

- DB types are exactly: `Needs`, `Wants`, `Business`, `Savings` — never change these
- Savings inclusion in budget total is temporary — will be revisited later
- Top 5 sub-categories (home insights) needs client-side grouping from `/api/transactions`
- Flutter `lib/` is gitignored — Dart files are local only
- Bearer token has no expiry — persists until explicit logout
- Backend must be deployed to Railway before testing any new API endpoints on device
