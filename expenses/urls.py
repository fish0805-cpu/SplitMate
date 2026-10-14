from django.urls import path

from . import views


app_name = "expenses"

urlpatterns = [
    path("", views.home, name="home"),
    path("trips/new/", views.create_trip, name="create_trip"),
    path("trips/<int:trip_id>/", views.trip_detail, name="trip_detail"),
    path("trips/<int:trip_id>/expenses/new/", views.add_expense, name="add_expense"),
    path(
        "trips/<int:trip_id>/expenses/<int:expense_id>/delete/",
        views.delete_expense,
        name="delete_expense",
    ),
    path("trips/<int:trip_id>/settlement/", views.settlement, name="settlement"),
]

