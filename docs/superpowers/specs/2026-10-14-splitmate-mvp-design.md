# SplitMate MVP Design

## Purpose

SplitMate is a small Django web application for groups who share travel,
dining, or activity expenses. The MVP lets a group create a trip, add members,
record shared expenses, and calculate both individual balances and the exact
payments needed to settle the trip.

This version is the shared `main` foundation for a three-person GitHub project.
Expense categories and payment statuses are deliberately excluded so that the
other contributors can add them independently on their feature branches.

## Scope

The MVP includes:

- Trip creation with at least two members
- A home page listing trips, member counts, and total expenses
- Trip details with members and expense history
- Equal-split expenses with a payer and one or more participants
- Expense deletion
- Per-member paid, should-pay, and balance totals
- Greedy "who pays whom" settlement instructions
- Responsive Django Template UI backed by SQLite
- Automated model, validation, service, and HTTP-flow tests

The MVP excludes authentication, accounts, expense categories, payment status,
custom or percentage splits, multiple currencies, APIs, OCR, charts, exports,
real-time collaboration, and third-party front-end frameworks.

## Technical Architecture

The project uses Python, Django, Django Templates, HTML, CSS, a small amount of
vanilla JavaScript, and SQLite. It contains one Django project named `config`
and one domain app named `expenses`.

Responsibilities are divided as follows:

- `expenses/models.py` owns persistent entities and model-level invariants.
- `expenses/forms.py` owns user-input validation and trip-scoped choices.
- `expenses/views.py` coordinates HTTP requests, transactions, and rendering.
- `expenses/services.py` owns equal splitting, balance calculation, and
  settlement generation.
- `expenses/templates/expenses/` contains page templates.
- `expenses/static/expenses/` contains the shared stylesheet and the JavaScript
  used to add or remove member form rows and confirm expense deletion.
- `templates/base.html` provides the shared page shell and navigation.

Function-based views are used because the workflow contains a small number of
purpose-specific pages and the explicit control flow is easier for student
contributors to follow than a hierarchy of generic class-based views and
mixins.

## Data Model

### Trip

- `name`: required character field
- `created_at`: automatically populated creation timestamp

A trip owns many members and many expenses. Deleting a trip cascades to those
records.

### Member

- `trip`: foreign key to `Trip`
- `name`: required character field

Member names are stripped before validation. Names must be unique within a
trip, compared case-insensitively at form validation time, so payer choices and
settlement results remain unambiguous.

### Expense

- `trip`: foreign key to `Trip`
- `title`: required character field
- `amount`: positive `DecimalField` with two decimal places
- `paid_by`: foreign key to `Member`
- `participants`: many-to-many relationship to `Member`
- `created_at`: automatically populated creation timestamp

No category, payment-status, or paid-state field is present.

`Expense.clean()` rejects a payer whose trip differs from the expense trip.
The expense form restricts the payer and participants querysets to the current
trip and validates that at least one participant is selected. A many-to-many
change validator also rejects participants from another trip when the model is
modified outside the form workflow.

## User Flows

### Home

The home page contains the SplitMate hero, the primary create-trip action, and
trip cards. Each card shows the trip name, member count, total expense, and a
link to the trip. When no trips exist, the page displays an explanatory empty
state and a create action.

### Create Trip

The page renders a trip form and a Django formset containing two member rows.
JavaScript can add and remove rows while maintaining the formset management
values. Server-side validation requires a nonblank trip name and at least two
nonblank, case-insensitively distinct member names.

The view creates the trip and all members inside `transaction.atomic()`. Any
failure rolls back the entire operation. Success redirects to the new trip's
detail page.

### Trip Detail

The detail page displays the trip name, member count, member list, total
expense, and expense cards. Each expense card displays its title, amount,
payer, participants, and each participant's equal share. The page also offers
add-expense and settlement actions. An empty state replaces the expense list
when no expenses exist.

Expense deletion is submitted by POST with CSRF protection and a browser
confirmation prompt. No member or trip deletion flow is included in the MVP.

