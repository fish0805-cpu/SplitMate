from django.urls import path
from django.views.generic import RedirectView

from . import views


app_name = "expenses"

urlpatterns = [
    path("", views.home, name="home"),
    path("activities/new/", views.create_activity, name="create_activity"),
    path("activities/<int:activity_id>/", views.activity_detail, name="activity_detail"),
    path("activities/<int:activity_id>/expenses/new/", views.add_expense, name="add_expense"),
    path(
        "activities/<int:activity_id>/expenses/<int:expense_id>/edit/",
        views.edit_expense,
        name="edit_expense",
    ),
    path(
        "activities/<int:activity_id>/expenses/<int:expense_id>/delete/",
        views.delete_expense,
        name="delete_expense",
    ),
    path("activities/<int:activity_id>/settlement/", views.settlement, name="settlement"),
    path(
        "activities/<int:activity_id>/settlement/payments/<int:debtor_id>/<int:creditor_id>/",
        views.toggle_settlement_payment,
        name="toggle_settlement_payment",
    ),
    path(
        "trips/new/",
        RedirectView.as_view(pattern_name="expenses:create_activity", permanent=False),
    ),
    path(
        "trips/<int:activity_id>/",
        RedirectView.as_view(pattern_name="expenses:activity_detail", permanent=False),
    ),
    path(
        "trips/<int:activity_id>/expenses/new/",
        RedirectView.as_view(pattern_name="expenses:add_expense", permanent=False),
    ),
    path(
        "trips/<int:activity_id>/expenses/<int:expense_id>/edit/",
        views.edit_expense,
    ),
    path(
        "trips/<int:activity_id>/expenses/<int:expense_id>/delete/",
        views.delete_expense,
    ),
    path(
        "trips/<int:activity_id>/settlement/",
        RedirectView.as_view(pattern_name="expenses:settlement", permanent=False),
    ),
]

