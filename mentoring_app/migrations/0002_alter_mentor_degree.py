# Generated by Django 4.2.6 on 2023-12-14 07:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mentoring_app", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="mentor",
            name="Degree",
            field=models.CharField(
                choices=[
                    ("BAC", "Bac"),
                    ("BTS", "BTS"),
                    ("DUT", "DUT"),
                    ("LIC", "Bachelor/Licence"),
                    ("MAS", "Master"),
                    ("DOC", "PHD/Doctorat"),
                ],
                max_length=100,
            ),
        ),
    ]
