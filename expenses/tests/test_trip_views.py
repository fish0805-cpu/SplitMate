from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from expenses.models import Expense, Member, Trip


class HomeViewTests(TestCase):
    def test_home_renders_hero_and_empty_state(self):
        response = self.client.get(reverse("expenses:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Split expenses.")
        self.assertContains(response, "Not friendships.")
        self.assertContains(response, "建立新旅程")
        self.assertContains(response, "還沒有旅程")

    def test_home_lists_trip_member_count_and_total(self):
        trip = Trip.objects.create(name="Tokyo Trip")
        members = [
            Member.objects.create(trip=trip, name=name)
            for name in ["Kai", "Kevin", "Amy", "Tom"]
        ]
        for title, amount, payer in [
            ("晚餐", "2400.00", members[0]),
            ("飯店", "8000.00", members[2]),
            ("計程車", "600.00", members[1]),
        ]:
            Expense.objects.create(
                trip=trip,
                title=title,
                amount=Decimal(amount),
                paid_by=payer,
            )

        response = self.client.get(reverse("expenses:home"))

        self.assertContains(response, "Tokyo Trip")
        self.assertContains(response, "4 位成員")
        self.assertContains(response, "NT$ 11,000")
        self.assertContains(response, reverse("expenses:trip_detail", args=[trip.pk]))

