# Generated by Django 5.0.2 on 2024-04-05 23:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0059_financialaccount_needs_attention"),
    ]

    operations = [
        migrations.AlterField(
            model_name="financialaccount",
            name="access_token",
            field=models.CharField(max_length=100, unique=True),
        ),
    ]
