# Generated by Django 5.0.2 on 2024-03-15 19:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0042_alter_categorycustom_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="financialaccount",
            name="last_refreshed_successfully",
            field=models.DateTimeField(default="1999-09-09"),
            preserve_default=False,
        ),
    ]