import re
from datetime import timedelta

from django.conf import settings
from django.core import mail
from django.urls import reverse
from django.utils import timezone

import pytest
from oauth2_provider.settings import oauth2_settings
from pytest_django import DjangoCaptureOnCommitCallbacks
from pytest_mock import MockerFixture

from asu.auth.models import User
from asu.verification.models import RegistrationVerification
from tests.conftest import OAuthClient, create_default_application
from tests.factories import UserFactory


@pytest.mark.django_db
def test_user_registration_create(
    first_party_app_client: OAuthClient,
    mocker: MockerFixture,
) -> None:
    create_default_application()
    verification = RegistrationVerification.objects.create(
        email="helen@example.com", date_verified=timezone.now()
    )
    consent = verification.create_consent()

    payload = {
        "email": "helen@example.com",
        "consent": consent,
        "display_name": "Helen",
        "password": "Hln_1900",
        "username": "helen",
    }
    response = first_party_app_client.post(
        reverse("api:auth:user-list"),
        data=payload,
    )
    assert response.status_code == 201
    assert response.json() == {
        "auth": {
            "access_token": mocker.ANY,
            "expires_in": 3600,
            "refresh_token": mocker.ANY,
            "scope": " ".join(oauth2_settings.SCOPES),
            "token_type": "Bearer",
        },
        "birth_date": None,
        "display_name": "Helen",
        "email": "helen@example.com",
        "gender": "unspecified",
        "id": mocker.ANY,
        "language": "en",
        "url": mocker.ANY,
        "username": "helen",
    }
    user = User.objects.get(email="helen@example.com")
    assert user.username == "helen"
    assert user.display_name == "Helen"
    assert user.birth_date is None
    assert user.gender == "unspecified"
    assert user.language == "en"
    assert user.description == ""
    assert user.website == ""
    assert not user.profile_picture
    assert user.allows_receipts is True
    assert user.allows_all_messages is True
    assert user.is_frozen is False
    assert user.is_private is False
    assert user.is_active is True

    verification.refresh_from_db()
    assert verification.date_completed is not None
    assert verification.user == user


@pytest.mark.django_db
def test_user_registration_create_case_invalid_consent(
    first_party_app_client: OAuthClient,
) -> None:
    payload = {
        "email": "helen@example.com",
        "consent": "bad:consent",
        "display_name": "Helen",
        "password": "Hln_1900",
        "username": "helen",
    }

    response = first_party_app_client.post(
        reverse("api:auth:user-list"),
        data=payload,
    )
    assert response.status_code == 400
    assert response.json()["errors"] == {
        "email": [
            {
                "code": "invalid",
                "message": "This e-mail could not be verified."
                " Please provide a validated e-mail address.",
            }
        ]
    }


@pytest.mark.django_db
def test_user_registration_create_case_expired_consent(
    first_party_app_client: OAuthClient,
    mocker: MockerFixture,
) -> None:
    verification = RegistrationVerification.objects.create(
        email="helen@example.com",
        date_verified=timezone.now(),
    )
    consent = verification.create_consent()
    mocker.patch(
        "django.utils.timezone.now",
        return_value=timezone.now()
        + timedelta(seconds=settings.REGISTRATION_REGISTER_PERIOD + 1),
    )
    payload = {
        "email": "helen@example.com",
        "consent": consent,
        "display_name": "Helen",
        "password": "Hln_1900",
        "username": "helen",
    }
    response = first_party_app_client.post(
        reverse("api:auth:user-list"),
        data=payload,
    )
    assert response.status_code == 400
    assert response.json()["errors"] == {
        "email": [
            {
                "code": "invalid",
                "message": "This e-mail could not be verified."
                " Please provide a validated e-mail address.",
            }
        ]
    }


@pytest.mark.django_db
def test_user_registration_create_password_validation(
    first_party_app_client: OAuthClient,
) -> None:
    verification = RegistrationVerification.objects.create(
        email="helen@example.com",
        date_verified=timezone.now(),
    )
    consent = verification.create_consent()
    payload = {
        "email": "helen@example.com",
        "consent": consent,
        "display_name": "Helen",
        "password": "helenexample",
        "username": "helen",
    }
    response = first_party_app_client.post(
        reverse("api:auth:user-list"),
        data=payload,
    )
    assert response.status_code == 400
    assert response.json()["errors"] == {
        "password": [
            {
                "message": "The password is too similar to the e-mail.",
                "code": "invalid",
            }
        ]
    }


