# SplitMate MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working, responsive Django MVP that stores trips and equal-split expenses in SQLite and produces exact per-member balances and settlement transfers.

**Architecture:** A single `expenses` Django app owns the models, forms, function-based views, templates, and static assets. Exact money allocation and settlement live in a side-effect-free service module, while views coordinate trip-scoped forms and atomic database writes.

**Tech Stack:** Python 3.10+, Django 5.2 LTS (`Django>=5.2.18,<5.3`), Django Templates, SQLite, HTML, CSS, and vanilla JavaScript.

**Spec:** `docs/superpowers/specs/2026-10-14-splitmate-mvp-design.md`

## Global Constraints

- Use Django Templates and server-rendered function-based views; do not add React, Vue, REST Framework, Bootstrap, Tailwind, Node.js, Docker, or another front-end framework.
- Persist money in `DecimalField(max_digits=12, decimal_places=2)` and perform allocation in integer cents; never use binary floating point.
- Keep `Expense` limited to `trip`, `title`, `amount`, `paid_by`, `participants`, and `created_at`; do not add category, payment-status, or paid-state fields.
- Support only equal splits in this release.
- Store application data in SQLite.
- Keep all mutating multi-record workflows atomic, CSRF-protected, and scoped to the trip in the URL.
- All user-facing pages must remain usable at desktop, tablet, and mobile widths.
- Use Traditional Chinese for application UI copy while preserving the approved English hero tagline.

## Review Focus

- Case-only duplicate member names such as `Kai` and `kai` must be rejected before any trip or member is persisted; Task 4 pins this with an atomicity test.
- A tampered payer or participant ID from another trip must be rejected and must not create or corrupt an expense; Tasks 1 and 5 pin both model and HTTP boundaries.
- Splitting NT$0.01 among three participants must conserve exactly one cent with deterministic recipient ordering; Task 2 pins this edge case.
- Blank extra formset rows and deleted dynamic rows must not be counted as valid members, while two valid rows still succeed; Task 4 pins both submissions.
- Trips with no expenses or with zero net balances must render a friendly settlement state and no fabricated transfer; Tasks 2 and 6 pin this behavior.

## File Map

- `manage.py`, `config/`: Django entry point, settings, and root URL routing.
- `requirements.txt`: supported Django 5.2 LTS dependency range.
- `.gitignore`: local Python, virtual-environment, SQLite, and editor artifacts.
- `expenses/models.py`: `Trip`, `Member`, and `Expense` persistence and direct invariants.
- `expenses/signals.py`: trip-membership validation for many-to-many participant changes.
- `expenses/forms.py`: trip, member formset, and trip-scoped expense input validation.
- `expenses/services.py`: exact allocation, balances, expense summaries, and settlements.
- `expenses/views.py`, `expenses/urls.py`: HTTP coordination and named routes.
- `expenses/templates/expenses/`: home, create-trip, trip-detail, add-expense, and settlement pages.
- `templates/base.html`: shared document shell and navigation.
- `expenses/static/expenses/css/style.css`: visual system and responsive layouts.
- `expenses/static/expenses/js/app.js`: dynamic formset rows and deletion confirmation.
- `expenses/tests/`: focused model, service, trip-view, and expense-view test modules.
- `README.md`: setup, migration, test, and launch instructions.

---

### Task 1: Django Foundation and Data Integrity

**Files:**
- Create: `.gitignore`
- Create: `requirements.txt`
- Create: `manage.py`
- Create: `config/__init__.py`
- Create: `config/settings.py`
- Create: `config/urls.py`
- Create: `config/asgi.py`
- Create: `config/wsgi.py`
- Create: `expenses/__init__.py`
- Create: `expenses/apps.py`
- Create: `expenses/admin.py`
- Create: `expenses/models.py`
- Create: `expenses/signals.py`
- Create: `expenses/migrations/__init__.py`
- Create: `expenses/migrations/0001_initial.py`
- Create: `expenses/tests/__init__.py`
- Create: `expenses/tests/test_models.py`

**Interfaces:**
- Consumes: no application interfaces.
- Produces: `Trip(name, created_at)`, `Member(trip, name)`, and `Expense(trip, title, amount, paid_by, participants, created_at)`; reverse names `trip.members`, `trip.expenses`, `member.expenses_paid`, and `member.expenses_shared`.

