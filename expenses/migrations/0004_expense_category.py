from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("expenses", "0003_expense_split_method_and_shares"),
    ]

    operations = [
        migrations.AddField(
            model_name="expense",
            name="category",
            field=models.CharField(
                choices=[
                    ("food", "餐飲"),
                    ("lodging", "住宿"),
                    ("transportation", "交通"),
                    ("activity", "活動"),
                    ("shopping", "購物"),
                    ("other", "其他"),
                ],
                blank=True,
                default="other",
                max_length=14,
            ),
        ),
    ]
