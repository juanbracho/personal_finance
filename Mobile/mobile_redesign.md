# Kanso — Mobile Redesign Tracker
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
| App name | **Kanso** (renamed from Kakeibo for easier pronunciation) |
| App subtitle | **"Mindful money tracking"** |
| Theme | 3-way cycle: Warm Ink (dark) → Indigo (dark) → Washi Paper (light) |
| Theme toggle | IconButton in every AppBar top-right, persistent across all tabs |
| Mobile philosophy | Read-only + Add only. No editing. Web dashboard for everything else. |
| Nav order | Overview · History · Record · Budget · Debts |

---

## Theme Reference (Locked)

**Warm Ink — dark, Japanese aesthetic**
| Role | Color | Notes |
|---|---|---|
| Background | `#141210` | Warm near-black, like dark washi paper |
| Surface | `#201D18` | Slightly lifted warm dark |
| Primary | `#C49A5E` | Gold/amber — candlelight |
| Needs | `#7BAF8E` | Sage green — bamboo |
| Wants | `#D4956A` | Terracotta — warm orange |
| Business | `#6A8FBF` | Slate blue |
| Savings | `#A67FB5` | Wisteria — lavender |
| Unexpected | `#E8761F` | Vivid orange — distinct across all themes |
| Error | `#C96060` | Vermillion — beni red |

**Japanese Indigo — structured, cooler**
| Role | Color |
|---|---|
| Background | `#0F1117` |
| Surface | `#1A1F2C` |
| Primary | `#7B9ED9` — periwinkle |

**Washi Paper — light**
| Role | Color |
|---|---|
| Background | `#F7F4EF` — warm off-white |
| Surface | `#FFFFFF` |
| Primary | `#8C6A3F` — dark amber ink |

---

## Redesign Backlog

Items are listed in proposed build order.
Status: `[ ]` pending · `[~]` in progress · `[x]` done

---

### 1. Branding & Theme System  `[x]`

3-theme system (Warm Ink / Indigo / Washi Paper), theme toggle as AppBar IconButton on every screen, `shared_preferences` persistence.

**Files:** `pubspec.yaml`, `lib/theme_notifier.dart`, `lib/main.dart`, `lib/screens/login_screen.dart`, `lib/widgets/theme_toggle_button.dart`

---

### 2. Fix Add Transaction (Functional Bug)  `[x]`

Wired `_submit()` to `ApiService.addTransaction()`. Replaced Expense/Income toggle with 4-chip Kakeibo type selector (Needs / Wants / Business / Savings). Business is now a first-class type — no separate switch.

---

### 3. Budgets Screen — Fix Hardcoded Date  `[x]`

Replaced `Text('February 2026')` with `DateFormat('MMMM yyyy').format(DateTime.now())`.

---

### 4. Budgets Screen — Expandable Accordion  `[x]`

2-level accordion: Category → Sub-category → Transactions.

```
▶ Dogs                    $906 spent / $1,180 budget   [Under]
  ▶ Dog Food              $111 spent / $154 budget
      Chewy  •  Jan 31  •  Venture          $111.55
  ▶ Dog Insurance         $245 spent / $245 budget
      Embrace  •  Feb 19                    $174.22
```

Backend: new `GET /api/budget_subcategories` endpoint (additive).
Flutter: `getBudgetSubcategories()`, `budgetSubcategoriesProvider`, rebuilt `BudgetsScreen`.

---

### 5. Budget Calculation Fix  `[x]`

**Decision (locked):** Savings counts toward budget total.
Fixed web `dashboard_budget_view` to include Savings in the type filter. Mobile and web now agree.

---

### 6. Home Screen — Dual Budget Bars  `[x]`

Two stacked segmented bars sharing the same scale:
- **Budget bar:** `[Initial — primary][Unexpected — orange #E8761F][Remaining — gray]`
- **Spending bar:** `[Needs][Wants][Business][Savings][Unspent — gray]`

No backend changes needed — data was already available in `budget_analysis` + `dashboard_summary`.

---

### 7. Home Screen — Insights  `[x]`

Removed all 4 stat cards. Replaced with:

| Section | Source |
|---|---|
| Spending by Type | `dashboard_summary.monthly_spending` — 4 tappable colored tiles |
| Top 5 Sub-categories | Month transactions, client-side grouped, rent excluded |
| Spending by Owner | Month transactions, client-side grouped |
| 6-month trend chart | `/api/monthly_trends` — re-fetches when type filter changes |

Type tiles act as filters: tap to filter all three insight sections + trend chart. Tap again to clear. One active at a time.

---

### 8. Home Screen — Branding & Greeting  `[x]`

- AppBar: persistent `KansoTitle` widget (app name + subtitle, same as all other screens)
- Body subheader: `MONTH YEAR` in primary color + *"How are we doing this month?"* italic greeting