- [ ] **Step 1: Create the minimal Django scaffold and dependency files**

Set `requirements.txt` to `Django>=5.2.18,<5.3`, configure `config.settings` for SQLite, `templates/`, and the `expenses` app, and ignore `.venv/`, `__pycache__/`, `*.py[cod]`, `.pytest_cache/`, `.coverage`, `db.sqlite3`, and common editor files.

- [ ] **Step 2: Install dependencies and verify the scaffold**

Run: `python -m pip install -r requirements.txt`

Run: `python manage.py check`

Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 3: Write failing model tests**

Add tests named `test_trip_can_be_created`, `test_member_belongs_to_trip`, `test_expense_saves_payer_and_participants`, `test_expense_rejects_payer_from_another_trip`, `test_participants_reject_members_from_another_trip`, and `test_member_name_is_unique_within_trip_case_insensitively`. Assert exact relationships and `ValidationError` or `IntegrityError` outcomes.

- [ ] **Step 4: Run model tests to verify they fail**

Run: `python manage.py test expenses.tests.test_models -v 2`

Expected: FAIL because the models and initial migration do not yet exist.

- [ ] **Step 5: Implement models and relationship validation**

Use these exact field choices:

- `Trip.name = CharField(max_length=120)`
- `Trip.created_at = DateTimeField(auto_now_add=True)`
- `Member.trip = ForeignKey(Trip, on_delete=CASCADE, related_name="members")`
- `Member.name = CharField(max_length=80)` with a case-insensitive per-trip `UniqueConstraint(Lower("name"), "trip", name="unique_member_name_per_trip_ci")`
- `Expense.trip = ForeignKey(Trip, on_delete=CASCADE, related_name="expenses")`
- `Expense.title = CharField(max_length=160)`
- `Expense.amount = DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])`
- `Expense.paid_by = ForeignKey(Member, on_delete=PROTECT, related_name="expenses_paid")`
- `Expense.participants = ManyToManyField(Member, related_name="expenses_shared")`
- `Expense.created_at = DateTimeField(auto_now_add=True)`

Normalize names with `.strip()`, have direct model saves call full validation, make `Expense.clean()` reject a cross-trip payer, and connect the `m2m_changed` receiver in `ExpensesConfig.ready()` so direct and reverse participant additions reject cross-trip relationships.

- [ ] **Step 6: Create and inspect the initial migration**

Run: `python manage.py makemigrations expenses`

Expected: one `0001_initial.py` migration containing all three models and the member uniqueness constraint, with no category or payment-state fields.

- [ ] **Step 7: Run migration, checks, and model tests**

Run: `python manage.py migrate`

Run: `python manage.py check`

Run: `python manage.py test expenses.tests.test_models -v 2`

Expected: all commands succeed and all model tests pass.

- [ ] **Step 8: Commit the foundation**

```bash
git add .gitignore requirements.txt manage.py config expenses
git commit -m "feat: add SplitMate Django data model"
```

### Task 2: Exact Split and Settlement Services

**Files:**
- Create: `expenses/services.py`
- Create: `expenses/tests/test_services.py`

**Interfaces:**
- Consumes: saved `Trip`, `Member`, and `Expense` objects from Task 1.
- Produces: `allocate_amount(amount: Decimal, participant_ids: Sequence[int]) -> dict[int, Decimal]`, `calculate_trip_balances(trip: Trip) -> list[MemberBalance]`, `calculate_settlements(balances: Sequence[MemberBalance]) -> list[Settlement]`, and immutable dataclasses `MemberBalance(member, paid, should_pay, balance)` and `Settlement(debtor, creditor, amount)`.

- [ ] **Step 1: Write failing allocation tests**

Add `test_equal_split_is_exact`, asserting `Decimal("2400.00")` over four IDs yields `Decimal("600.00")` each, and `test_one_cent_split_is_conserved_and_deterministic`, asserting `Decimal("0.01")` over IDs `[30, 10, 20]` yields `{10: Decimal("0.01"), 20: Decimal("0.00"), 30: Decimal("0.00")}` and sums to `Decimal("0.01")`.

- [ ] **Step 2: Run allocation tests to verify they fail**

Run: `python manage.py test expenses.tests.test_services.AllocationTests -v 2`

Expected: FAIL because `expenses.services` does not exist.

