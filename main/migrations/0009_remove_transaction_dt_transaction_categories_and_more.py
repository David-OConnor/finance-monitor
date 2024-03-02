# Generated by Django 5.0.2 on 2024-03-01 01:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0008_alter_financialaccount_plaid_cursor"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="transaction",
            name="dt",
        ),
        migrations.AddField(
            model_name="transaction",
            name="categories",
            field=models.JSONField(default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="transaction",
            name="date",
            field=models.DateField(default="1999-09-09"),
            preserve_default=False,
        ),
    ]