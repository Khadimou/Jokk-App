from django.conf import settings
from django.contrib.auth.models import User
from django.db import models

# Create your models here.
from django.contrib.auth.models import User
from django.db import models

from smart_mentor.models import OpenAIAssistant


class WorkGroup(models.Model):
    name = models.CharField(max_length=50)
    with_assistant = models.BooleanField(default=False)
    description = models.TextField(max_length=200, blank=True)
    avatar = models.ImageField(upload_to='avatars_workgroup/', blank=True)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, through='WorkGroupMember', related_name='invited_to_workgroups')
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_workgroups', null=True)
    assistants = models.ManyToManyField(OpenAIAssistant, blank=True, related_name='workgroups')

class WorkGroupMember(models.Model):
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('denied', 'Denied')])
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    workgroup = models.ForeignKey(WorkGroup, on_delete=models.CASCADE)
    # Vous pouvez ajouter d'autres champs si nécessaire
    class Meta:
        unique_together = ('workgroup', 'user')

class ChatRoom(models.Model):
    workgroup = models.ForeignKey(WorkGroup, on_delete=models.CASCADE, related_name='chatrooms')
    created_at = models.DateTimeField(auto_now_add=True)

class Message(models.Model):
    chat_room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class MessageAudio(models.Model):
    workgroup = models.ForeignKey(WorkGroup, related_name='audio_messages', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    audio_file = models.FileField(upload_to='audio_messages/')
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Audio message from {self.user.username} in {self.workgroup.name}"

class UserOnlineStatus(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='online_status')
    is_online = models.BooleanField(default=False)

    def set_online(self):
        self.is_online = True
        self.save()

    def set_offline(self):
        self.is_online = False
        self.save()