- [ ] **Step 3: Implement exact allocation**

Implement `allocate_amount()` by quantizing to cents, converting to integer minor units, sorting participant IDs, and distributing the quotient plus one cent to the first `remainder` IDs. Raise `ValueError` for an empty participant sequence.

- [ ] **Step 4: Run allocation tests to verify they pass**

Run: `python manage.py test expenses.tests.test_services.AllocationTests -v 2`

Expected: PASS.

- [ ] **Step 5: Write failing balance and settlement tests**

Create the exact Tokyo Trip fixture using `Decimal` amounts. In `test_tokyo_trip_balances_match_spec`, assert Kai `(Decimal("2400.00"), Decimal("2800.00"), Decimal("-400.00"))`, Kevin `(Decimal("600.00"), Decimal("2800.00"), Decimal("-2200.00"))`, Amy `(Decimal("8000.00"), Decimal("2800.00"), Decimal("5200.00"))`, and Tom `(Decimal("0.00"), Decimal("2600.00"), Decimal("-2600.00"))`. In `test_tokyo_trip_settlement_matches_spec`, assert transfers `Kai -> Amy Decimal("400.00")`, `Kevin -> Amy Decimal("2200.00")`, and `Tom -> Amy Decimal("2600.00")`. Also add `test_zero_balances_create_no_transfers`.

- [ ] **Step 6: Run balance tests to verify they fail**

Run: `python manage.py test expenses.tests.test_services.BalanceAndSettlementTests -v 2`

Expected: FAIL because balance and settlement functions are missing.

- [ ] **Step 7: Implement balances and greedy settlement**

Accumulate paid and allocated shares in integer cents, return members in primary-key order, and convert values to two-place `Decimal` at the return boundary. Settle debtors and creditors in member-primary-key order using the smaller remaining absolute balance for each transfer.

- [ ] **Step 8: Run service and full tests**

Run: `python manage.py test expenses.tests.test_services -v 2`

Run: `python manage.py test -v 2`

Expected: all tests pass.

- [ ] **Step 9: Commit services**

```bash
git add expenses/services.py expenses/tests/test_services.py
git commit -m "feat: calculate exact trip settlements"
```

### Task 3: Shared UI Shell and Home Page

**Files:**
- Create: `expenses/urls.py`
- Create: `expenses/views.py`
- Modify: `config/urls.py`
- Create: `templates/base.html`
- Create: `expenses/templates/expenses/home.html`
- Create: `expenses/templates/expenses/trip_detail.html`
- Create: `expenses/static/expenses/css/style.css`
- Create: `expenses/tests/test_trip_views.py`

**Interfaces:**
- Consumes: `Trip`, `trip.members`, and `trip.expenses` from Task 1.
- Produces: named routes `expenses:home` and `expenses:trip_detail`, `home(request)`, a basic `trip_detail(request, trip_id)` member summary, shared page shell, and reusable button/card/empty-state styles.

- [ ] **Step 1: Write failing home-page tests**

Add `test_home_renders_hero_and_empty_state` and `test_home_lists_trip_member_count_and_total`. Assert the approved tagline, create action, trip name, `4 位成員`, and `NT$ 11,000` for the fixture.

- [ ] **Step 2: Run the home-page tests to verify they fail**

Run: `python manage.py test expenses.tests.test_trip_views.HomeViewTests -v 2`

Expected: FAIL because URL routing and templates are missing.

- [ ] **Step 3: Implement root routing, home view, and shared shell**

Add `django.contrib.humanize` to installed apps for `intcomma` formatting. Add `path("", include("expenses.urls"))`; define `path("", views.home, name="home")` and `path("trips/<int:trip_id>/", views.trip_detail, name="trip_detail")`. Query trips newest-first and attach member count and total expense without multiplying aggregates. Render the approved hero copy and a trip-card or empty-state collection from `home.html` extending `base.html`; each card links to a basic trip detail page that already shows the trip name and member list and returns 404 for an unknown trip. Format money with `floatformat:"-2"` followed by `intcomma` so whole-dollar fixtures render as `NT$ 11,000` while cents remain visible when present.

- [ ] **Step 4: Implement the base visual tokens and components**

Define CSS custom properties for the warm off-white canvas, ink text, muted text, green accent, borders, radii, shadows, and focus ring. Add shared container, navigation, hero, card, badge, button, money, form, error, and empty-state classes without a front-end framework.

