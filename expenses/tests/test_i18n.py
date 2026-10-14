import re

from django.test import TestCase
from django.urls import reverse

from expenses.models import Activity, Expense, Member


class LanguageSwitchTests(TestCase):
    def test_default_header_offers_english_instead_of_create_activity(self):
        response = self.client.get(reverse("expenses:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<html lang="zh-Hant">')
        self.assertContains(response, 'name="language" value="en"')
        self.assertContains(response, "建立新活動")
        self.assertNotContains(response, 'class="nav-action"')

    def test_switch_to_english_returns_to_same_page_and_remembers_language(self):
        activity = Activity.objects.create(name="週五晚餐")
        Member.objects.create(activity=activity, name="Kai")
        Member.objects.create(activity=activity, name="Amy")
        path = reverse("expenses:activity_detail", args=[activity.pk])

        response = self.client.post(
            "/i18n/setlang/",
            {"language": "en", "next": path},
        )

        self.assertRedirects(response, path, fetch_redirect_response=False)
        detail = self.client.get(path)
        self.assertContains(detail, '<html lang="en">')
        self.assertContains(detail, "Activity total")
        self.assertContains(detail, "2 members")
        self.assertContains(detail, "週五晚餐")
        self.assertNotContains(detail, "活動總支出")
        home = self.client.get(reverse("expenses:home"))
        self.assertContains(home, "Create new activity")
        self.assertContains(home, 'name="language" value="zh-hant"')

    def test_switch_back_to_chinese(self):
        self.client.post(
            "/i18n/setlang/",
            {"language": "en", "next": "/"},
        )

        self.client.post(
            "/i18n/setlang/",
            {"language": "zh-hant", "next": "/"},
        )

        response = self.client.get(reverse("expenses:home"))
        self.assertContains(response, '<html lang="zh-Hant">')
        self.assertContains(response, "建立新活動")

    def test_external_next_url_is_not_used(self):
        response = self.client.post(
            "/i18n/setlang/",
            {"language": "en", "next": "https://example.com/away"},
        )

        self.assertNotEqual(response.get("Location"), "https://example.com/away")


class EnglishPageTests(TestCase):
    def setUp(self):
        self.client.post(
            "/i18n/setlang/",
            {"language": "en", "next": "/"},
        )

    def test_create_activity_form_and_errors_are_english(self):
        path = reverse("expenses:create_activity")
        response = self.client.get(path)
        self.assertContains(response, "Activity name")
        self.assertContains(response, "Member 1")
        self.assertContains(response, "Add member")

        invalid = self.client.post(path, {
            "name": "",
            "members-TOTAL_FORMS": "2",
            "members-INITIAL_FORMS": "0",
            "members-MIN_NUM_FORMS": "2",
            "members-MAX_NUM_FORMS": "1000",
            "members-0-name": "Kai",
            "members-1-name": "Amy",
        })
        self.assertContains(invalid, "Please correct the highlighted fields.")
        self.assertContains(invalid, "This field is required.")

    def test_expense_and_settlement_pages_are_english(self):
        activity = Activity.objects.create(name="Dinner")
        Member.objects.create(activity=activity, name="Kai")
        Member.objects.create(activity=activity, name="Amy")

        add_page = self.client.get(reverse("expenses:add_expense", args=[activity.pk]))
        settlement = self.client.get(reverse("expenses:settlement", args=[activity.pk]))

        self.assertContains(add_page, "Add expense")
        self.assertContains(add_page, "Payer")
        self.assertContains(add_page, "Split method")
        self.assertContains(add_page, "Custom amounts")
        self.assertContains(settlement, "Suggested payments")
        self.assertContains(settlement, "No expenses to settle yet")

    def test_calculation_details_are_english_for_activity_with_expenses(self):
        activity = Activity.objects.create(name="Dinner")
        kai = Member.objects.create(activity=activity, name="Kai")
        amy = Member.objects.create(activity=activity, name="Amy")
        expense = Expense.objects.create(
            activity=activity, title="Meal", amount="20.00", paid_by=kai
        )
        expense.participants.add(kai, amy)

        response = self.client.get(reverse("expenses:settlement", args=[activity.pk]))

        self.assertContains(response, "Calculation details")
        self.assertContains(response, "Expenses and shares")
        self.assertContains(response, "Paid − owed = net balance")
        self.assertContains(response, "By expense: who owes whom")
        self.assertNotContains(response, "計算明細")

    def test_custom_split_detail_is_english(self):
        activity = Activity.objects.create(name="Dinner")
        kai = Member.objects.create(activity=activity, name="Kai")
        amy = Member.objects.create(activity=activity, name="Amy")
        self.client.post(reverse("expenses:add_expense", args=[activity.pk]), {
            "title": "Dinner", "amount": "100.00", "paid_by": str(kai.pk),
            "participants": [str(kai.pk), str(amy.pk)], "split_method": "custom",
            f"share_{kai.pk}": "40.00", f"share_{amy.pk}": "60.00",
        })

        response = self.client.get(reverse("expenses:activity_detail", args=[activity.pk]))

        self.assertContains(response, "Custom split")
        self.assertContains(response, "Kai: NT$ 40")
        self.assertContains(response, "Amy: NT$ 60")

    def test_custom_member_errors_are_english(self):
        path = reverse("expenses:create_activity")
        data = {
            "name": "Dinner",
            "members-TOTAL_FORMS": "2",
            "members-INITIAL_FORMS": "0",
            "members-MIN_NUM_FORMS": "2",
            "members-MAX_NUM_FORMS": "1000",
            "members-0-name": "Kai",
            "members-1-name": "kai",
        }

        duplicate = self.client.post(path, data)
        self.assertContains(duplicate, "Member names must be unique.")

        data["members-1-name"] = ""
        too_few = self.client.post(path, data)
        self.assertContains(too_few, "At least 2 members are required.")

    def test_expense_dialog_and_balances_are_english(self):
        activity = Activity.objects.create(name="Friday dinner")
        kai = Member.objects.create(activity=activity, name="Kai")
        amy = Member.objects.create(activity=activity, name="Amy")
        expense = Expense.objects.create(
            activity=activity, title="Dinner", amount="100.00", paid_by=kai
        )
        expense.participants.add(kai, amy)

        detail = self.client.get(reverse("expenses:activity_detail", args=[activity.pk]))
        settlement = self.client.get(reverse("expenses:settlement", args=[activity.pk]))

        self.assertContains(detail, "Paid by Kai")
        self.assertContains(detail, "Delete this expense?")
        self.assertContains(detail, "will be removed from this activity")
        self.assertContains(settlement, "To receive")
        self.assertContains(settlement, "To pay")
        self.assertContains(settlement, "Kai")

    def test_all_public_pages_have_no_chinese_interface_copy(self):
        activity = Activity.objects.create(name="Dinner")
        kai = Member.objects.create(activity=activity, name="Kai")
        amy = Member.objects.create(activity=activity, name="Amy")
        expense = Expense.objects.create(
            activity=activity, title="Taxi", amount="20.00", paid_by=kai
        )
        expense.participants.add(kai, amy)
        paths = [
            reverse("expenses:home"),
            reverse("expenses:create_activity"),
            reverse("expenses:activity_detail", args=[activity.pk]),
            reverse("expenses:add_expense", args=[activity.pk]),
            reverse("expenses:settlement", args=[activity.pk]),
        ]

        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                html = response.content.decode().replace("中文", "")
                self.assertIsNone(re.search(r"[\u4e00-\u9fff]", html))
