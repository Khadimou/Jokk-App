from django.contrib import admin

from workgroup.models import WorkGroup, WorkGroupMember, ChatRoom, Message

# Register your models here.
admin.site.register(WorkGroup)
admin.site.register(WorkGroupMember)
admin.site.register(ChatRoom)
admin.site.register(Message)