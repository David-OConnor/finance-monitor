# Generated by Django 5.0.2 on 2024-03-01 03:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0011_transaction_plaid_id_alter_transaction_account"),
    ]

    operations = [
        migrations.AddField(
            model_name="subaccount",
            name="ignored",
            field=models.BooleanField(default=False),
        ),
    ]
