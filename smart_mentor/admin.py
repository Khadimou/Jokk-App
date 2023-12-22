from django.contrib import admin

from smart_mentor.models import Profile, OpenAIAssistant

# Register your models here.
admin.site.register(Profile)
admin.site.register(OpenAIAssistant)