- [ ] **Step 5: Run home and full tests**

Run: `python manage.py test expenses.tests.test_trip_views.HomeViewTests -v 2`

Run: `python manage.py test -v 2`

Expected: all tests pass.

- [ ] **Step 6: Commit the home page**

```bash
git add config/urls.py expenses/urls.py expenses/views.py templates expenses/templates/expenses/home.html expenses/templates/expenses/trip_detail.html expenses/static/expenses/css/style.css expenses/tests/test_trip_views.py
git commit -m "feat: add SplitMate home page"
```

### Task 4: Atomic Trip Creation Workflow

**Files:**
- Create: `expenses/forms.py`
- Modify: `expenses/views.py`
- Modify: `expenses/urls.py`
- Create: `expenses/templates/expenses/create_trip.html`
- Create: `expenses/static/expenses/js/app.js`
- Modify: `expenses/tests/test_trip_views.py`

**Interfaces:**
- Consumes: `Trip` and `Member` from Task 1 and shared UI from Task 3.
- Produces: `TripForm`, `MemberForm`, `MemberFormSet`, named route `expenses:create_trip`, and `create_trip(request)`.

- [ ] **Step 1: Write failing trip-creation tests**

Add `test_get_create_trip_starts_with_two_member_rows`, `test_valid_post_creates_trip_and_members_then_redirects`, `test_fewer_than_two_members_is_rejected`, `test_case_insensitive_duplicate_members_roll_back_entire_trip`, and `test_deleted_or_blank_extra_rows_do_not_count_as_members`. Assert database counts before and after invalid posts to prove atomicity.

- [ ] **Step 2: Run creation tests to verify they fail**

Run: `python manage.py test expenses.tests.test_trip_views.CreateTripViewTests -v 2`

Expected: FAIL because forms, route, view, and template are missing.

- [ ] **Step 3: Implement forms and atomic create view**

Use `ModelForm` for `Trip`, a plain `MemberForm(name)` and `formset_factory(MemberForm, extra=2, min_num=2, validate_min=True, can_delete=True)`. Add formset-level validation that strips names, ignores deleted rows, rejects blanks and case-insensitive duplicates, and requires at least two valid names. Save the trip and members inside `transaction.atomic()` and redirect to `expenses:trip_detail`.

- [ ] **Step 4: Implement the dynamic member formset UI**

Render the management form, member rows, non-form errors, an `<template>` based on `empty_form`, and add/remove controls. In `app.js`, clone the template with the next index, increment `TOTAL_FORMS`, mark persisted form rows for deletion, and remove unsaved rows without letting indices collide.

- [ ] **Step 5: Run creation and full tests**

Run: `python manage.py test expenses.tests.test_trip_views.CreateTripViewTests -v 2`

Run: `python manage.py test -v 2`

Expected: all tests pass.

- [ ] **Step 6: Commit trip creation**

```bash
git add expenses/forms.py expenses/views.py expenses/urls.py expenses/templates/expenses/create_trip.html expenses/static/expenses/js/app.js expenses/tests/test_trip_views.py
git commit -m "feat: create trips with dynamic members"
```

### Task 5: Expense Entry, Detail Cards, and Deletion

**Files:**
- Modify: `expenses/forms.py`
- Modify: `expenses/services.py`
- Modify: `expenses/views.py`
- Modify: `expenses/urls.py`
- Modify: `expenses/templates/expenses/trip_detail.html`
- Create: `expenses/templates/expenses/add_expense.html`
- Modify: `expenses/static/expenses/js/app.js`
- Create: `expenses/tests/test_expense_views.py`
- Modify: `expenses/tests/test_services.py`

**Interfaces:**
- Consumes: trip-scoped models, `allocate_amount()`, and shared UI components.
- Produces: `ExpenseForm(*args, trip: Trip, **kwargs)`, `expense_allocations(expense: Expense) -> dict[int, Decimal]`, the enriched `trip_detail(request, trip_id)`, `add_expense(request, trip_id)`, `delete_expense(request, trip_id, expense_id)`, and named routes `expenses:trip_detail`, `expenses:add_expense`, and `expenses:delete_expense`.

- [ ] **Step 1: Write failing expense-form and HTTP tests**