### Add Expense

The form accepts a title, positive amount, payer, and one or more participants.
Payer and participant choices contain only members from the URL's trip. The
view saves the expense and its participants atomically, then redirects to the
trip detail page. Invalid submissions preserve the entered values and show
field-specific errors.

### Settlement

The settlement page shows each member's paid amount, should-pay amount, and
balance. It also renders transfer cards containing debtor, creditor, and amount.
When the trip is already settled or has no expenses, the page displays an
appropriate empty state.

## Money and Equal-Split Algorithm

Stored amounts use `Decimal`; floating-point arithmetic is never used. Service
functions convert each amount into an integer number of cents before splitting
or accumulating it.

For an expense with `n` participants:

1. Divide the integer cent amount by `n` using quotient and remainder.
2. Give every participant the quotient.
3. Give one additional cent to the first `remainder` participants in ascending
   member-primary-key order.

This deterministic remainder policy guarantees that the participant shares for
every expense sum exactly to the stored expense amount. It also makes repeated
calculations and tests stable.

For every member:

- `paid` is the sum of expenses for which the member is `paid_by`.
- `should_pay` is the sum of that member's allocated participant shares.
- `balance` is `paid - should_pay`.

All three values remain integer cents throughout calculation and are converted
to `Decimal` only for the presentation boundary.

## Settlement Algorithm

Members with positive balances become creditors; members with negative
balances become debtors. Zero balances are omitted. Both lists retain a stable
member-primary-key order.

The service repeatedly transfers the smaller of the current debtor's remaining
debt and creditor's remaining credit. A fully resolved party advances to the
next party. Processing ends when all balances are zero. Because balances are
integer cents and expense allocations conserve every cent, the algorithm does
not require a floating-point tolerance and cannot create or lose money.

For the required Tokyo Trip fixture, the result is:

- Kai pays Amy NT$400
- Kevin pays Amy NT$2,200
- Tom pays Amy NT$2,600

## Error Handling and Data Integrity

- Unknown trip or expense URLs return Django 404 responses.
- Forms render errors beside the relevant field.
- Trip creation and expense creation use database transactions.
- Expense payer and participant membership is checked at both the form/service
  boundary and the applicable model relationship boundary.
- Destructive expense operations require POST and CSRF protection.
- Empty states cover no trips, no expenses, and no required settlement
  transfers.

## Visual Design and Responsiveness

The interface uses a warm off-white canvas, dark ink text, and a low-saturation
green accent. Generous spacing, rounded cards, soft shadows, and prominent money
figures create a modern travel-finance feel without resembling Django Admin or
an enterprise dashboard. Animation is limited to subtle interaction feedback.

Desktop layouts use multi-column cards where useful, tablets reduce the column
count, and mobile layouts use one column. Buttons retain touch-friendly heights,
forms never exceed the viewport, and expense and settlement content uses
wrapping cards instead of wide tables. Form controls have visible labels,
errors, and focus states.

## Testing Strategy

Automated Django tests cover:

- Creating trips, members, expenses, and participant relationships
- Member-to-trip relationships
- Trip creation validation and atomic persistence
- Positive expense amount and required participant validation
- Rejection of cross-trip payers and participants
- Exact equal splits
- Remainder distribution for non-divisible amounts
- Conservation of the original amount
- Paid, should-pay, and balance calculations
- Greedy settlement calculations
- The complete Tokyo Trip expected balances and transfers
- The main home, create-trip, trip-detail, add-expense, delete-expense, and
  settlement HTTP flows

Completion verification consists of migrations, `python manage.py check`, the
full `python manage.py test` suite, and smoke checks of the main pages.

## Repository and Documentation

The repository's default working branch is `main`. `requirements.txt` pins the
Django dependency range used by the project. `README.md` explains the project,
Python environment requirements, Windows virtual-environment activation,
dependency installation, migrations, tests, SQLite storage, and local server
startup.

