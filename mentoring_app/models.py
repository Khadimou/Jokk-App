from django.conf import settings
from django.db import models

# Create your models here.
class Matching(models.Model):
    Fields = models.CharField(max_length=100)
    Degree = models.CharField(max_length=100)
    Skills = models.CharField(max_length=100)
    Objectives = models.CharField(max_length=100)
    Job = models.CharField(max_length=100)
    PersonalityDescription = models.CharField(max_length=100)

    def __str__(self):
        return self.Fields

from django.contrib.auth.models import User

class Mentor(models.Model):
    DEGREE_CHOICES = (
        ('BAC', 'Baccalauréat'),
        ('BTS', 'BTS'),
        ('DUT', 'DUT'),
        ('LIC', 'Bachelor/Licence'),
        ('MAS', 'Master'),
        ('DOC', 'PHD/Doctorat'),
    )

    Fields = models.CharField(max_length=100)
    Degree = models.CharField(max_length=100, choices=DEGREE_CHOICES)
    Skills = models.CharField(max_length=100)
    Objectives = models.CharField(max_length=100)
    Job = models.CharField(max_length=100)
    PersonalityDescription = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.Fields

class Response(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.TextField()
    answer = models.TextField()

    def __str__(self):
        return f"{self.user.username} - {self.question}"

class Notification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    workgroup = models.ForeignKey('workgroup.WorkGroup', on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=255)
    body = models.TextField()
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Notification for {self.recipient.username}'

