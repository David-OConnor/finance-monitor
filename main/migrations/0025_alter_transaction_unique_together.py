# Generated by Django 5.0.2 on 2024-03-05 02:31

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0024_alter_subaccount_name_official_and_more"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="transaction",
            unique_together={
                ("date", "description", "amount", "account"),
                ("date", "description", "amount", "person"),
            },
        ),
    ]