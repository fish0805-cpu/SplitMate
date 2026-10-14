from decimal import Decimal

from django.db.models import Count, DecimalField, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, render

from .models import Expense, Trip


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


def trip_detail(request, trip_id):
    trip = get_object_or_404(Trip.objects.prefetch_related("members"), pk=trip_id)
    return render(request, "expenses/trip_detail.html", {"trip": trip})

