from datetime import timedelta

from django.conf import settings
from django.utils import timezone

import pytest
from pytest_mock import MockerFixture

from asu.verification.models import RegistrationVerification


@pytest.mark.django_db
def test_verification_registration_code_generation() -> None:
    verification = RegistrationVerification.objects.create(email="helen@example.com")

    assert len(verification.code) == 6
    assert verification.code.isdigit()


@pytest.mark.django_db
def test_verification_registration_get_with_consent() -> None:
    verification = RegistrationVerification.objects.create(
        email="helen@example.com", verified_at=timezone.now()
    )
    consent = verification.create_consent()
    actual = RegistrationVerification.objects.get_with_consent(
        "helen@example.com", consent
    )
    assert actual == verification


@pytest.mark.django_db
def test_verification_registration_get_with_consent_case_expired(
    mocker: MockerFixture,
) -> None:
    # Create a verified registration
    verification = RegistrationVerification.objects.create(
        email="helen@example.com",
        verified_at=timezone.now(),
    )
    consent = verification.create_consent()

    # Use get_with_consent after allocated time has been passed
    mocker.patch(
        "django.utils.timezone.now",
        return_value=timezone.now()
        + timedelta(seconds=settings.REGISTRATION_REGISTER_PERIOD + 10),
    )
    obj = RegistrationVerification.objects.get_with_consent(
        "helen@example.com", consent
    )
    assert obj is None
