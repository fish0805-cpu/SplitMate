from django.test import TestCase
from django.urls import reverse

from expenses.models import Expense, Member, Trip


class AddExpenseViewTests(TestCase):
    def setUp(self):
        self.trip = Trip.objects.create(name="Tokyo Trip")
        self.kai = Member.objects.create(trip=self.trip, name="Kai")
        self.amy = Member.objects.create(trip=self.trip, name="Amy")
        self.other_trip = Trip.objects.create(name="Osaka Trip")
        self.outsider = Member.objects.create(trip=self.other_trip, name="Tom")
        self.url = reverse("expenses:add_expense", args=[self.trip.pk])

    def _valid_data(self):
        return {
            "title": "晚餐",
            "amount": "2400.00",
            "paid_by": str(self.kai.pk),
            "participants": [str(self.kai.pk), str(self.amy.pk)],
        }

    def test_add_expense_choices_only_include_current_trip_members(self):
        response = self.client.get(self.url)

        form = response.context["expense_form"]
        self.assertQuerySetEqual(
            form.fields["paid_by"].queryset,
            [self.kai, self.amy],
        )
        self.assertQuerySetEqual(
            form.fields["participants"].queryset,
            [self.kai, self.amy],
        )
        self.assertContains(response, 'for="id_title"')
        self.assertContains(response, 'for="id_amount"')
        self.assertContains(response, 'for="id_paid_by"')
        self.assertContains(response, 'for="id_participants_0"')
        self.assertContains(response, "<main>", count=1)
        self.assertContains(response, "<h1>", count=1)

    def test_valid_expense_saves_payer_and_participants(self):
        response = self.client.post(self.url, self._valid_data())

        expense = Expense.objects.get(title="晚餐")
        self.assertRedirects(
            response,
            reverse("expenses:trip_detail", args=[self.trip.pk]),
        )
        self.assertEqual(expense.trip, self.trip)
        self.assertEqual(expense.paid_by, self.kai)
        self.assertQuerySetEqual(
            expense.participants.order_by("pk"),
            [self.kai, self.amy],
        )

    def test_zero_amount_is_rejected(self):
        data = self._valid_data()
        data["amount"] = "0"

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "金額必須大於 0")
        self.assertContains(response, 'role="alert"')
        self.assertEqual(Expense.objects.count(), 0)

    def test_missing_participant_is_rejected(self):
        data = self._valid_data()
        data["participants"] = []

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "至少選擇一位參與成員")
        self.assertEqual(Expense.objects.count(), 0)

    def test_tampered_cross_trip_payer_is_rejected_without_write(self):
        data = self._valid_data()
        data["paid_by"] = str(self.outsider.pk)

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Expense.objects.count(), 0)

    def test_tampered_cross_trip_participant_is_rejected_without_write(self):
        data = self._valid_data()
        data["participants"] = [str(self.kai.pk), str(self.outsider.pk)]

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Expense.objects.count(), 0)


class TripDetailAndDeleteTests(TestCase):
    def setUp(self):
        self.trip = Trip.objects.create(name="Tokyo Trip")
        self.kai = Member.objects.create(trip=self.trip, name="Kai")
        self.kevin = Member.objects.create(trip=self.trip, name="Kevin")
        self.amy = Member.objects.create(trip=self.trip, name="Amy")
        self.detail_url = reverse("expenses:trip_detail", args=[self.trip.pk])

    def _create_expense(self, title="晚餐", amount="2400.00"):
        expense = Expense.objects.create(
            trip=self.trip,
            title=title,
            amount=amount,
            paid_by=self.kai,
        )
        expense.participants.add(self.kai, self.kevin, self.amy)
        return expense

    def test_trip_detail_shows_members_total_and_empty_state(self):
        response = self.client.get(self.detail_url)

        self.assertContains(response, "Tokyo Trip")
        self.assertContains(response, "3 位成員")
        self.assertContains(response, "Kai")
        self.assertContains(response, "Kevin")
        self.assertContains(response, "Amy")
        self.assertContains(response, "NT$ 0")
        self.assertContains(response, "還沒有支出")

    def test_trip_detail_shows_expense_payer_participants_and_equal_share(self):
        expense = self._create_expense()

        response = self.client.get(self.detail_url)

        self.assertContains(response, "晚餐")
        self.assertContains(response, "NT$ 2,400")
        self.assertContains(response, "由 Kai 付款")
        self.assertContains(response, "Kai、Kevin、Amy")
        self.assertContains(response, "每人 NT$ 800")
        self.assertContains(response, 'method="post"')
        self.assertContains(
            response,
            reverse("expenses:delete_expense", args=[self.trip.pk, expense.pk]),
        )

    def test_delete_control_has_accessible_page_confirmation(self):
        expense = self._create_expense(title="晚餐")

        response = self.client.get(self.detail_url)

        self.assertContains(response, 'id="delete-expense-dialog"')
        self.assertContains(response, 'aria-labelledby="delete-expense-title"')
        self.assertContains(response, 'aria-describedby="delete-expense-description"')
        self.assertContains(response, 'data-delete-trigger data-expense-title="晚餐"')
        self.assertContains(response, f'id="delete-expense-{expense.pk}"')
        self.assertContains(response, "取消")
        self.assertContains(response, "確認刪除")

    def test_non_divisible_expense_shows_conserved_share_range(self):
        self._create_expense(title="測試零錢", amount="0.01")

        response = self.client.get(self.detail_url)

        self.assertContains(response, "NT$ 0 – 0.01")
        self.assertContains(response, "餘額依最小貨幣單位分配")

    def test_delete_expense_requires_post(self):
        expense = self._create_expense()
        delete_url = reverse(
            "expenses:delete_expense",
            args=[self.trip.pk, expense.pk],
        )

        response = self.client.get(delete_url)

        self.assertEqual(response.status_code, 405)
        self.assertTrue(Expense.objects.filter(pk=expense.pk).exists())

    def test_post_delete_removes_only_expense_from_url_trip(self):
        expense = self._create_expense()
        other_trip = Trip.objects.create(name="Osaka Trip")
        outsider = Member.objects.create(trip=other_trip, name="Tom")
        other_expense = Expense.objects.create(
            trip=other_trip,
            title="車票",
            amount="1000.00",
            paid_by=outsider,
        )

        response = self.client.post(
            reverse(
                "expenses:delete_expense",
                args=[self.trip.pk, expense.pk],
            )
        )

        self.assertRedirects(response, self.detail_url)
        self.assertFalse(Expense.objects.filter(pk=expense.pk).exists())
        self.assertTrue(Expense.objects.filter(pk=other_expense.pk).exists())


