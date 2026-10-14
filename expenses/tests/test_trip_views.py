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
        self.assertContains(
            response,
            '<p class="money">NT$ 11,000</p>',
            html=True,
        )
        self.assertContains(response, reverse("expenses:trip_detail", args=[trip.pk]))


class CreateTripViewTests(TestCase):
    def _post_data(self, names, deleted_indexes=()):
        data = {
            "name": "Tokyo Trip",
            "members-TOTAL_FORMS": str(len(names)),
            "members-INITIAL_FORMS": "0",
            "members-MIN_NUM_FORMS": "2",
            "members-MAX_NUM_FORMS": "1000",
        }
        for index, name in enumerate(names):
            data[f"members-{index}-name"] = name
            if index in deleted_indexes:
                data[f"members-{index}-DELETE"] = "on"
        return data

    def test_get_create_trip_starts_with_two_member_rows(self):
        response = self.client.get(reverse("expenses:create_trip"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["member_formset"].total_form_count(), 2)

    def test_valid_post_creates_trip_and_members_then_redirects(self):
        response = self.client.post(
            reverse("expenses:create_trip"),
            self._post_data(["Kai", "Kevin"]),
        )

        trip = Trip.objects.get(name="Tokyo Trip")
        self.assertRedirects(
            response,
            reverse("expenses:trip_detail", args=[trip.pk]),
        )
        self.assertQuerySetEqual(
            trip.members.order_by("pk").values_list("name", flat=True),
            ["Kai", "Kevin"],
        )

    def test_fewer_than_two_members_is_rejected(self):
        response = self.client.post(
            reverse("expenses:create_trip"),
            self._post_data(["Kai", ""]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "至少需要 2 位成員")
        self.assertEqual(Trip.objects.count(), 0)
        self.assertEqual(Member.objects.count(), 0)

    def test_case_insensitive_duplicate_members_roll_back_entire_trip(self):
        response = self.client.post(
            reverse("expenses:create_trip"),
            self._post_data(["Kai", "kai"]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "成員名稱不可重複")
        self.assertEqual(Trip.objects.count(), 0)
        self.assertEqual(Member.objects.count(), 0)

    def test_deleted_or_blank_extra_rows_do_not_count_as_members(self):
        response = self.client.post(
            reverse("expenses:create_trip"),
            self._post_data(["Kai", "Kevin", "", "Amy"], deleted_indexes=(3,)),
        )

        trip = Trip.objects.get(name="Tokyo Trip")
        self.assertRedirects(
            response,
            reverse("expenses:trip_detail", args=[trip.pk]),
        )
        self.assertQuerySetEqual(
            trip.members.order_by("pk").values_list("name", flat=True),
            ["Kai", "Kevin"],
        )

