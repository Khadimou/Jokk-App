from django.contrib import admin

from mentoring_app.models import Mentor, Response, Notification, Availability, CoachingRequest

# Register your models here.
admin.site.register(Mentor)
admin.site.register(Response)
admin.site.register(Notification)
admin.site.register(Availability)
admin.site.register(CoachingRequest)
