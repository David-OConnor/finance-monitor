# Generated by Django 5.0.2 on 2024-03-09 14:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0028_alter_subaccount_name_official_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="subaccount",
            name="current",
            field=models.FloatField(default=0),
        ),
    ]
