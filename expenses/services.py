from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence

from .models import Member, Trip


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


def calculate_trip_balances(trip: Trip) -> list[MemberBalance]:
    members = list(trip.members.order_by("pk"))
    paid = {member.pk: 0 for member in members}
    should_pay = {member.pk: 0 for member in members}

    expenses = trip.expenses.select_related("paid_by").prefetch_related(
        "participants"
    )
    for expense in expenses:
        paid[expense.paid_by_id] += _to_minor_units(expense.amount)
        participant_ids = list(
            expense.participants.order_by("pk").values_list("pk", flat=True)
        )
        for member_id, share in allocate_amount(
            expense.amount, participant_ids
        ).items():
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

