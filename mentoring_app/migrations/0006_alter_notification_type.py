# Generated by Django 4.2.9 on 2024-01-23 21:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mentoring_app', '0005_alter_notification_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='type',
            field=models.CharField(choices=[('invitation', 'Invitation'), ('join_request', 'Join Request'), ('coaching_request', 'Coaching Request'), ('room_launched', 'Room launched'), ('mentor_promotion', 'Mentor Promotion'), ('renewal_reminder', 'Renewal Reminder'), ('premium_status_change', 'Premium Status'), ('follow', 'Follow')], default='invitation', max_length=50),
        ),
    ]
