# Generated by Django 5.0.2 on 2024-03-28 23:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0051_budgetitem"),
    ]

    operations = [
        migrations.AddField(
            model_name="budgetitem",
            name="amount",
            field=models.FloatField(default=0),
            preserve_default=False,
        ),
    ]
