from datetime import timedelta

from django.conf import settings
from django.utils import timezone

import pytest
from pytest_mock import MockerFixture

from asu.verification.models import RegistrationVerification
from tests.factories import RegistrationVerificationFactory


@pytest.mark.django_db
def test_verification_registration_eligible() -> None:
    verification = RegistrationVerificationFactory.create(
        email="helen@example.com",
        verified_at=timezone.now(),
    )
    actual = RegistrationVerification.objects.eligible().get()
    assert actual == verification


@pytest.mark.django_db
def test_verification_registration_eligible_case_expired(
    mocker: MockerFixture,
) -> None:
    # Create a verified registration
    RegistrationVerificationFactory.create(
        email="helen@example.com",
        verified_at=timezone.now(),
    )

    # Use eligible() after allocated time has been passed
    mocker.patch(
        "django.utils.timezone.now",
        return_value=timezone.now()
        + timedelta(seconds=settings.REGISTRATION_COMPLETE_TIMEOUT + 10),
    )
    assert RegistrationVerification.objects.eligible().exists() is False
