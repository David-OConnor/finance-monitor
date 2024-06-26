# Generated by Django 5.0.2 on 2024-02-29 14:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="financialaccount",
            name="name",
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name="subaccount",
            name="name",
            field=models.CharField(max_length=50),
        ),
        migrations.AlterField(
            model_name="subaccount",
            name="name_official",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
