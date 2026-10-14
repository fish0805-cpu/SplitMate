from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from expenses.models import Activity, Expense, Member


class ExpenseAdminTests(TestCase):
    def setUp(self):
        self.activity = Activity.objects.create(name="Dinner")
        self.kai = Member.objects.create(activity=self.activity, name="Kai")
        self.amy = Member.objects.create(activity=self.activity, name="Amy")
        admin = get_user_model().objects.create_superuser(
            username="admin", email="admin@example.com", password="password"
        )
        self.client.force_login(admin)

    def test_admin_cannot_create_custom_split_without_member_shares(self):
        response = self.client.post(reverse("admin:expenses_expense_add"), {
            "activity": str(self.activity.pk),
            "title": "Dinner",
            "amount": "100.00",
            "paid_by": str(self.kai.pk),
            "participants": [str(self.kai.pk), str(self.amy.pk)],
            "split_method": "custom",
            "_save": "Save",
        })

        self.assertEqual(response.status_code, 302)
        expense = Expense.objects.get(title="Dinner")
        self.assertEqual(expense.split_method, Expense.SplitMethod.EQUAL)

    def test_admin_cannot_change_custom_split_without_revalidating_shares(self):
        expense = Expense.objects.create(
            activity=self.activity, title="Dinner", amount="100.00",
            paid_by=self.kai, split_method=Expense.SplitMethod.CUSTOM,
        )
        expense.participants.add(self.kai, self.amy)
        expense.shares.create(member=self.kai, amount="40.00")
        expense.shares.create(member=self.amy, amount="60.00")

        response = self.client.post(reverse("admin:expenses_expense_change", args=[expense.pk]), {
            "activity": str(self.activity.pk),
            "title": "Changed dinner",
            "amount": "200.00",
            "paid_by": str(self.kai.pk),
            "participants": [str(self.kai.pk), str(self.amy.pk)],
            "split_method": "equal",
            "_save": "Save",
        })

        expense.refresh_from_db()
        self.assertNotEqual(response.status_code, 302)
        self.assertEqual(expense.title, "Dinner")
        self.assertEqual(str(expense.amount), "100.00")
        self.assertEqual(expense.split_method, Expense.SplitMethod.CUSTOM)
