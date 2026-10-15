from dataclasses import replace
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, DecimalField, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from .forms import ActivityForm, ExpenseForm, MemberFormSet
from .models import Activity, Expense, ExpenseShare, Member, SettlementPayment
from .services import (
    calculate_activity_balances,
    calculate_direct_payments,
    calculate_settlements,
    expense_allocations,
)


MONEY_FIELD = DecimalField(max_digits=12, decimal_places=2)


def home(request):
    expense_totals = (
        Expense.objects.filter(activity_id=OuterRef("pk"))
        .values("activity_id")
        .annotate(total=Sum("amount"))
        .values("total")
    )
    activities = list(
        Activity.objects.annotate(
            member_count=Count("members", distinct=True),
            expense_count=Count("expenses", distinct=True),
            total_expense=Coalesce(
                Subquery(expense_totals, output_field=MONEY_FIELD),
                Value(Decimal("0.00"), output_field=MONEY_FIELD),
            ),
        )
        .order_by("-created_at", "-pk")
    )
    return render(
        request,
        "expenses/home.html",
        {
            "activities": activities,
            "latest_activity": activities[0] if activities else None,
        },
    )


def create_activity(request):
    if request.method == "POST":
        activity_form = ActivityForm(request.POST)
        member_formset = MemberFormSet(request.POST, prefix="members")
        if activity_form.is_valid() and member_formset.is_valid():
            with transaction.atomic():
                activity = activity_form.save()
                for form in member_formset.forms:
                    if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                        continue
                    name = form.cleaned_data.get("name", "").strip()
                    if name:
                        Member.objects.create(activity=activity, name=name)
            return redirect("expenses:activity_detail", activity_id=activity.pk)
    else:
        activity_form = ActivityForm()
        member_formset = MemberFormSet(prefix="members")

    return render(
        request,
        "expenses/create_activity.html",
        {"activity_form": activity_form, "member_formset": member_formset},
    )


def activity_detail(request, activity_id):
    activity = get_object_or_404(
        Activity.objects.prefetch_related(
            "members",
            "expenses__paid_by",
            "expenses__participants",
            "expenses__shares",
        ),
        pk=activity_id,
    )
    expense_summaries = []
    total_expense = Decimal("0.00")
    for expense in activity.expenses.all():
        participants = list(expense.participants.order_by("pk"))
        allocations = expense_allocations(expense)
        shares = list(allocations.values())
        expense_summaries.append(
            {
                "expense": expense,
                "participants": participants,
                "participant_names": _("、").join(
                    member.name for member in participants
                ),
                "min_share": min(shares),
                "max_share": max(shares),
                "is_equal": min(shares) == max(shares),
                "custom_shares": [
                    {"member": member, "amount": allocations[member.pk]}
                    for member in participants
                ] if expense.split_method == Expense.SplitMethod.CUSTOM else [],
            }
        )
        total_expense += expense.amount
    return render(
        request,
        "expenses/activity_detail.html",
        {
            "activity": activity,
            "expense_summaries": expense_summaries,
            "total_expense": total_expense,
        },
    )


def add_expense(request, activity_id):
    activity = get_object_or_404(Activity, pk=activity_id)
    if request.method == "POST":
        expense_form = ExpenseForm(request.POST, activity=activity)
        if expense_form.is_valid():
            with transaction.atomic():
                expense = expense_form.save(commit=False)
                expense.activity = activity
                expense.save()
                expense_form.save_m2m()
                if expense.split_method == Expense.SplitMethod.CUSTOM:
                    ExpenseShare.objects.bulk_create(
                        ExpenseShare(expense=expense, member_id=member_id, amount=amount)
                        for member_id, amount in expense_form.custom_shares.items()
                    )
            return redirect("expenses:activity_detail", activity_id=activity.pk)
    else:
        expense_form = ExpenseForm(activity=activity)

    return render(
        request,
        "expenses/add_expense.html",
        {"activity": activity, "expense_form": expense_form},
    )


@require_POST
def delete_expense(request, activity_id, expense_id):
    expense = get_object_or_404(
        Expense,
        pk=expense_id,
        activity_id=activity_id,
    )
    expense.delete()
    return redirect("expenses:activity_detail", activity_id=activity_id)


def settlement(request, activity_id):
    activity = get_object_or_404(Activity.objects.prefetch_related("members"), pk=activity_id)
    balances = calculate_activity_balances(activity)
    settlements = calculate_settlements(balances)
    paid_settlements = {
        (payment.debtor_id, payment.creditor_id, payment.amount)
        for payment in SettlementPayment.objects.filter(activity=activity, is_paid=True)
    }
    settlements = [
        replace(
            transfer,
            is_paid=(
                transfer.debtor.pk,
                transfer.creditor.pk,
                transfer.amount,
            ) in paid_settlements,
        )
        for transfer in settlements
    ]
    direct_payments = calculate_direct_payments(activity)
    calculation_expenses = []
    for expense in activity.expenses.select_related("paid_by").prefetch_related(
        "participants", "shares"
    ):
        allocations = expense_allocations(expense)
        calculation_expenses.append(
            {
                "expense": expense,
                "shares": [
                    {"member": member, "amount": allocations[member.pk]}
                    for member in expense.participants.order_by("pk")
                ],
            }
        )
    balance_rows = []
    for item in balances:
        if item.balance > 0:
            status_code = "positive"
            status = _("應收款")
        elif item.balance < 0:
            status_code = "negative"
            status = _("應付款")
        else:
            status_code = "settled"
            status = _("已結清")
        balance_rows.append(
            {
                "item": item,
                "status": status,
                "status_code": status_code,
                "status_amount": abs(item.balance),
            }
        )
    return render(
        request,
        "expenses/settlement.html",
        {
            "activity": activity,
            "balance_rows": balance_rows,
            "settlements": settlements,
            "direct_payments": direct_payments,
            "calculation_expenses": calculation_expenses,
            "has_expenses": bool(calculation_expenses),
        },
    )


@require_POST
def toggle_settlement_payment(request, activity_id, debtor_id, creditor_id):
    activity = get_object_or_404(Activity.objects.prefetch_related("members"), pk=activity_id)
    transfer = next(
        (
            settlement
            for settlement in calculate_settlements(calculate_activity_balances(activity))
            if settlement.debtor.pk == debtor_id and settlement.creditor.pk == creditor_id
        ),
        None,
    )
    if transfer is None:
        return redirect("expenses:settlement", activity_id=activity.pk)

    with transaction.atomic():
        payment, created = SettlementPayment.objects.get_or_create(
            activity=activity,
            debtor_id=debtor_id,
            creditor_id=creditor_id,
            defaults={"amount": transfer.amount, "is_paid": True},
        )
        if not created:
            if payment.amount != transfer.amount:
                payment.amount = transfer.amount
                payment.is_paid = True
            else:
                payment.is_paid = not payment.is_paid
            payment.save(update_fields=["amount", "is_paid"])

    return redirect("expenses:settlement", activity_id=activity.pk)

