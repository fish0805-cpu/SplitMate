from django.test import TestCase
from django.urls import reverse

from expenses.models import Activity, Expense, ExpenseShare, Member, SettlementPayment


class AddExpenseViewTests(TestCase):
    def setUp(self):
        self.activity = Activity.objects.create(name="Tokyo Trip")
        self.kai = Member.objects.create(activity=self.activity, name="Kai")
        self.amy = Member.objects.create(activity=self.activity, name="Amy")
        self.other_activity = Activity.objects.create(name="Osaka Trip")
        self.outsider = Member.objects.create(activity=self.other_activity, name="Tom")
        self.url = reverse("expenses:add_expense", args=[self.activity.pk])

    def _valid_data(self):
        return {
            "title": "晚餐",
            "amount": "2400.00",
            "paid_by": str(self.kai.pk),
            "participants": [str(self.kai.pk), str(self.amy.pk)],
        }

    def test_add_expense_choices_only_include_current_activity_members(self):
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
        self.assertContains(response, 'for="id_category"')
        self.assertContains(response, 'for="id_paid_by"')
        self.assertContains(response, 'for="id_participants_0"')
        self.assertContains(response, 'name="split_method"')
        self.assertContains(response, 'data-custom-share-row')
        self.assertContains(response, f'name="share_{self.kai.pk}"')
        self.assertContains(response, "<main>", count=1)
        self.assertContains(response, "<h1>", count=1)

    def test_valid_expense_saves_payer_and_participants(self):
        response = self.client.post(self.url, self._valid_data())

        expense = Expense.objects.get(title="晚餐")
        self.assertRedirects(
            response,
            reverse("expenses:activity_detail", args=[self.activity.pk]),
        )
        self.assertEqual(expense.activity, self.activity)
        self.assertEqual(expense.paid_by, self.kai)
        self.assertQuerySetEqual(
            expense.participants.order_by("pk"),
            [self.kai, self.amy],
        )
        self.assertEqual(expense.split_method, Expense.SplitMethod.EQUAL)
        self.assertEqual(expense.category, Expense.Category.OTHER)

    def test_expense_can_save_category_and_detail_shows_it(self):
        data = self._valid_data()
        data["category"] = Expense.Category.FOOD

        response = self.client.post(self.url, data)

        self.assertRedirects(response, reverse("expenses:activity_detail", args=[self.activity.pk]))
        expense = Expense.objects.get(title="晚餐")
        self.assertEqual(expense.category, Expense.Category.FOOD)
        detail = self.client.get(reverse("expenses:activity_detail", args=[self.activity.pk]))
        self.assertContains(detail, "餐飲")

    def test_custom_split_saves_member_amounts_and_settlement(self):
        data = self._valid_data()
        data.update({
            "amount": "1000.00",
            "split_method": "custom",
            f"share_{self.kai.pk}": "300.00",
            f"share_{self.amy.pk}": "700.00",
        })

        response = self.client.post(self.url, data)

        self.assertRedirects(response, reverse("expenses:activity_detail", args=[self.activity.pk]))
        expense = Expense.objects.get(title="晚餐")
        self.assertEqual(expense.split_method, Expense.SplitMethod.CUSTOM)
        self.assertEqual(
            dict(expense.shares.values_list("member_id", "amount")),
            {self.kai.pk: 300, self.amy.pk: 700},
        )
        detail = self.client.get(reverse("expenses:activity_detail", args=[self.activity.pk]))
        self.assertContains(detail, "Kai：NT$ 300")
        self.assertContains(detail, "Amy：NT$ 700")
        settlement = self.client.get(reverse("expenses:settlement", args=[self.activity.pk]))
        self.assertContains(settlement, "Amy → Kai")
        self.assertContains(settlement, "NT$ 700")

    def test_custom_split_rejects_missing_member_amount(self):
        data = self._valid_data()
        data.update({"split_method": "custom", f"share_{self.kai.pk}": "1200.00"})

        response = self.client.post(self.url, data)

        self.assertContains(response, "請填寫每位分攤成員的金額")
        self.assertEqual(Expense.objects.count(), 0)

    def test_custom_split_rejects_amounts_that_do_not_match_total(self):
        data = self._valid_data()
        data.update({
            "split_method": "custom",
            f"share_{self.kai.pk}": "1000.00",
            f"share_{self.amy.pk}": "1000.00",
        })

        response = self.client.post(self.url, data)

        self.assertContains(response, "每人分攤金額加總必須等於支出金額")
        self.assertEqual(Expense.objects.count(), 0)

    def test_custom_split_rejects_nonpositive_member_amount(self):
        data = self._valid_data()
        data.update({
            "split_method": "custom",
            f"share_{self.kai.pk}": "0",
            f"share_{self.amy.pk}": "2400.00",
        })

        response = self.client.post(self.url, data)

        self.assertContains(response, "每位分攤成員的金額必須大於 0")
        self.assertEqual(Expense.objects.count(), 0)

    def test_equal_split_ignores_stale_custom_amount_input(self):
        data = self._valid_data()
        data.update({"split_method": "equal", f"share_{self.kai.pk}": "not-a-number"})

        response = self.client.post(self.url, data)

        self.assertRedirects(response, reverse("expenses:activity_detail", args=[self.activity.pk]))
        self.assertEqual(Expense.objects.get().split_method, Expense.SplitMethod.EQUAL)

    def test_custom_split_ignores_stale_amount_for_deselected_member(self):
        data = self._valid_data()
        data["participants"] = [str(self.kai.pk)]
        data.update({
            "split_method": "custom",
            f"share_{self.kai.pk}": "2400.00",
            f"share_{self.amy.pk}": "not-a-number",
        })

        response = self.client.post(self.url, data)

        self.assertRedirects(response, reverse("expenses:activity_detail", args=[self.activity.pk]))
        self.assertEqual(list(Expense.objects.get().shares.values_list("member_id", flat=True)), [self.kai.pk])

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

    def test_tampered_cross_activity_payer_is_rejected_without_write(self):
        data = self._valid_data()
        data["paid_by"] = str(self.outsider.pk)

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Expense.objects.count(), 0)

    def test_tampered_cross_activity_participant_is_rejected_without_write(self):
        data = self._valid_data()
        data["participants"] = [str(self.kai.pk), str(self.outsider.pk)]

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Expense.objects.count(), 0)


