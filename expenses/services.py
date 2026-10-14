from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence

from .models import Activity, Expense, Member


CENT = Decimal("0.01")


@dataclass(frozen=True)
class MemberBalance:
    member: Member
    paid: Decimal
    should_pay: Decimal
    balance: Decimal


@dataclass(frozen=True)
class Settlement:
    debtor: Member
    creditor: Member
    amount: Decimal


def _to_minor_units(amount: Decimal) -> int:
    return int(amount.quantize(CENT) * 100)


def _from_minor_units(amount: int) -> Decimal:
    return (Decimal(amount) / 100).quantize(CENT)


def allocate_amount(
    amount: Decimal,
    participant_ids: Sequence[int],
) -> dict[int, Decimal]:
    ordered_ids = sorted(participant_ids)
    if not ordered_ids:
        raise ValueError("At least one participant is required.")

    minor_units = _to_minor_units(amount)
    share, remainder = divmod(minor_units, len(ordered_ids))
    return {
        participant_id: _from_minor_units(share + (index < remainder))
        for index, participant_id in enumerate(ordered_ids)
    }


def expense_allocations(expense: Expense) -> dict[int, Decimal]:
    if expense.split_method == Expense.SplitMethod.CUSTOM:
        return dict(expense.shares.values_list("member_id", "amount"))
    participant_ids = list(
        expense.participants.order_by("pk").values_list("pk", flat=True)
    )
    return allocate_amount(expense.amount, participant_ids)


def calculate_activity_balances(activity: Activity) -> list[MemberBalance]:
    members = list(activity.members.order_by("pk"))
    paid = {member.pk: 0 for member in members}
    should_pay = {member.pk: 0 for member in members}

    expenses = activity.expenses.select_related("paid_by").prefetch_related(
        "participants", "shares"
    )
    for expense in expenses:
        paid[expense.paid_by_id] += _to_minor_units(expense.amount)
        for member_id, share in expense_allocations(expense).items():
            should_pay[member_id] += _to_minor_units(share)

    return [
        MemberBalance(
            member=member,
            paid=_from_minor_units(paid[member.pk]),
            should_pay=_from_minor_units(should_pay[member.pk]),
            balance=_from_minor_units(paid[member.pk] - should_pay[member.pk]),
        )
        for member in members
    ]


def calculate_direct_payments(activity: Activity) -> list[Settlement]:
    members = {member.pk: member for member in activity.members.all()}
    debts: dict[tuple[int, int], int] = {}

    for expense in activity.expenses.prefetch_related("participants", "shares"):
        for member_id, share in expense_allocations(expense).items():
            if member_id == expense.paid_by_id:
                continue
            pair = (member_id, expense.paid_by_id)
            debts[pair] = debts.get(pair, 0) + _to_minor_units(share)

    payments = []
    for first_id, second_id in sorted({tuple(sorted(pair)) for pair in debts}):
        difference = debts.get((first_id, second_id), 0) - debts.get(
            (second_id, first_id), 0
        )
        if difference == 0:
            continue
        debtor_id, creditor_id = (
            (first_id, second_id) if difference > 0 else (second_id, first_id)
        )
        payments.append(
            Settlement(
                debtor=members[debtor_id],
                creditor=members[creditor_id],
                amount=_from_minor_units(abs(difference)),
            )
        )
    return payments


def calculate_settlements(
    balances: Sequence[MemberBalance],
) -> list[Settlement]:
    debtors = [
        [item.member, -_to_minor_units(item.balance)]
        for item in sorted(balances, key=lambda item: item.member.pk)
        if item.balance < 0
    ]
    creditors = [
        [item.member, _to_minor_units(item.balance)]
        for item in sorted(balances, key=lambda item: item.member.pk)
        if item.balance > 0
    ]
    settlements = []
    debtor_index = 0
    creditor_index = 0

    while debtor_index < len(debtors) and creditor_index < len(creditors):
        debtor, debt = debtors[debtor_index]
        creditor, credit = creditors[creditor_index]
        transfer = min(debt, credit)
        settlements.append(
            Settlement(
                debtor=debtor,
                creditor=creditor,
                amount=_from_minor_units(transfer),
            )
        )
        debtors[debtor_index][1] -= transfer
        creditors[creditor_index][1] -= transfer

        if debtors[debtor_index][1] == 0:
            debtor_index += 1
        if creditors[creditor_index][1] == 0:
            creditor_index += 1

    return settlements

