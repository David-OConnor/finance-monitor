# Generated by Django 5.0.2 on 2024-03-10 15:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "main",
            "0032_rename_merchange_name_recurringtransaction_merchant_name_and_more",
        ),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="recurringtransaction",
            options={"ordering": ["-last_date"]},
        ),
        migrations.AddField(
            model_name="recurringtransaction",
            name="notes",
            field=models.TextField(default=""),
            preserve_default=False,
        ),
    ]