class SettlementViewTests(TestCase):
    def _add_expense(self, trip, members, title, amount, payer, participants):
        expense = Expense.objects.create(
            trip=trip,
            title=title,
            amount=amount,
            paid_by=members[payer],
        )
        expense.participants.add(*(members[name] for name in participants))

    def test_tokyo_settlement_page_shows_all_balances_and_transfers(self):
        trip = Trip.objects.create(name="Tokyo Trip")
        members = {
            name: Member.objects.create(trip=trip, name=name)
            for name in ["Kai", "Kevin", "Amy", "Tom"]
        }
        self._add_expense(
            trip, members, "晚餐", "2400.00", "Kai", ["Kai", "Kevin", "Amy", "Tom"]
        )
        self._add_expense(
            trip, members, "飯店", "8000.00", "Amy", ["Kai", "Kevin", "Amy", "Tom"]
        )
        self._add_expense(
            trip, members, "計程車", "600.00", "Kevin", ["Kai", "Kevin", "Amy"]
        )

        response = self.client.get(reverse("expenses:settlement", args=[trip.pk]))

        self.assertContains(response, "Kai")
        self.assertContains(response, "實付 NT$ 2,400")
        self.assertContains(response, "應負擔 NT$ 2,800")
        self.assertContains(response, "應付款 NT$ 400")
        self.assertContains(response, "實付 NT$ 600")
        self.assertContains(response, "應付款 NT$ 2,200")
        self.assertContains(response, "實付 NT$ 8,000")
        self.assertContains(response, "應收款 NT$ 5,200")
        self.assertContains(response, "實付 NT$ 0")
        self.assertContains(response, "應負擔 NT$ 2,600")
        self.assertContains(response, "應付款 NT$ 2,600")
        self.assertContains(response, "Kai → Amy")
        self.assertContains(response, "Kevin → Amy")
        self.assertContains(response, "Tom → Amy")

    def test_trip_without_expenses_shows_settlement_empty_state(self):
        trip = Trip.objects.create(name="Empty Trip")
        Member.objects.create(trip=trip, name="A")
        Member.objects.create(trip=trip, name="B")

        response = self.client.get(reverse("expenses:settlement", args=[trip.pk]))

        self.assertContains(response, "尚無可結算支出")
        self.assertNotContains(response, "付款給")
        self.assertContains(response, "<main>", count=1)
        self.assertContains(response, "<h1>", count=1)

    def test_balanced_trip_shows_no_transfer_required(self):
        trip = Trip.objects.create(name="Balanced Trip")
        member = Member.objects.create(trip=trip, name="Kai")
        Member.objects.create(trip=trip, name="Amy")
        expense = Expense.objects.create(
            trip=trip,
            title="個人咖啡",
            amount="100.00",
            paid_by=member,
        )
        expense.participants.add(member)

        response = self.client.get(reverse("expenses:settlement", args=[trip.pk]))

        self.assertContains(response, "目前不需要任何轉帳")
        self.assertNotContains(response, "付款給")