---

### 9. Navigation — Final Order  `[x]`

| Tab | Label | Icon |
|---|---|---|
| 0 | Overview | `dashboard_outlined` |
| 1 | History | `receipt_long_outlined` |
| 2 | Record | `edit_note_outlined` |
| 3 | Budget | `pie_chart_outline` |
| 4 | Debts | `credit_card_outlined` |

Record is center tab. History moved to index 1.

---

### 10. App Identity — Kanso Branding  `[x]`

- App renamed **Kanso** (was Kakeibo)
- `KansoTitle` widget: "Kanso" bold + "Mindful money tracking" muted subtitle — shown in every screen's AppBar top-left
- iOS `CFBundleDisplayName` + `CFBundleName` → "Kanso"
- Android `android:label` → "Kanso"
- App icons: all iOS sizes (iPhone + iPad) generated from `appstore.png` via `sips`; Android all 5 mipmap densities copied from pre-made assets
- Login screen: "Kanso" + "Mindful money tracking" tagline

---

### 11. Transaction History — Type Color Coding  `[ ]`

**What:** Each transaction row should visually indicate its Kakeibo type.

**Scope:**
- Colored left border or leading dot/avatar based on `tx.type`
- Use the 4 type colors: Needs `#7BAF8E` · Wants `#D4956A` · Business `#6A8FBF` · Savings `#A67FB5`

---

### 12. Debts Screen — Polish  `[ ]`

Minor visual polish, no functional changes. Review when needed.

---

### 13. Analytics — Future  `[ ]`

Define what insights are useful for a Kanso-style monthly review.

**Kanso's four end-of-month questions:**
1. How much did I have?
2. How much did I save?
3. How much did I spend?
4. How can I improve next month?

**Ideas (not committing yet):**
- Month-over-month comparison per type
- Savings rate trend
- Wants as % of total (mindfulness metric)
- Unexpected expenses flag

**Platform split (TBD):**
- Mobile: simple insight card on Home ("Your Wants are up 12% vs last month")
- Web: full analytics rework with filters, year-over-year, drilldowns

---

## Mobile v1 — Complete ✓

*February 21, 2026*

All core screens are live and connected to production. The app is usable day-to-day. Remaining backlog items (11–13) are polish and future features, not blockers.

**What's working:**
- Login / logout with real Bearer token auth
- Home: dual budget bars, type filter tiles, top-5 categories, spending by owner, 6-month trend
- Record: add transactions with Needs/Wants/Business/Savings type selection
- History: transaction list with owner/category/date filters
- Budget: 2-level accordion (category → sub → transactions)
- Debts: debt list with balances and rates
- 3-theme system persistent across restarts
- Kanso branding and custom icon on device

---

## Session Log

| Date | What Was Built |
|---|---|
| Feb 21, 2026 | Backend complete, Flutter connected to production API |
| Feb 21, 2026 | Add Transaction wired to real API — Needs/Wants/Business/Savings type chips |
| Feb 21, 2026 | New `GET /api/budget_subcategories` endpoint; budgets screen rebuilt as 2-level accordion |
| Feb 21, 2026 | Web dashboard budget fix — added Savings to transaction type filter |
| Feb 21, 2026 | 3-theme system (Warm Ink / Indigo / Washi Paper), `shared_preferences` persistence |
| Feb 21, 2026 | Home screen rebuilt — dual budget bars, type tiles, top-5 subs, spending by owner |
| Feb 21, 2026 | Type tiles as filters — tap to filter categories, owner breakdown, and 6-month trend |
| Feb 21, 2026 | Theme toggle moved to AppBar top-right (ThemeToggleButton widget); FAB removed |
| Feb 21, 2026 | Nav reordered: Overview / History / Record / Budget / Debts (Record is center tab) |
| Feb 21, 2026 | Unexpected bar color fixed to vivid orange (#E8761F) — distinct across all 3 themes |
| Feb 21, 2026 | App renamed Kanso; KansoTitle widget ("Kanso / Mindful money tracking") on all screens |
| Feb 21, 2026 | App icon + display name updated on iOS and Android; Xcode now shows Kanso |

---

## Gotchas to Carry Forward

- DB types are exactly: `Needs`, `Wants`, `Business`, `Savings` — never change these strings
- Savings inclusion in budget total is locked — revisit only if explicitly requested
- Month transactions fetched once at `perPage: 500` for client-side filtering — increase if data grows
- Flutter `lib/` is gitignored — Dart files are local only, not in git
- Bearer token has no expiry — persists until explicit logout
- Backend must be deployed to Railway before testing any new API endpoints on device
- Budget commitment tracking (rent, subscriptions) exists on web but is not yet exposed to mobile — future work
