from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic.base import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path('login/', include("smart_mentor.urls")),  # Assurez-vous que 'smart_mentor.urls' contient la route 'login/'
]

urlpatterns += i18n_patterns(
    path('', include("smart_mentor.urls")),
    path('', include("workgroup.urls")),
    path('', include("mentoring_app.urls")),
    path('',include("user_payment.urls")),
    path('', RedirectView.as_view(pattern_name='login', permanent=True)),  # Redirige le chemin racine vers 'login'
    #prefix_default_language=False,  # Ajoutez cette option si vous ne voulez pas de préfixe pour la langue par défaut
)

urlpatterns += [
    path('i18n/', include('django.conf.urls.i18n')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
