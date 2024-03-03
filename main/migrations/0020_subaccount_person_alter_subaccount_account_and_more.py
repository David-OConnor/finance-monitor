# Generated by Django 5.0.2 on 2024-03-03 20:26

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0019_person_email_verified"),
    ]

    operations = [
        migrations.AddField(
            model_name="subaccount",
            name="person",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="subaccounts_manual",
                to="main.person",
            ),
        ),
        migrations.AlterField(
            model_name="subaccount",
            name="account",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="sub_accounts",
                to="main.financialaccount",
            ),
        ),
        migrations.AlterField(
            model_name="subaccount",
            name="plaid_id",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name="transaction",
            name="plaid_id",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]