# Generated by Django 4.2.6 on 2023-12-29 20:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workgroup", "0008_workgroup_with_assistant"),
    ]

    operations = [
        migrations.AlterField(
            model_name="workgroupmember",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("accepted", "Accepted"),
                    ("denied", "Denied"),
                ],
                max_length=20,
            ),
        ),
    ]
