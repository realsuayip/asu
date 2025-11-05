from datetime import timedelta

from django.conf import settings
from django.urls import reverse
from django.utils import timezone

import pytest
from pytest_mock import MockerFixture

from asu.verification.models import RegistrationVerification
from tests.conftest import OAuthClient


@pytest.mark.django_db
def test_verification_registration_check(
    first_party_app_client: OAuthClient,
    mocker: MockerFixture,
) -> None:
    verification = RegistrationVerification.objects.create(email="helen@example.com")
    response = first_party_app_client.post(
        reverse("api:verification:registration-verification-check"),
        data={
            "email": verification.email,
            "code": verification.code,
        },
    )
    assert response.status_code == 200
    assert response.json() == {
        "email": verification.email,
        "consent": mocker.ANY,
    }
    verification.refresh_from_db()
    assert verification.is_eligible is True
    assert verification.date_verified is not None
    assert verification.date_completed is None


@pytest.mark.django_db
def test_verification_registration_check_expires_code_after_use(
    first_party_app_client: OAuthClient,
) -> None:
    verification = RegistrationVerification.objects.create(email="helen@example.com")
    url, payload = (
        reverse("api:verification:registration-verification-check"),
        {"email": verification.email, "code": verification.code},
    )
    r1 = first_party_app_client.post(url, data=payload)
    r2 = first_party_app_client.post(url, data=payload)
    assert r1.status_code == 200
    assert r2.status_code == 404


@pytest.mark.django_db
def test_verification_registration_check_bad_code(
    first_party_app_client: OAuthClient,
) -> None:
    verification = RegistrationVerification.objects.create(email="helen@example.com")
    verification.code = "123456"
    verification.save(update_fields=["code"])
    response = first_party_app_client.post(
        reverse("api:verification:registration-verification-check"),
        data={
            "email": verification.email,
            "code": "987654",
        },
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_verification_registration_check_missing(
    first_party_app_client: OAuthClient,
) -> None:
    response = first_party_app_client.post(
        reverse("api:verification:registration-verification-check"),
        data={
            "email": "helen@example.com",
            "code": "987654",
        },
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_verification_registration_check_expired_code(
    first_party_app_client: OAuthClient,
    mocker: MockerFixture,
) -> None:
    past = timezone.now() - timedelta(seconds=settings.REGISTRATION_VERIFY_PERIOD + 10)
    mocker.patch("django.utils.timezone.now", return_value=past)
    verification = RegistrationVerification.objects.create(email="helen@example.com")
    mocker.stopall()

    response = first_party_app_client.post(
        reverse("api:verification:registration-verification-check"),
        data={
            "email": verification.email,
            "code": verification.code,
        },
    )
    assert response.status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize(
    "code, errorlist",
    (
        (
            "9876544",
            [
                {
                    "message": "Ensure this field has no more than 6 characters.",
                    "code": "max_length",
                }
            ],
        ),
        (
            "AB34511",
            [
                {
                    "message": "Ensure this field contains only digits.",
                    "code": "invalid",
                },
                {
                    "message": "Ensure this field has no more than 6 characters.",
                    "code": "max_length",
                },
            ],
        ),
        (
            "112",
            [
                {
                    "message": "Ensure this field has at least 6 digits.",
                    "code": "invalid",
                }
            ],
        ),
    ),
)
def test_verification_registration_check_invalid_code(
    first_party_app_client: OAuthClient,
    code: str,
    errorlist: list[dict[str, str]],
) -> None:
    response = first_party_app_client.post(
        reverse("api:verification:registration-verification-check"),
        data={
            "email": "helen@example.com",
            "code": code,
        },
    )
    assert response.status_code == 400
    assert response.json()["errors"]["code"] == errorlist


def test_verification_registration_check_requires_authentication(
    client: OAuthClient,
) -> None:
    response = client.post(
        reverse("api:verification:registration-verification-check"),
        data={
            "email": "helen@example.com",
            "code": "123456",
        },
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_verification_registration_check_requires_first_party_app(
    app_client: OAuthClient,
) -> None:
    response = app_client.post(
        reverse("api:verification:registration-verification-check"),
        data={
            "email": "helen@example.com",
            "code": "123456",
        },
    )
    assert response.status_code == 403
