# Generated by Django 5.0.2 on 2024-03-03 14:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0018_networthsnapshot"),
    ]

    operations = [
        migrations.AddField(
            model_name="person",
            name="email_verified",
            field=models.BooleanField(default=False),
        ),
    ]
