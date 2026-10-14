from decimal import Decimal

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("expenses", "0002_activity_naming"),
    ]

    operations = [
        migrations.AddField(
            model_name="expense",
            name="split_method",
            field=models.CharField(
                choices=[("equal", "平均分攤"), ("custom", "自訂金額")],
                default="equal",
                max_length=6,
            ),
        ),
        migrations.CreateModel(
            name="ExpenseShare",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal("0.01"))])),
                ("expense", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="shares", to="expenses.expense")),
                ("member", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="expenses.member")),
            ],
        ),
        migrations.AddConstraint(
            model_name="expenseshare",
            constraint=models.UniqueConstraint(fields=("expense", "member"), name="unique_member_share_per_expense"),
        ),
    ]
