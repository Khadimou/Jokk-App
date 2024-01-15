from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django_countries.fields import CountryField

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)

class Profile(models.Model):
    GENDER_CHOICES = (
        ('MALE', _('Male')),
        ('FEMALE', _('Female')),
        ('OTHER', _('Other')),
    )

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    first_login = models.BooleanField(default=True)
    is_mentor = models.BooleanField(default=False)
    avatar = models.ImageField(upload_to='avatars/', blank=True, default='avatars/pp.svg')
    birthdate = models.DateField(null=True)
    gender = models.CharField(max_length=6, choices=GENDER_CHOICES)
    #city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True)
    #region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True)
    country = CountryField(blank_label='(Select a country)', blank=True)
    education_level = models.CharField(max_length=100, blank=True)
    skills = models.TextField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    bio = models.TextField(max_length=100, blank=True)
    social_media_links = models.URLField(max_length=200, blank=True)

    def __str__(self):
        return self.user.username

from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


class OpenAIAssistant(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    assistant_id = models.CharField(max_length=100, unique=True)
    file_id = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    description = models.TextField()
    model = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class Message(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sent_messages', on_delete=models.CASCADE)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='received_messages', on_delete=models.CASCADE)
    text = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    def __str__(self):
        return f"Message from {self.sender} to {self.recipient}"

class Follow(models.Model):
    follower = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='following', on_delete=models.CASCADE)
    followed = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='followers', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'followed')

    def __str__(self):
        return f"{self.follower.username} follows {self.followed.username}"


