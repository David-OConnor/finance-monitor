# Generated by Django 5.0.2 on 2024-02-29 22:23

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0003_alter_subaccount_name_official"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="person",
            name="user",
            field=models.OneToOneField(
                default=0,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="person",
                to=settings.AUTH_USER_MODEL,
            ),
            preserve_default=False,
        ),
    ]
