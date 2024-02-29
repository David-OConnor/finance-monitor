# Generated by Django 4.2.4 on 2024-02-29 03:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0005_subaccount"),
    ]

    operations = [
        migrations.AddField(
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
                ],
                default=1,
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="subaccount",
            name="plaid_id_persistent",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name="subaccount",
            name="type",
            field=models.IntegerField(
                choices=[(1, "DEPOSITORY"), (2, "INVESTMENT"), (3, "LOAN")]
            ),
        ),
    ]
