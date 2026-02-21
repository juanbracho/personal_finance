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

### 1. Branding & Theme System  `[ ]`

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

**Theme toggle:** small icon button (top-right of home screen or settings). Preference saved locally.

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

### 6. Home Screen — Budget Bar Redesign  `[ ]`

**Depends on:** Item #5 confirmed and API fields verified.

**API already exposes** (per `budget_analysis` rows): `initial_budget`, `unexpected_expenses`, `effective_budget`
So the layered bar is doable with existing data — just sum across rows.

**Visual approach:**
- Two rows:
  - Row 1: Actual spent, stacked by type (Needs/Wants/Business/Savings, 4 colors)
  - Row 2: Effective budget bar — with a tick/divider showing where Initial ends and Unexpected begins
- Labels: Initial $X | +Unexpected $Y | = Effective $Z | Spent $W

---

### 7. Home Screen — Remove Stat Cards, Add Insights  `[ ]`

**Depends on:** Item #6.

**Remove:** Total Debt, Min Payments cards (Debt tab exists for that).
**Possibly remove:** Spent + Remaining cards too (covered by bar).

**Add:**
| Insight | Source | Notes |
|---|---|---|
| Spending by type | `dashboard_summary.monthly_spending` | Already available |
| Spending by owner | Owner-filtered summary calls | 3 quick API calls (one per owner) |
| Top 5 sub-categories (excl. Rent) | Client-side from transactions | Hardcode exclusion list in config |

---

### 8. Home Screen — Kakeibo Framing + Title  `[ ]`

**What:** Rename "Dashboard" title, add month context, add mindfulness tone.

**Scope:**
- AppBar title: current month name ("February") instead of "Dashboard"
- Small subtitle or greeting line beneath the header
- Keep 6-month trend chart — it works and is useful

---

### 9. Transaction History — Type Color Coding  `[ ]`

**What:** Each transaction row should visually indicate its Kakeibo type (Needs/Wants/Business/Savings).

**Scope:**
- Add a colored left border or colored avatar based on `tx.type`
- Use the 4 type colors from the new theme

---

### 10. Navigation — Icons & Labels  `[ ]`

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

---

## Gotchas to Carry Forward

- DB types are exactly: `Needs`, `Wants`, `Business`, `Savings` — never change these
- `add_transaction_screen.dart` is now wired to real API ✓
- `budgets_screen.dart` line 57 has hardcoded "February 2026" — fix is item #3
- Budget total discrepancy ($12,710 mobile vs $11,092 web) — must investigate before redesigning the bar (item #5)
- Top 5 sub-categories insight needs API decision — either new backend endpoint or client-side grouping
- Flutter `lib/` is gitignored — Dart files are local only
- Bearer token has no expiry — persists until explicit logout
