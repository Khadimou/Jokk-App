from django.db.models.signals import post_save
from django.dispatch import receiver

from mentoring_app.models import Mentor
from smart_mentor.models import Profile


@receiver(post_save, sender=Profile)
def create_mentor_profile(sender, instance, **kwargs):
    if instance.is_mentor and not Mentor.objects.filter(profile=instance).exists():
        Mentor.objects.create(profile=instance)

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Profile, Notification

@receiver(post_save, sender=Profile)
def create_mentor_notification(sender, instance, created, **kwargs):
    if instance.is_mentor:
        # Tentez de récupérer l'instance de Mentor associée
        try:
            mentor = Mentor.objects.get(profile=instance)
            field_info = mentor.Fields
        except Mentor.DoesNotExist:
            field_info = "a field"

        # Créer la notification
        Notification.objects.create(
            recipient=instance.user,
            title="Promotion to Mentor",
            body=f"Congratulations {instance.user.username}, you have been designated as a mentor in {field_info}.",
            type="mentor_promotion"
        )
