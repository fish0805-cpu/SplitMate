from decimal import Decimal

from django.test import SimpleTestCase, TestCase

from expenses import services
from expenses.models import Expense, Member, Trip


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
        self.trip = Trip.objects.create(name="Tokyo Trip")
        self.members = {
            name: Member.objects.create(trip=self.trip, name=name)
            for name in ["Kai", "Kevin", "Amy", "Tom"]
        }
        self._add_expense("晚餐", "2400.00", "Kai", ["Kai", "Kevin", "Amy", "Tom"])
        self._add_expense("飯店", "8000.00", "Amy", ["Kai", "Kevin", "Amy", "Tom"])
        self._add_expense("計程車", "600.00", "Kevin", ["Kai", "Kevin", "Amy"])

    def _add_expense(self, title, amount, payer, participants):
        expense = Expense.objects.create(
            trip=self.trip,
            title=title,
            amount=Decimal(amount),
            paid_by=self.members[payer],
        )
        expense.participants.add(*(self.members[name] for name in participants))

    def test_tokyo_trip_balances_match_spec(self):
        balances = services.calculate_trip_balances(self.trip)

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

    def test_tokyo_trip_settlement_matches_spec(self):
        balances = services.calculate_trip_balances(self.trip)

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
        empty_trip = Trip.objects.create(name="Empty Trip")
        Member.objects.create(trip=empty_trip, name="A")
        Member.objects.create(trip=empty_trip, name="B")
        balances = services.calculate_trip_balances(empty_trip)

        self.assertEqual(services.calculate_settlements(balances), [])

