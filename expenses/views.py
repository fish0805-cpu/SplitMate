from decimal import Decimal

from django.db.models import Count, DecimalField, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ExpenseForm, MemberFormSet, TripForm
from .models import Expense, Member, Trip
from .services import (
    calculate_settlements,
    calculate_trip_balances,
    expense_allocations,
)


MONEY_FIELD = DecimalField(max_digits=12, decimal_places=2)


def home(request):
    expense_totals = (
        Expense.objects.filter(trip_id=OuterRef("pk"))
        .values("trip_id")
        .annotate(total=Sum("amount"))
        .values("total")
    )
    trips = (
        Trip.objects.annotate(
            member_count=Count("members", distinct=True),
            total_expense=Coalesce(
                Subquery(expense_totals, output_field=MONEY_FIELD),
                Value(Decimal("0.00"), output_field=MONEY_FIELD),
            ),
        )
        .order_by("-created_at", "-pk")
    )
    return render(request, "expenses/home.html", {"trips": trips})


def create_trip(request):
    if request.method == "POST":
        trip_form = TripForm(request.POST)
        member_formset = MemberFormSet(request.POST, prefix="members")
        if trip_form.is_valid() and member_formset.is_valid():
            with transaction.atomic():
                trip = trip_form.save()
                for form in member_formset.forms:
                    if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                        continue
                    name = form.cleaned_data.get("name", "").strip()
                    if name:
                        Member.objects.create(trip=trip, name=name)
            return redirect("expenses:trip_detail", trip_id=trip.pk)
    else:
        trip_form = TripForm()
        member_formset = MemberFormSet(prefix="members")

    return render(
        request,
        "expenses/create_trip.html",
        {"trip_form": trip_form, "member_formset": member_formset},
    )


def trip_detail(request, trip_id):
    trip = get_object_or_404(
        Trip.objects.prefetch_related(
            "members",
            "expenses__paid_by",
            "expenses__participants",
        ),
        pk=trip_id,
    )
    expense_summaries = []
    total_expense = Decimal("0.00")
    for expense in trip.expenses.all():
        participants = list(expense.participants.order_by("pk"))
        allocations = expense_allocations(expense)
        shares = list(allocations.values())
        expense_summaries.append(
            {
                "expense": expense,
                "participants": participants,
                "participant_names": "、".join(
                    member.name for member in participants
                ),
                "min_share": min(shares),
                "max_share": max(shares),
                "is_equal": min(shares) == max(shares),
            }
        )
        total_expense += expense.amount
    return render(
        request,
        "expenses/trip_detail.html",
        {
            "trip": trip,
            "expense_summaries": expense_summaries,
            "total_expense": total_expense,
        },
    )


def add_expense(request, trip_id):
    trip = get_object_or_404(Trip, pk=trip_id)
    if request.method == "POST":
        expense_form = ExpenseForm(request.POST, trip=trip)
        if expense_form.is_valid():
            with transaction.atomic():
                expense = expense_form.save(commit=False)
                expense.trip = trip
                expense.save()
                expense_form.save_m2m()
            return redirect("expenses:trip_detail", trip_id=trip.pk)
    else:
        expense_form = ExpenseForm(trip=trip)

    return render(
        request,
        "expenses/add_expense.html",
        {"trip": trip, "expense_form": expense_form},
    )


@require_POST
def delete_expense(request, trip_id, expense_id):
    expense = get_object_or_404(
        Expense,
        pk=expense_id,
        trip_id=trip_id,
    )
    expense.delete()
    return redirect("expenses:trip_detail", trip_id=trip_id)


def settlement(request, trip_id):
    trip = get_object_or_404(Trip.objects.prefetch_related("members"), pk=trip_id)
    balances = calculate_trip_balances(trip)
    settlements = calculate_settlements(balances)
    balance_rows = []
    for item in balances:
        if item.balance > 0:
            status = "應收款"
        elif item.balance < 0:
            status = "應付款"
        else:
            status = "已結清"
        balance_rows.append(
            {
                "item": item,
                "status": status,
                "status_amount": abs(item.balance),
            }
        )
    return render(
        request,
        "expenses/settlement.html",
        {
            "trip": trip,
            "balance_rows": balance_rows,
            "settlements": settlements,
            "has_expenses": trip.expenses.exists(),
        },
    )

