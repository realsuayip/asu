from django.utils import timezone

from celery import Celery

__all__ = ["app"]

app = Celery("asu")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "auth-tokens": {
        "task": "asu.auth.tasks.clear_expired_oauth_tokens",
        "schedule": timezone.timedelta(hours=24),
    }
}
