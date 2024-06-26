# Generated by Django 5.0.2 on 2024-03-20 02:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0047_alter_transaction_institution_name"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="financialaccount",
            unique_together={("person", "institution"), ("person", "name")},
        ),
        migrations.AlterUniqueTogether(
            name="subaccount",
            unique_together={
                ("account", "name", "name_official"),
                ("account", "plaid_id"),
            },
        ),
    ]
