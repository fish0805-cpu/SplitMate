from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("expenses", "0003_expense_split_method_and_shares"),
    ]

    operations = [
        migrations.CreateModel(
            name="SettlementPayment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("is_paid", models.BooleanField(default=False)),
                ("activity", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="settlement_payments", to="expenses.activity")),
                ("creditor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="settlement_payments_to_receive", to="expenses.member")),
                ("debtor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="settlement_payments_to_make", to="expenses.member")),
            ],
        ),
        migrations.AddConstraint(
            model_name="settlementpayment",
            constraint=models.UniqueConstraint(fields=("activity", "debtor", "creditor"), name="unique_settlement_payment_per_pair"),
        ),
    ]
