from django.apps import AppConfig


class MentoringAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "mentoring_app"
    def ready(self):
        import mentoring_app.signals