from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserOnlineStatus

@receiver(post_save, sender=User)
def create_user_online_status(sender, instance, created, **kwargs):
    if created:
        UserOnlineStatus.objects.create(user=instance)

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def send_notification(notification):
    channel_layer = get_channel_layer()
    group_name = f'notifications_{notification.recipient.id}'

    # Préparer la notification à envoyer
    notification_data = {
        'id': notification.id,
        'title': notification.title,
        'body': notification.body,
        'type': notification.type,
        'read': notification.read,
        'created_at': notification.created_at.strftime('%Y-%m-%d %H:%M:%S')
    }

    # Envoyer la notification au groupe de WebSocket
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'receive_notification',
            'notification': notification_data
        }
    )

