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

---

# Settings Screen + Biometric Opt-In — Feb 23 2026

## Overview
Replaced per-screen theme toggle icon with a centralized Settings screen. Added biometric unlock (Face ID / Touch ID / fingerprint) as an opt-in feature. App still requires credentials on every cold start, but biometric-opted-in users are prompted automatically and skip the password form.

---

## Task 10: Settings Screen ✅
**Route:** `/settings` — top-level `GoRoute` outside the `StatefulShellRoute`, pushed modally over any active tab with a native back arrow via `context.push('/settings')`.

**Sections:**
- **Appearance** — three `RadioListTile<KakeiboTheme>` entries (Warm Ink · Japanese Indigo · Washi Paper). Watches `themeNotifierProvider`; calls `setTheme()` on tap. Theme changes are instant and persist across restarts (existing `SharedPreferences` key `kakeibo_theme`).
- **Security** — `SwitchListTile` for "Face ID / Touch ID". Only rendered when `BiometricService.isAvailable()` returns true (checked in `initState`). Toggles `biometricOptInProvider` which writes to `SharedPreferences` key `biometric_opt_in`.
- **Account** — "Sign Out" `ListTile` with `colorScheme.error` text/icon. Shows a confirmation `AlertDialog` before calling `authNotifier.logout()`.

**New file:** `lib/screens/settings_screen.dart`

---

## Task 11: Biometric Opt-In Infrastructure ✅

### `lib/services/biometric_service.dart` (new)
Static utility wrapping `local_auth`:
- `isAvailable()` — calls `canCheckBiometrics` + `getAvailableBiometrics()`. Returns false on any exception (safe on simulators).
- `authenticate()` — calls `authenticate()` with `biometricOnly: true`, `stickyAuth: true`. Returns false on exception or user cancellation.

### `lib/providers/biometric_provider.dart` (new)
```dart
class BiometricOptInNotifier extends StateNotifier<bool>
  - _load()         // reads SharedPrefs key 'biometric_opt_in' on init
  - setOptIn(bool)  // writes to SharedPrefs + updates state
  - toggle()        // calls setOptIn(!state)

final biometricOptInProvider = StateNotifierProvider<BiometricOptInNotifier, bool>
```

### `lib/auth_notifier.dart` — biometric unlock flag
Added to `AuthNotifier`:
```dart
bool _needsBiometricUnlock = false;
bool get needsBiometricUnlock => _needsBiometricUnlock;
```
`init()` now reads `biometric_opt_in` from `SharedPreferences` and checks for a stored token via `ApiService.getApiKey()`. If both are true, sets `_needsBiometricUnlock = true` before notifying listeners.

`clearBiometricUnlock()` resets the flag without calling `notifyListeners()` — callers handle state transition via `setLoggedIn()`.

---

## Task 12: Login Screen — Biometric Auto-Trigger ✅
`lib/screens/login_screen.dart` changes:
- Added `_showBiometricButton` state bool.
- In `initState`: if `authNotifier.needsBiometricUnlock` is true, sets `_showBiometricButton = true` and schedules `_tryBiometric()` via `addPostFrameCallback` (ensures widget tree is mounted before the OS prompt appears).
- `_tryBiometric()`: calls `BiometricService.authenticate()`. On success → `clearBiometricUnlock()` + `setLoggedIn(true)`. On failure/cancel → `clearBiometricUnlock()` + clears `_showBiometricButton` (falls back to password form).
- A secondary `OutlinedButton.icon` (fingerprint icon, "Use Face ID / Touch ID") appears below the Sign In button when `_showBiometricButton` is true, allowing the user to re-trigger the prompt if they dismissed it.

---

## Task 13: Theme Toggle → Settings Gear (4 screens) ✅
Replaced `const ThemeToggleButton()` in every tab's AppBar `actions` with:
```dart
IconButton(
  icon: const Icon(Icons.settings_outlined),
  tooltip: 'Settings',
  onPressed: () => context.push('/settings'),
)
```
Screens updated: `home_screen.dart`, `transactions_screen.dart`, `budgets_screen.dart`, `debts_screen.dart`.

Each screen: removed `import '../widgets/theme_toggle_button.dart'`, added `import 'package:go_router/go_router.dart'`.

`add_transaction_screen.dart`: removed the `ThemeToggleButton` import and usage (screen has no route; housekeeping only).

`lib/widgets/theme_toggle_button.dart`: **deleted** — no longer referenced.

---

## Task 14: Platform Configuration ✅

### iOS — `ios/Runner/Info.plist`
Added inside root `<dict>`:
```xml
<key>NSFaceIDUsageDescription</key>
<string>Use Face ID to unlock Kanso without entering your password</string>
```
Required by iOS for any app using Face ID. Without this the app crashes when `local_auth` is invoked.

### Android — `android/app/src/main/AndroidManifest.xml`
Two changes:
1. Added permission before `<application>`:
   ```xml
   <uses-permission android:name="android.permission.USE_BIOMETRIC"/>
   ```
2. Changed `<activity android:name=".MainActivity"` → `android:name="io.flutter.embedding.android.FlutterFragmentActivity"` — required by `local_auth` on Android (the plugin uses `FragmentActivity` APIs for the biometric prompt).

---

## Dependency Added
```yaml
local_auth: ^2.3.0   # resolved to 2.3.0
```
Transitive additions: `local_auth_android`, `local_auth_darwin`, `local_auth_windows`, `local_auth_platform_interface`, `flutter_plugin_android_lifecycle`.

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
