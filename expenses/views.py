from decimal import Decimal

from django.db.models import Count, DecimalField, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from .forms import MemberFormSet, TripForm
from .models import Expense, Member, Trip


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
    trip = get_object_or_404(Trip.objects.prefetch_related("members"), pk=trip_id)
    return render(request, "expenses/trip_detail.html", {"trip": trip})

