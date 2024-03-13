# Generated by Django 5.0.2 on 2024-03-13 02:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0039_categoryrule"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="categoryrule",
            options={"ordering": ["person"]},
        ),
        migrations.AlterUniqueTogether(
            name="categoryrule",
            unique_together={("person", "description")},
        ),
    ]