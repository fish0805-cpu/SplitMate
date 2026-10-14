from decimal import Decimal

from django.test import SimpleTestCase, TestCase

from expenses import services
from expenses.models import Expense, ExpenseShare, Member, Activity


class AllocationTests(SimpleTestCase):
    def test_equal_split_is_exact(self):
        allocation = services.allocate_amount(Decimal("2400.00"), [4, 1, 3, 2])

        self.assertEqual(
            allocation,
            {
                1: Decimal("600.00"),
                2: Decimal("600.00"),
                3: Decimal("600.00"),
                4: Decimal("600.00"),
            },
        )

    def test_one_cent_split_is_conserved_and_deterministic(self):
        allocation = services.allocate_amount(Decimal("0.01"), [30, 10, 20])

        self.assertEqual(
            allocation,
            {
                10: Decimal("0.01"),
                20: Decimal("0.00"),
                30: Decimal("0.00"),
            },
        )
        self.assertEqual(sum(allocation.values()), Decimal("0.01"))


class BalanceAndSettlementTests(TestCase):
    def setUp(self):
        self.activity = Activity.objects.create(name="Tokyo Trip")
        self.members = {
            name: Member.objects.create(activity=self.activity, name=name)
            for name in ["Kai", "Kevin", "Amy", "Tom"]
        }
        self._add_expense("晚餐", "2400.00", "Kai", ["Kai", "Kevin", "Amy", "Tom"])
        self._add_expense("飯店", "8000.00", "Amy", ["Kai", "Kevin", "Amy", "Tom"])
        self._add_expense("計程車", "600.00", "Kevin", ["Kai", "Kevin", "Amy"])

    def _add_expense(self, title, amount, payer, participants):
        expense = Expense.objects.create(
            activity=self.activity,
            title=title,
            amount=Decimal(amount),
            paid_by=self.members[payer],
        )
        expense.participants.add(*(self.members[name] for name in participants))

    def test_tokyo_activity_balances_match_spec(self):
        balances = services.calculate_activity_balances(self.activity)

        actual = {
            item.member.name: (item.paid, item.should_pay, item.balance)
            for item in balances
        }
        self.assertEqual(
            actual,
            {
                "Kai": (
                    Decimal("2400.00"),
                    Decimal("2800.00"),
                    Decimal("-400.00"),
                ),
                "Kevin": (
                    Decimal("600.00"),
                    Decimal("2800.00"),
                    Decimal("-2200.00"),
                ),
                "Amy": (
                    Decimal("8000.00"),
                    Decimal("2800.00"),
                    Decimal("5200.00"),
                ),
                "Tom": (
                    Decimal("0.00"),
                    Decimal("2600.00"),
                    Decimal("-2600.00"),
                ),
            },
        )

    def test_tokyo_activity_settlement_matches_spec(self):
        balances = services.calculate_activity_balances(self.activity)

        transfers = services.calculate_settlements(balances)

        self.assertEqual(
            [
                (item.debtor.name, item.creditor.name, item.amount)
                for item in transfers
            ],
            [
                ("Kai", "Amy", Decimal("400.00")),
                ("Kevin", "Amy", Decimal("2200.00")),
                ("Tom", "Amy", Decimal("2600.00")),
            ],
        )

    def test_zero_balances_create_no_transfers(self):
        empty_activity = Activity.objects.create(name="Empty Trip")
        Member.objects.create(activity=empty_activity, name="A")
        Member.objects.create(activity=empty_activity, name="B")
        balances = services.calculate_activity_balances(empty_activity)

        self.assertEqual(services.calculate_settlements(balances), [])

    def test_expense_allocations_use_saved_participants(self):
        expense = self.activity.expenses.get(title="計程車")

        allocations = services.expense_allocations(expense)

        self.assertEqual(
            allocations,
            {
                self.members["Kai"].pk: Decimal("200.00"),
                self.members["Kevin"].pk: Decimal("200.00"),
                self.members["Amy"].pk: Decimal("200.00"),
            },
        )


class DirectPaymentTests(TestCase):
    def test_opposite_expense_debts_cancel_only_within_the_same_pair(self):
        activity = Activity.objects.create(name="Dinner")
        members = {
            name: Member.objects.create(activity=activity, name=name)
            for name in ["Kai", "Kevin", "Amy", "Tom"]
        }

        def add_expense(title, amount, payer, participants):
            expense = Expense.objects.create(
                activity=activity, title=title, amount=amount, paid_by=members[payer]
            )
            expense.participants.add(*(members[name] for name in participants))

        add_expense("Shared dinner", "1200.00", "Kai", members)
        add_expense("Kai's dinner", "500.00", "Tom", ["Kai"])
        add_expense("Set meals", "400.00", "Kevin", ["Kai", "Amy"])

        payments = services.calculate_direct_payments(activity)

        self.assertEqual(
            {(p.debtor.name, p.creditor.name, p.amount) for p in payments},
            {
                ("Amy", "Kai", Decimal("300.00")),
                ("Amy", "Kevin", Decimal("200.00")),
                ("Kevin", "Kai", Decimal("100.00")),
                ("Kai", "Tom", Decimal("200.00")),
            },
        )

    def test_custom_shares_and_self_paid_portions_create_only_actual_debts(self):
        activity = Activity.objects.create(name="Dinner")
        kai = Member.objects.create(activity=activity, name="Kai")
        amy = Member.objects.create(activity=activity, name="Amy")
        meal = Expense.objects.create(
            activity=activity, title="Set meals", amount="100.00", paid_by=kai,
            split_method=Expense.SplitMethod.CUSTOM,
        )
        meal.participants.add(kai, amy)
        ExpenseShare.objects.create(expense=meal, member=kai, amount="30.00")
        ExpenseShare.objects.create(expense=meal, member=amy, amount="70.00")
        return_payment = Expense.objects.create(
            activity=activity, title="Taxi", amount="20.00", paid_by=amy
        )
        return_payment.participants.add(kai)

        payments = services.calculate_direct_payments(activity)

        self.assertEqual(
            [(p.debtor.name, p.creditor.name, p.amount) for p in payments],
            [("Amy", "Kai", Decimal("50.00"))],
        )

    def test_no_expenses_create_no_direct_payments(self):
        activity = Activity.objects.create(name="Empty")
        Member.objects.create(activity=activity, name="Kai")

        self.assertEqual(services.calculate_direct_payments(activity), [])

