# Generated by Django 4.2.6 on 2023-12-22 16:49

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("workgroup", "0004_chatroom_message"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserOnlineStatus",
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
                ("is_online", models.BooleanField(default=False)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="online_status",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]