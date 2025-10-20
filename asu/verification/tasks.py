from django.db import transaction

from celery.utils.log import get_task_logger

from asu.auth.models import User
from asu.core.celery import app
from asu.verification.models import EmailVerification, RegistrationVerification

logger = get_task_logger(__name__)


@app.task
def send_registration_email(*, email: str) -> None:
    logger.info("Registration requested, email=%s", email)
    if User.objects.filter(email__iexact=email).exists():
        # Skip sending email if user with this email is already registered.
        logger.warning("Registration mail cancelled, email=%s", email)
        return

    with transaction.atomic():
        verification = RegistrationVerification.objects.create(email=email)
        transaction.on_commit(verification.send_email)


@app.task
def send_email_change_email(*, user_id: int, email: str) -> None:
    if User.objects.filter(email__iexact=email).exists():
        logger.warning("Email change request cancelled, email=%s", email)
        return
    user = User.objects.only("id", "email").get(pk=user_id)
    logger.info(
        "Email change requested, user_id=%s current_email=%s requested_email=%s",
        user_id,
        user.email,
        email,
    )
    with transaction.atomic():
        verification = EmailVerification.objects.create(email=email, user=user)
        transaction.on_commit(verification.send_email)
