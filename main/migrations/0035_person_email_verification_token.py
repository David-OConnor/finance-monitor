# Generated by Django 5.0.2 on 2024-03-11 21:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0034_person_previous_emails"),
    ]

    operations = [
        migrations.AddField(
            model_name="person",
            name="email_verification_token",
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
    ]