Add tests named `test_add_expense_choices_only_include_current_trip_members`, `test_valid_expense_saves_payer_and_participants`, `test_zero_amount_is_rejected`, `test_missing_participant_is_rejected`, `test_tampered_cross_trip_payer_is_rejected_without_write`, and `test_tampered_cross_trip_participant_is_rejected_without_write`.

- [ ] **Step 2: Run expense tests to verify they fail**

Run: `python manage.py test expenses.tests.test_expense_views -v 2`

Expected: FAIL because the form and routes do not exist.

- [ ] **Step 3: Implement the trip-scoped expense form and create view**

Initialize `paid_by` and `participants` querysets from the required `trip` argument, render participants as checkboxes, validate positive amount and at least one participant, and save the expense plus many-to-many relationship inside `transaction.atomic()`.

- [ ] **Step 4: Write failing detail and deletion tests**

Add `test_trip_detail_shows_members_total_and_empty_state`, `test_trip_detail_shows_expense_payer_participants_and_equal_share`, `test_non_divisible_expense_shows_conserved_share_range`, `test_delete_expense_requires_post`, and `test_post_delete_removes_only_expense_from_url_trip`.

- [ ] **Step 5: Run detail tests to verify they fail**

Run: `python manage.py test expenses.tests.test_expense_views.TripDetailAndDeleteTests -v 2`

Expected: FAIL because detail summaries, templates, and deletion route are missing.

- [ ] **Step 6: Implement expense summaries, detail page, and deletion**

Add `expense_allocations()` as the model-aware wrapper around `allocate_amount()`. The detail view must show exact equal shares when identical, otherwise the minimum-to-maximum cent range with a short remainder note. Scope deletion with both `trip_id` and `expense_id`, accept POST only, then redirect to that trip. Add the browser confirmation hook in `app.js`.

- [ ] **Step 7: Run expense and full tests**

Run: `python manage.py test expenses.tests.test_expense_views expenses.tests.test_services -v 2`

Run: `python manage.py test -v 2`

Expected: all tests pass.

- [ ] **Step 8: Commit expense workflows**

```bash
git add expenses/forms.py expenses/services.py expenses/views.py expenses/urls.py expenses/templates/expenses/trip_detail.html expenses/templates/expenses/add_expense.html expenses/static/expenses/js/app.js expenses/tests
git commit -m "feat: add shared expense workflow"
```

### Task 6: Settlement Page

**Files:**
- Modify: `expenses/views.py`
- Modify: `expenses/urls.py`
- Create: `expenses/templates/expenses/settlement.html`
- Modify: `expenses/static/expenses/css/style.css`
- Modify: `expenses/tests/test_expense_views.py`

**Interfaces:**
- Consumes: `calculate_trip_balances()` and `calculate_settlements()` from Task 2.
- Produces: named route `expenses:settlement` and `settlement(request, trip_id)`.

- [ ] **Step 1: Write failing settlement-page tests**

Add `test_tokyo_settlement_page_shows_all_balances_and_transfers`, asserting the four exact balances and the three exact payer arrows from the specification. Add `test_trip_without_expenses_shows_settlement_empty_state` and `test_balanced_trip_shows_no_transfer_required`.

- [ ] **Step 2: Run settlement-page tests to verify they fail**

Run: `python manage.py test expenses.tests.test_expense_views.SettlementViewTests -v 2`

Expected: FAIL because the route and template are missing.

- [ ] **Step 3: Implement the settlement view and responsive cards**

Fetch the trip or return 404, calculate balances and settlements in the service layer, and render summary cards for Paid, Should Pay, Balance, and each debtor-to-creditor transfer. Use semantic status text for receivable, payable, and settled balances rather than relying on color alone.

- [ ] **Step 4: Run settlement and full tests**

Run: `python manage.py test expenses.tests.test_expense_views.SettlementViewTests -v 2`

Run: `python manage.py test -v 2`

Expected: all tests pass.

- [ ] **Step 5: Commit settlement UI**

```bash
git add expenses/views.py expenses/urls.py expenses/templates/expenses/settlement.html expenses/static/expenses/css/style.css expenses/tests/test_expense_views.py
git commit -m "feat: show trip settlement results"
```

### Task 7: Responsive and Accessibility Verification

