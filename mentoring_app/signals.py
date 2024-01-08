from django.db.models.signals import post_save
from django.dispatch import receiver

from mentoring_app.models import Mentor
from smart_mentor.models import Profile


@receiver(post_save, sender=Profile)
def create_mentor_profile(sender, instance, **kwargs):
    if instance.is_mentor and not Mentor.objects.filter(profile=instance).exists():
        Mentor.objects.create(profile=instance)