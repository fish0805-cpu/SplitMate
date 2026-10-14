from django.db import migrations, models
from django.db.models.functions import Lower


class Migration(migrations.Migration):
    dependencies = [
        ("expenses", "0001_initial"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="member",
            name="unique_member_name_per_trip_ci",
        ),
        migrations.RenameModel(
            old_name="Trip",
            new_name="Activity",
        ),
        migrations.RenameField(
            model_name="member",
            old_name="trip",
            new_name="activity",
        ),
        migrations.RenameField(
            model_name="expense",
            old_name="trip",
            new_name="activity",
        ),
        migrations.AddConstraint(
            model_name="member",
            constraint=models.UniqueConstraint(
                Lower("name"),
                "activity",
                name="unique_member_name_per_activity_ci",
            ),
        ),
    ]
