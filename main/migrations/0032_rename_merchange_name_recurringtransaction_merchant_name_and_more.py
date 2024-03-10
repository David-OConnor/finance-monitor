# Generated by Django 5.0.2 on 2024-03-10 14:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0031_rename_categorycusom_categorycustom_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="recurringtransaction",
            old_name="merchange_name",
            new_name="merchant_name",
        ),
        migrations.AddField(
            model_name="financialaccount",
            name="last_refreshed_recurring",
            field=models.DateTimeField(default="1999-09-09"),
            preserve_default=False,
        ),
    ]