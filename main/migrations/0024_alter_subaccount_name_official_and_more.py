# Generated by Django 5.0.2 on 2024-03-04 23:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0023_person_subscribed_alter_subaccount_sub_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="subaccount",
            name="name_official",
            field=models.CharField(default="", max_length=100),
        ),
        migrations.AlterField(
            model_name="subaccount",
            name="sub_type",
            field=models.IntegerField(
                choices=[
                    (0, "CHECKING"),
                    (1, "SAVINGS"),
                    (2, "DEBIT_CARD"),
                    (3, "CREDIT_CARD"),
                    (4, "T401K"),
                    (5, "STUDENT"),
                    (6, "MORTGAGE"),
                    (7, "CD"),
                    (8, "MONEY_MARKET"),
                    (9, "IRA"),
                    (10, "MUTUAL_FUND"),
                    (11, "CRYPTO"),
                    (12, "ASSET"),
                    (13, "BROKERAGE"),
                    (14, "ROTH"),
                ]
            ),
        ),
    ]
