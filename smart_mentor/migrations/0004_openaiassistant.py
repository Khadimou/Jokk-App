# Generated by Django 4.2.7 on 2023-12-12 22:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("smart_mentor", "0003_profile_birthdate_alter_profile_avatar"),
    ]

    operations = [
        migrations.CreateModel(
            name="OpenAIAssistant",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("assistant_id", models.CharField(max_length=100, unique=True)),
                ("file_id", models.CharField(max_length=100)),
                ("name", models.CharField(max_length=100)),
                ("description", models.TextField()),
                ("model", models.CharField(max_length=50)),
            ],
        ),
    ]
