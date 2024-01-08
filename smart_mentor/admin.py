from django.contrib import admin

from smart_mentor.models import Profile, OpenAIAssistant, Message

# Register your models here.
#admin.site.register(Profile)
admin.site.register(OpenAIAssistant)
admin.site.register(Message)
def set_as_mentor(modeladmin, request, queryset):
    queryset.update(is_mentor=True)
set_as_mentor.short_description = "Mark selected users as mentors"
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_mentor', 'country', 'education_level', 'phone')
    list_editable = ('is_mentor',)
    search_fields = ('user__username', 'country', 'education_level')
    list_filter = ('is_mentor', 'gender', 'country')

    actions = [set_as_mentor]

