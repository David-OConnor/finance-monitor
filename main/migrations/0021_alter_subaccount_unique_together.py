# Generated by Django 5.0.2 on 2024-03-03 21:18

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0020_subaccount_person_alter_subaccount_account_and_more"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="subaccount",
            unique_together={("account", "name"), ("account", "plaid_id")},
        ),
    ]
