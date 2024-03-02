# Generated by Django 5.0.2 on 2024-03-02 03:58

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0014_alter_transaction_account"),
    ]

    operations = [
        migrations.AddField(
            model_name="transaction",
            name="notes",
            field=models.CharField(default="", max_length=100),
        ),
        migrations.AddField(
            model_name="transaction",
            name="person",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="transactions_without_account",
                to="main.person",
            ),
        ),
        migrations.AlterField(
            model_name="transaction",
            name="account",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="transactions",
                to="main.financialaccount",
            ),
        ),
    ]
