from django.contrib import admin

from workgroup.models import WorkGroup, WorkGroupMember, ChatRoom, Message, MessageAudio

# Register your models here.
admin.site.register(WorkGroup)
admin.site.register(WorkGroupMember)
admin.site.register(ChatRoom)
admin.site.register(Message)
admin.site.register(MessageAudio)