# Generated by Django 5.0.2 on 2024-03-31 13:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0052_budgetitem_amount"),
    ]

    operations = [
        migrations.AddField(
            model_name="transaction",
            name="ignored",
            field=models.BooleanField(default=False),
        ),
    ]
