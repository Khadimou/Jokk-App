from django.contrib import admin

from mentoring_app.models import Notification
from smart_mentor.models import Profile, OpenAIAssistant, Message, Follow, CustomUser

# Register your models here.
admin.site.register(CustomUser)
admin.site.register(OpenAIAssistant)
admin.site.register(Message)
admin.site.register(Follow)
from django.contrib import messages

def set_as_mentor(modeladmin, request, queryset):
    for profile in queryset:
        profile.is_mentor = True
        profile.save()

        notification = Notification.objects.create(
            recipient=profile.user,
            title="Promotion to Mentor",
            body=f"Congratulations {profile.user.username}, you have been designated as a mentor in {profile.Fields}.",
            type="mentor_promotion"
        )
        messages.info(request, f"Notification created for {profile.user.username}: {notification}")

    modeladmin.message_user(request, "Selected users have been marked as mentors and notified.")


set_as_mentor.short_description = "Mark selected users as mentors and notify them"

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):

    list_display = ('user', 'is_mentor', 'country', 'education_level', 'phone')
    list_editable = ('is_mentor',)
    search_fields = ('user__username', 'country', 'education_level')
    list_filter = ('is_mentor', 'gender', 'country')

    actions = [set_as_mentor]

