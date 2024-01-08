from django.contrib import admin

from mentoring_app.models import Mentor, Response, Notification

# Register your models here.
admin.site.register(Mentor)
admin.site.register(Response)
admin.site.register(Notification)