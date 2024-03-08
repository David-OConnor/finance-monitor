# Generated by Django 5.0.2 on 2024-03-07 14:22

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0025_alter_transaction_unique_together"),
    ]

    operations = [
        migrations.CreateModel(
            name="SnapshotAccount",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("account_name", models.CharField(max_length=30)),
                ("dt", models.DateTimeField()),
                ("value", models.FloatField()),
                (
                    "account",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="snapshots",
                        to="main.subaccount",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="SnapshotPerson",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("dt", models.DateTimeField()),
                ("value", models.FloatField()),
                (
                    "person",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="snapshots",
                        to="main.person",
                    ),
                ),
            ],
        ),
        migrations.DeleteModel(
            name="NetWorthSnapshot",
        ),
    ]