@pytest.mark.django_db
@pytest.mark.parametrize(
    "username, error_message",
    (
        ("helen", "The username you specified is already in use."),
        (
            "_helen",
            "Usernames can only contain latin letters, numerals and"
            " underscores. Trailing, leading or consecutive underscores"
            " are not allowed.",
        ),
    ),
)
def test_user_registration_create_username_validation(
    first_party_app_client: OAuthClient,
    username: str,
    error_message: str,
) -> None:
    UserFactory.create(username="Helen")
    verification = RegistrationVerification.objects.create(
        email="helen@example.com",
        date_verified=timezone.now(),
    )
    consent = verification.create_consent()
    payload = {
        "email": "helen@example.com",
        "consent": consent,
        "display_name": "Helen",
        "password": "helenexample",
        "username": username,
    }
    response = first_party_app_client.post(
        reverse("api:auth:user-list"),
        data=payload,
    )
    assert response.status_code == 400
    assert response.json()["errors"] == {
        "username": [
            {
                "message": error_message,
                "code": "invalid",
            }
        ]
    }


@pytest.mark.django_db
@pytest.mark.parametrize(
    "verification_email, creation_email",
    (
        ("Helen@example.com", "Helen@Example.com"),
        ("Helen@example.com", "helen@example.com"),
    ),
)
def test_user_registration_create_email_normalization(
    first_party_app_client: OAuthClient,
    verification_email: str,
    creation_email: str,
) -> None:
    create_default_application()
    verification = RegistrationVerification.objects.create(
        email=verification_email,
        date_verified=timezone.now(),
    )
    consent = verification.create_consent()
    payload = {
        "email": creation_email,
        "consent": consent,
        "display_name": "Helen",
        "password": "hln_14194xx",
        "username": "helen",
    }
    response = first_party_app_client.post(
        reverse("api:auth:user-list"),
        data=payload,
    )
    assert response.status_code == 201
    user = User.objects.only("email").get(username="helen")
    assert user.email == verification_email


def test_user_registration_create_requires_authentication(client: OAuthClient) -> None:
    response = client.post(
        reverse("api:auth:user-list"),
        data={
            "email": "helen@example.com",
            "consent": "bad:consent",
            "display_name": "Helen",
            "password": "Hln_1900",
            "username": "helen",
        },
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_user_registration_create_requires_requires_first_party_app(
    app_client: OAuthClient,
) -> None:
    response = app_client.post(
        reverse("api:auth:user-list"),
        data={
            "email": "helen@example.com",
            "consent": "bad:consent",
            "display_name": "Helen",
            "password": "Hln_1900",
            "username": "helen",
        },
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_user_registration_nullifies_other_verifications(
    first_party_app_client: OAuthClient,
) -> None:
    create_default_application()
    v1, v2 = RegistrationVerification.objects.bulk_create(
        [
            RegistrationVerification(
                email="helen@example.com",
                date_verified=timezone.now(),
                code="111111",
            ),
            RegistrationVerification(
                email="helen@example.com",
                date_verified=timezone.now(),
                code="111112",
            ),
        ]
    )
    consent = v1.create_consent()
    response = first_party_app_client.post(
        reverse("api:auth:user-list"),
        data={
            "email": "helen@example.com",
            "consent": consent,
            "display_name": "Helen",
            "password": "Hln_1900",
            "username": "helen",
        },
    )
    assert response.status_code == 201

    v1.refresh_from_db()
    v2.refresh_from_db()

    assert v1.date_completed is not None
    assert v2.nulled_by == v1


@pytest.mark.django_db
def test_user_registration_flow(
    client: OAuthClient,
    first_party_app_client: OAuthClient,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    create_default_application()

    # Step 1: Send verification email containing code
    with django_capture_on_commit_callbacks(execute=True):
        response = first_party_app_client.post(
            reverse("api:verification:registration-verification-list"),
            data={"email": "helen@example.com"},
        )
    assert response.status_code == 201
    code = re.search(
        r"<div class='code'><strong>(\d+)</strong></div>",
        mail.outbox[0].body,
    ).group(1)

    # Step 2: Use grabbed code to get a consent
    response = first_party_app_client.post(
        reverse("api:verification:registration-verification-check"),
        data={
            "email": "helen@example.com",
            "code": code,
        },
    )
    assert response.status_code == 200
    consent = response.json()["consent"]

    # Step 3: Create user with given consent
    response = first_party_app_client.post(
        reverse("api:auth:user-list"),
        data={
            "email": "helen@example.com",
            "consent": consent,
            "display_name": "Helen",
            "password": "Hln_1900",
            "username": "helen",
        },
    )
    assert response.status_code == 201

    # Can we use returned token to fetch our user?
    token = response.json()["auth"]["access_token"]
    client.set_token(token)
    response = client.get(reverse("api:auth:user-me"))
    assert response.status_code == 200
