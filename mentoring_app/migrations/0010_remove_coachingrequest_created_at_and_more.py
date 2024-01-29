# Generated by Django 4.2.9 on 2024-01-24 23:12

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('mentoring_app', '0009_rename_user_availability_mentor'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='coachingrequest',
            name='created_at',
        ),
        migrations.RemoveField(
            model_name='coachingrequest',
            name='updated_at',
        ),
        migrations.AddField(
            model_name='coachingrequest',
            name='available_dates',
            field=models.ManyToManyField(to='mentoring_app.availability'),
        ),
        migrations.AddField(
            model_name='coachingrequest',
            name='date',
            field=models.DateField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='coachingrequest',
            name='time',
            field=models.TimeField(auto_now=True),
        ),
    ]