import datetime

from django.utils import timezone

from oauth2_provider.models import clear_expired

from asu.auth.models import User, UserDeactivation
from asu.core.celery import app


@app.task
def clear_expired_oauth_tokens() -> None:
    """
    This is a periodic task run to clean now-unnecessary
    oauth token entries from the database.
    """
    clear_expired()


@app.task
def delete_users_permanently() -> tuple[int, dict[str, int]]:
    """
    Permanently delete users who deactivated their accounts long ago.
    """
    deactivations = UserDeactivation.objects.filter(
        for_deletion=True,
        date_revoked__isnull=True,
        date_created__lte=timezone.now() - datetime.timedelta(days=30),
    ).values("user_id")
    return User.objects.filter(id__in=deactivations).delete()