class ActivityDetailAndDeleteTests(TestCase):
    def setUp(self):
        self.activity = Activity.objects.create(name="Tokyo Trip")
        self.kai = Member.objects.create(activity=self.activity, name="Kai")
        self.kevin = Member.objects.create(activity=self.activity, name="Kevin")
        self.amy = Member.objects.create(activity=self.activity, name="Amy")
        self.detail_url = reverse("expenses:activity_detail", args=[self.activity.pk])

    def _create_expense(self, title="晚餐", amount="2400.00"):
        expense = Expense.objects.create(
            activity=self.activity,
            title=title,
            amount=amount,
            paid_by=self.kai,
        )
        expense.participants.add(self.kai, self.kevin, self.amy)
        return expense

    def test_activity_detail_shows_members_total_and_empty_state(self):
        response = self.client.get(self.detail_url)

        self.assertContains(response, "Tokyo Trip")
        self.assertContains(response, "3 位成員")
        self.assertContains(response, "Kai")
        self.assertContains(response, "Kevin")
        self.assertContains(response, "Amy")
        self.assertContains(response, "NT$ 0")
        self.assertContains(response, "還沒有支出")

    def test_empty_activity_shows_one_primary_add_expense_action(self):
        response = self.client.get(self.detail_url)
        html = response.content.decode()
        add_url = reverse("expenses:add_expense", args=[self.activity.pk])
        empty_state = html.split('<div class="empty-state compact-empty">', 1)[1].split(
            "</section>", 1
        )[0]

        self.assertEqual(html.count(f'href="{add_url}"'), 1)
        self.assertNotIn('class="activity-add-action', html)
        self.assertIn('class="button button-primary"', empty_state)

    def test_activity_detail_shows_expense_payer_participants_and_equal_share(self):
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
            reverse("expenses:delete_expense", args=[self.activity.pk, expense.pk]),
        )

    def test_total_card_is_between_members_and_settlement_link(self):
        self._create_expense(amount="2400.00")

        response = self.client.get(self.detail_url)
        html = response.content.decode()
        sidebar = html.split('<aside class="activity-sidebar">', 1)[1].split(
            "</aside>", 1
        )[0]

        self.assertEqual(html.count("活動總支出"), 1)
        self.assertIn("NT$ 2,400", sidebar)
        self.assertLess(sidebar.index("活動成員"), sidebar.index("活動總支出"))
        self.assertLess(sidebar.index("活動總支出"), sidebar.index("查看分帳結果"))

    def test_add_expense_action_belongs_to_expense_heading(self):
        self._create_expense()

        response = self.client.get(self.detail_url)
        html = response.content.decode()
        heading = html.split('<div class="activity-heading section-heading">', 1)[1].split(
            "</div>", 2
        )[:2]
        heading_html = "</div>".join(heading)

        self.assertIn('class="activity-add-action', heading_html)
        self.assertContains(
            response,
            f'href="{reverse("expenses:add_expense", args=[self.activity.pk])}"',
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
            args=[self.activity.pk, expense.pk],
        )

        response = self.client.get(delete_url)

        self.assertEqual(response.status_code, 405)
        self.assertTrue(Expense.objects.filter(pk=expense.pk).exists())

    def test_old_delete_form_url_still_accepts_post(self):
        expense = self._create_expense()

        response = self.client.post(
            f"/trips/{self.activity.pk}/expenses/{expense.pk}/delete/"
        )

        self.assertRedirects(response, self.detail_url)
        self.assertFalse(Expense.objects.filter(pk=expense.pk).exists())

    def test_post_delete_removes_only_expense_from_url_activity(self):
        expense = self._create_expense()
        other_activity = Activity.objects.create(name="Osaka Trip")
        outsider = Member.objects.create(activity=other_activity, name="Tom")
        other_expense = Expense.objects.create(
            activity=other_activity,
            title="車票",
            amount="1000.00",
            paid_by=outsider,
        )

        response = self.client.post(
            reverse(
                "expenses:delete_expense",
                args=[self.activity.pk, expense.pk],
            )
        )

        self.assertRedirects(response, self.detail_url)
        self.assertFalse(Expense.objects.filter(pk=expense.pk).exists())
        self.assertTrue(Expense.objects.filter(pk=other_expense.pk).exists())


