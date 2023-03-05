from oauth2_provider.models import clear_expired

from asu.celery import app


@app.task
def clear_expired_oauth_tokens():
    """
    This is a periodic task run to clean now-unnecessary
    oauth token entries from the database.
    """
    clear_expired()
