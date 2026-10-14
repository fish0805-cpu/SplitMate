from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from expenses.models import Expense, Member, Trip


class TripAndMemberModelTests(TestCase):
    def test_trip_can_be_created(self):
        trip = Trip.objects.create(name="Tokyo Trip")

        self.assertEqual(trip.name, "Tokyo Trip")
        self.assertIsNotNone(trip.created_at)

    def test_member_belongs_to_trip(self):
        trip = Trip.objects.create(name="Tokyo Trip")
        member = Member.objects.create(trip=trip, name="Kai")

        self.assertEqual(member.trip, trip)
        self.assertQuerySetEqual(trip.members.all(), [member])

    def test_member_name_is_unique_within_trip_case_insensitively(self):
        trip = Trip.objects.create(name="Tokyo Trip")
        Member.objects.create(trip=trip, name="Kai")

        with self.assertRaises(ValidationError):
            Member.objects.create(trip=trip, name="kai")


class ExpenseModelTests(TestCase):
    def setUp(self):
        self.trip = Trip.objects.create(name="Tokyo Trip")
        self.kai = Member.objects.create(trip=self.trip, name="Kai")
        self.amy = Member.objects.create(trip=self.trip, name="Amy")

    def test_expense_saves_payer_and_participants(self):
        expense = Expense.objects.create(
            trip=self.trip,
            title="晚餐",
            amount=Decimal("2400.00"),
            paid_by=self.kai,
        )
        expense.participants.add(self.kai, self.amy)

        self.assertEqual(expense.paid_by, self.kai)
        self.assertQuerySetEqual(
            expense.participants.order_by("pk"),
            [self.kai, self.amy],
        )

    def test_expense_rejects_payer_from_another_trip(self):
        other_trip = Trip.objects.create(name="Osaka Trip")
        outsider = Member.objects.create(trip=other_trip, name="Tom")

        with self.assertRaises(ValidationError):
            Expense.objects.create(
                trip=self.trip,
                title="飯店",
                amount=Decimal("8000.00"),
                paid_by=outsider,
            )

    def test_participants_reject_members_from_another_trip(self):
        other_trip = Trip.objects.create(name="Osaka Trip")
        outsider = Member.objects.create(trip=other_trip, name="Tom")
        expense = Expense.objects.create(
            trip=self.trip,
            title="計程車",
            amount=Decimal("600.00"),
            paid_by=self.kai,
        )

        with self.assertRaises(ValidationError):
            expense.participants.add(outsider)

