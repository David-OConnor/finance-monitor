# Generated by Django 5.0.2 on 2024-04-04 18:19

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0056_person_date_registered"),
    ]

    operations = [
        migrations.RenameField(
            model_name="financialaccount",
            old_name="last_refreshed",
            new_name="last_balance_refresh_attempt",
        ),
        migrations.RenameField(
            model_name="financialaccount",
            old_name="last_refreshed_successfully",
            new_name="last_balance_refresh_success",
        ),
    ]
