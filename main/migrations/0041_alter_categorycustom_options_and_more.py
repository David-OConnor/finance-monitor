# Generated by Django 5.0.2 on 2024-03-14 14:58

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0040_alter_categoryrule_options_and_more"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="categorycustom",
            options={"ordering": ["person"]},
        ),
        migrations.AlterField(
            model_name="categorycustom",
            name="person",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="custom_categories",
                to="main.person",
            ),
        ),
    ]