from django.urls import path

from . import views


app_name = "expenses"

urlpatterns = [
    path("", views.home, name="home"),
    path("trips/<int:trip_id>/", views.trip_detail, name="trip_detail"),
]

