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
def test_verification_registration_eligible() -> None:
    verification = RegistrationVerification.objects.create(
        email="helen@example.com", verified_at=timezone.now()
    )
    actual = RegistrationVerification.objects.eligible().get()
    assert actual == verification


@pytest.mark.django_db
def test_verification_registration_eligible_case_expired(
    mocker: MockerFixture,
) -> None:
    # Create a verified registration
    RegistrationVerification.objects.create(
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
