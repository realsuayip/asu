from celery import Celery

__all__ = ["app"]

app = Celery("zeynep")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
