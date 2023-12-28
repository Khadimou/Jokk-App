from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserOnlineStatus

@receiver(post_save, sender=User)
def create_user_online_status(sender, instance, created, **kwargs):
    if created:
        UserOnlineStatus.objects.create(user=instance)