**Files:**
- Modify: `templates/base.html`
- Modify: `expenses/templates/expenses/home.html`
- Modify: `expenses/templates/expenses/create_trip.html`
- Modify: `expenses/templates/expenses/trip_detail.html`
- Modify: `expenses/templates/expenses/add_expense.html`
- Modify: `expenses/templates/expenses/settlement.html`
- Modify: `expenses/static/expenses/css/style.css`
- Modify: `expenses/static/expenses/js/app.js`
- Modify: `expenses/tests/test_trip_views.py`
- Modify: `expenses/tests/test_expense_views.py`

**Interfaces:**
- Consumes: all user flows from Tasks 3-6.
- Produces: complete responsive UI and stable accessibility hooks; no new domain interface.

- [ ] **Step 1: Add failing semantic and asset tests**

Assert every form input has an associated label, every page has one `<main>` and one level-one heading, validation errors use an announced error summary, and templates load the shared CSS. Assert delete controls remain real POST forms when JavaScript is unavailable.

- [ ] **Step 2: Run semantic tests to verify they fail where coverage is missing**

Run: `python manage.py test expenses.tests.test_trip_views expenses.tests.test_expense_views -v 2`

Expected: at least one new semantic assertion fails before the markup polish.

- [ ] **Step 3: Complete responsive and accessible presentation**

Add breakpoints at `48rem` and `72rem`, single-column mobile cards, two-column tablet trip cards, desktop multi-column layouts, touch targets of at least 44px, wrapping settlement rows, visible keyboard focus, reduced-motion handling, and no horizontal form overflow at 320px.

- [ ] **Step 4: Run automated tests and inspect the pages**

Run: `python manage.py test -v 2`

Run: `python manage.py check`

Start: `python manage.py runserver`

Inspect home, create-trip, trip-detail, add-expense, and settlement pages at representative desktop and mobile widths. Verify the complete Tokyo Trip flow and check for console errors, overflow, inaccessible controls, and unreadable balance states.

- [ ] **Step 5: Commit UI verification fixes**

```bash
git add templates expenses/templates expenses/static expenses/tests
git commit -m "style: polish responsive SplitMate interface"
```

### Task 8: README and Release Verification

**Files:**
- Create: `README.md`
- Modify: files from earlier tasks only if final verification exposes a defect.

**Interfaces:**
- Consumes: the completed application.
- Produces: reproducible developer setup and a verified MVP checkout.

- [ ] **Step 1: Write README setup and usage documentation**

Document SplitMate's purpose, Python 3.10+ requirement, `python -m venv .venv`, Windows activation, `pip install -r requirements.txt`, `python manage.py migrate`, `python manage.py test`, `python manage.py runserver`, SQLite storage, the five-page user flow, and the deliberate exclusion of category and payment-status features.

- [ ] **Step 2: Verify migration state and configuration**

Run: `python manage.py makemigrations --check --dry-run`

Expected: `No changes detected`.

Run: `python manage.py migrate --check`

Expected: exit code 0.

Run: `python manage.py check`

Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 3: Run the complete automated test suite**

Run: `python manage.py test -v 2`

Expected: all tests pass with exit code 0.

- [ ] **Step 4: Re-run the Tokyo Trip acceptance flow**

Create Kai, Kevin, Amy, and Tom; enter 晚餐 NT$2,400 paid by Kai for all, 飯店 NT$8,000 paid by Amy for all, and 計程車 NT$600 paid by Kevin for Kai/Kevin/Amy. Confirm total NT$11,000, the four approved balances, and transfers `Kai -> Amy 400`, `Kevin -> Amy 2200`, and `Tom -> Amy 2600`.

- [ ] **Step 5: Inspect the final diff for excluded fields and accidental artifacts**

Run: `rg -n "category|payment_status|is_paid|float\(" --glob '!docs/**' --glob '!README.md' .`

Expected: no product-code matches for excluded fields or floating-point money conversions.

Run: `git status --short`

Expected: only intentional README or final-fix changes are present; `db.sqlite3`, caches, and virtual-environment files are absent.

- [ ] **Step 6: Commit documentation and any verified final fixes**

```bash
git add README.md
git commit -m "docs: add SplitMate setup guide"
```

- [ ] **Step 7: Record final verification evidence**

Capture the exact test count, successful check output, migration status, and browser smoke-check result for the final handoff. Do not claim completion unless these fresh commands all succeed.

