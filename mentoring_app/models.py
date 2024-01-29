from django.conf import settings
from django.db import models

from smart_mentor.models import Profile


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
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)

    def __str__(self):
        return self.Fields

class Availability(models.Model):
    mentor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    day_of_week = models.CharField(max_length=10)
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.user.username} available on {self.day_of_week} from {self.start_time} to {self.end_time}"

class CoachingRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    )

    mentor = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='coaching_requests_mentor', on_delete=models.CASCADE)
    mentee = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='coaching_requests_mentee', on_delete=models.CASCADE)
    selected_dates = models.JSONField()  # Utilisez JSONField pour stocker une liste de dates
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    
     # DateField pour stocker la date de la session de coaching.
    date = models.DateField(auto_now_add=True)
    available_dates = models.ManyToManyField('Availability')

    # TimeField pour stocker l'heure de la session de coaching.
    time = models.TimeField(auto_now=True)

    def __str__(self):
        return f"Coaching request from {self.mentee} to {self.mentor} - Status: {self.status}"


class Response(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    question = models.TextField()
    answer = models.TextField()

    def __str__(self):
        return f"{self.user.username} - {self.question}"

class Notification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, related_name='sent_notifications')
    workgroup = models.ForeignKey('workgroup.WorkGroup', on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=255)
    body = models.TextField()
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    coaching_request_id = models.IntegerField(null=True, blank=True)
    TYPE_CHOICES = (
        ('invitation', 'Invitation'),
        ('join_request', 'Join Request'),
        ('coaching_request', 'Coaching Request'),
        # Autres types si nécessaire
        ('room_launched','Room launched'),
        ('mentor_promotion', 'Mentor Promotion'),
	('renewal_reminder', 'Renewal Reminder'),
        ('premium_status_change','Premium Status'),
        ('follow','Follow'),
    )
    type = models.CharField(max_length=50, choices=TYPE_CHOICES, default='invitation')

    def __str__(self):
        return f'Notification to {self.recipient.username} - {self.type}'

