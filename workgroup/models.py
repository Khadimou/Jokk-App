from django.conf import settings
from django.contrib.auth.models import User
from django.db import models

# Create your models here.
from django.contrib.auth.models import User
from django.db import models

class WorkGroup(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(max_length=200, blank=True)
    avatar = models.ImageField(upload_to='avatars_workgroup/', blank=True)
    members = models.ManyToManyField(User, through='WorkGroupMember', related_name='invited_to_workgroups')
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_workgroups', null=True)

class WorkGroupMember(models.Model):
    status = models.CharField(max_length=20, choices=[('invited', 'Invited'), ('accepted', 'Accepted'), ('refused', 'Refused')])
    user = models.ForeignKey(User, on_delete=models.CASCADE)
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