class SettlementViewTests(TestCase):
    def _add_expense(self, activity, members, title, amount, payer, participants):
        expense = Expense.objects.create(
            activity=activity,
            title=title,
            amount=amount,
            paid_by=members[payer],
        )
        expense.participants.add(*(members[name] for name in participants))

    def test_tokyo_settlement_page_shows_all_balances_and_transfers(self):
        activity = Activity.objects.create(name="Tokyo Trip")
        members = {
            name: Member.objects.create(activity=activity, name=name)
            for name in ["Kai", "Kevin", "Amy", "Tom"]
        }
        self._add_expense(
            activity, members, "晚餐", "2400.00", "Kai", ["Kai", "Kevin", "Amy", "Tom"]
        )
        self._add_expense(
            activity, members, "飯店", "8000.00", "Amy", ["Kai", "Kevin", "Amy", "Tom"]
        )
        self._add_expense(
            activity, members, "計程車", "600.00", "Kevin", ["Kai", "Kevin", "Amy"]
        )

        response = self.client.get(reverse("expenses:settlement", args=[activity.pk]))

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

    def test_calculation_details_show_each_expense_and_net_balance(self):
        activity = Activity.objects.create(name="Dinner")
        kai = Member.objects.create(activity=activity, name="Kai")
        amy = Member.objects.create(activity=activity, name="Amy")
        tom = Member.objects.create(activity=activity, name="Tom")
        shared = Expense.objects.create(
            activity=activity, title="Shared meal", amount="90.00", paid_by=kai
        )
        shared.participants.add(kai, amy, tom)
        custom = Expense.objects.create(
            activity=activity, title="Set meals", amount="70.00", paid_by=tom,
            split_method=Expense.SplitMethod.CUSTOM,
        )
        custom.participants.add(amy, tom)
        ExpenseShare.objects.create(expense=custom, member=amy, amount="50.00")
        ExpenseShare.objects.create(expense=custom, member=tom, amount="20.00")

        response = self.client.get(reverse("expenses:settlement", args=[activity.pk]))

        self.assertContains(response, 'data-calculation-trigger')
        self.assertContains(response, 'data-calculation-dialog')
        self.assertContains(response, "計算明細")
        self.assertContains(response, "Shared meal")
        self.assertContains(response, "Set meals")
        self.assertContains(response, "Amy：NT$ 30")
        self.assertContains(response, "Amy：NT$ 50")
        self.assertContains(response, "實付 − 應負擔 = 淨額")
        self.assertContains(response, "Amy → Kai")
        self.assertContains(response, "Amy → Tom")

    def test_calculation_details_show_direct_payments_before_explanation(self):
        activity = Activity.objects.create(name="Dinner")
        kai = Member.objects.create(activity=activity, name="Kai")
        amy = Member.objects.create(activity=activity, name="Amy")
        expense = Expense.objects.create(
            activity=activity, title="Meal", amount="100.00", paid_by=kai
        )
        expense.participants.add(kai, amy)

        response = self.client.get(reverse("expenses:settlement", args=[activity.pk]))
        html = response.content.decode()

        self.assertContains(response, "依支出計算：誰該付給誰")
        self.assertContains(response, "Amy → Kai")
        self.assertContains(response, "NT$ 50")
        self.assertLess(html.index("依支出計算：誰該付給誰"), html.index("為什麼付款對象可能不同？"))

    def test_calculation_details_explain_when_no_direct_payment_remains(self):
        activity = Activity.objects.create(name="Dinner")
        kai = Member.objects.create(activity=activity, name="Kai")
        Member.objects.create(activity=activity, name="Amy")
        expense = Expense.objects.create(
            activity=activity, title="Coffee", amount="100.00", paid_by=kai
        )
        expense.participants.add(kai)

        response = self.client.get(reverse("expenses:settlement", args=[activity.pk]))

        self.assertContains(response, "依支出計算：誰該付給誰")
        self.assertContains(response, "沒有需要代付的金額")

    def test_calculation_details_button_is_hidden_without_expenses(self):
        activity = Activity.objects.create(name="Empty")
        Member.objects.create(activity=activity, name="Kai")

        response = self.client.get(reverse("expenses:settlement", args=[activity.pk]))

        self.assertNotContains(response, 'data-calculation-trigger')
        self.assertNotContains(response, 'data-calculation-dialog')

    def test_activity_without_expenses_shows_settlement_empty_state(self):
        activity = Activity.objects.create(name="Empty Trip")
        Member.objects.create(activity=activity, name="A")
        Member.objects.create(activity=activity, name="B")

        response = self.client.get(reverse("expenses:settlement", args=[activity.pk]))

        self.assertContains(response, "尚無可結算支出")
        self.assertNotContains(response, "付款給")
        self.assertContains(response, "<main>", count=1)
        self.assertContains(response, "<h1>", count=1)

    def test_balanced_activity_shows_no_transfer_required(self):
        activity = Activity.objects.create(name="Balanced Trip")
        member = Member.objects.create(activity=activity, name="Kai")
        Member.objects.create(activity=activity, name="Amy")
        expense = Expense.objects.create(
            activity=activity,
            title="個人咖啡",
            amount="100.00",
            paid_by=member,
        )
        expense.participants.add(member)

        response = self.client.get(reverse("expenses:settlement", args=[activity.pk]))

        self.assertContains(response, "目前不需要任何轉帳")
        self.assertNotContains(response, "付款給")

    def test_payment_status_can_be_toggled_and_persists_after_refresh(self):
        activity = Activity.objects.create(name="Dinner")
        kai = Member.objects.create(activity=activity, name="Kai")
        amy = Member.objects.create(activity=activity, name="Amy")
        expense = Expense.objects.create(
            activity=activity, title="Meal", amount="100.00", paid_by=kai
        )
        expense.participants.add(kai, amy)
        settlement_url = reverse("expenses:settlement", args=[activity.pk])
        toggle_url = reverse(
            "expenses:toggle_settlement_payment", args=[activity.pk, amy.pk, kai.pk]
        )

        response = self.client.get(settlement_url)
        self.assertContains(response, "未付款")
        self.assertContains(response, "標記為已付款")

        response = self.client.post(toggle_url)
        self.assertRedirects(response, settlement_url)
        payment = SettlementPayment.objects.get(
            activity=activity, debtor=amy, creditor=kai
        )
        self.assertTrue(payment.is_paid)
        self.assertEqual(str(payment.amount), "50.00")

        response = self.client.get(settlement_url)
        self.assertContains(response, "✓ 已付款")
        self.assertContains(response, "取消付款標記")

        self.client.post(toggle_url)
        payment.refresh_from_db()
        self.assertFalse(payment.is_paid)

    def test_payment_toggle_ignores_pairs_that_are_not_current_settlements(self):
        activity = Activity.objects.create(name="Dinner")
        kai = Member.objects.create(activity=activity, name="Kai")
        amy = Member.objects.create(activity=activity, name="Amy")
        expense = Expense.objects.create(
            activity=activity, title="Coffee", amount="100.00", paid_by=kai
        )
        expense.participants.add(kai)

        response = self.client.post(
            reverse(
                "expenses:toggle_settlement_payment", args=[activity.pk, amy.pk, kai.pk]
            )
        )

        self.assertRedirects(response, reverse("expenses:settlement", args=[activity.pk]))
        self.assertFalse(SettlementPayment.objects.exists())


