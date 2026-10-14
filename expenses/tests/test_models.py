from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from expenses.models import Expense, Member, Activity


class ActivityAndMemberModelTests(TestCase):
    def test_activity_can_be_created(self):
        activity = Activity.objects.create(name="Tokyo Trip")

        self.assertEqual(activity.name, "Tokyo Trip")
        self.assertIsNotNone(activity.created_at)

    def test_member_belongs_to_activity(self):
        activity = Activity.objects.create(name="Tokyo Trip")
        member = Member.objects.create(activity=activity, name="Kai")

        self.assertEqual(member.activity, activity)
        self.assertQuerySetEqual(activity.members.all(), [member])

    def test_member_name_is_unique_within_activity_case_insensitively(self):
        activity = Activity.objects.create(name="Tokyo Trip")
        Member.objects.create(activity=activity, name="Kai")

        with self.assertRaises(ValidationError):
            Member.objects.create(activity=activity, name="kai")


class ExpenseModelTests(TestCase):
    def setUp(self):
        self.activity = Activity.objects.create(name="Tokyo Trip")
        self.kai = Member.objects.create(activity=self.activity, name="Kai")
        self.amy = Member.objects.create(activity=self.activity, name="Amy")

    def test_expense_saves_payer_and_participants(self):
        expense = Expense.objects.create(
            activity=self.activity,
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

    def test_expense_rejects_payer_from_another_activity(self):
        other_activity = Activity.objects.create(name="Osaka Trip")
        outsider = Member.objects.create(activity=other_activity, name="Tom")

        with self.assertRaises(ValidationError):
            Expense.objects.create(
                activity=self.activity,
                title="飯店",
                amount=Decimal("8000.00"),
                paid_by=outsider,
            )

    def test_participants_reject_members_from_another_activity(self):
        other_activity = Activity.objects.create(name="Osaka Trip")
        outsider = Member.objects.create(activity=other_activity, name="Tom")
        expense = Expense.objects.create(
            activity=self.activity,
            title="計程車",
            amount=Decimal("600.00"),
            paid_by=self.kai,
        )

        with self.assertRaises(ValidationError):
            expense.participants.add(outsider)

