import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SocialNetwork.settings')

# Exemple de configuration pour utiliser Redis comme courtier
app = Celery('SocialNetwork', broker='redis://localhost:6379/0')
app.conf.beat_scheduler = 'django_celery_beat.schedulers:DatabaseScheduler'
app.config_from_object('django.conf:settings', namespace='CELERY')

# Découverte automatique des tâches
app.autodiscover_tasks()

