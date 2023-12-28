from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField

class Profile(models.Model):
    GENDER_CHOICES = (
        ('MALE', _('Male')),
        ('FEMALE', _('Female')),
        ('OTHER', _('Other')),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to='avatars/', blank=True)
    birthdate = models.DateField(null=True)
    gender = models.CharField(max_length=6, choices=GENDER_CHOICES)
    country = CountryField(blank_label='(select country)', blank=True)
    education_level = models.CharField(max_length=100, blank=True)
    skills = models.TextField(max_length=100, blank=True)
    phone = models.CharField(max_length=20)
    bio = models.TextField(max_length=100, blank=True)
    social_media_links = models.URLField(max_length=200, blank=True)

    def __str__(self):
        return self.user.username

class OpenAIAssistant(models.Model):
    assistant_id = models.CharField(max_length=100, unique=True)
    file_id = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    description = models.TextField()
    model = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class Message(models.Model):
    sender = models.ForeignKey(User, related_name='sent_messages', on_delete=models.CASCADE)
    recipient = models.ForeignKey(User, related_name='received_messages', on_delete=models.CASCADE)
    text = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    def __str__(self):
        return f"Message from {self.sender} to {self.recipient}"




