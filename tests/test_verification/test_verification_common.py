from django.urls import reverse

import pytest

from tests.conftest import OAuthClient
from tests.factories import UserFactory


@pytest.mark.django_db
@pytest.mark.parametrize(
    "endpoint",
    (
        "api:verification:registration-verify",
        "api:verification:password-reset-verify",
        "api:verification:email-change-complete",
    ),
)
def test_verification_verify_missing(
    first_party_app_client: OAuthClient,
    endpoint: str,
) -> None:
    if endpoint == "api:verification:email-change-complete":
        user = UserFactory.create(email="helen_old@example.com")
        first_party_app_client.set_user(user, scope="")
    response = first_party_app_client.post(
        reverse(endpoint),
        data={
            "id": "019b04e3-90e4-7751-a386-7a4550a69409",
            "code": "987654",
        },
    )
    assert response.status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize("code", ("9876544", "AB34511", "112"))
@pytest.mark.parametrize(
    "endpoint",
    (
        "api:verification:registration-verify",
        "api:verification:password-reset-verify",
        "api:verification:email-change-complete",
    ),
)
def test_verification_verify_invalid_code(
    first_party_app_client: OAuthClient,
    endpoint: str,
    code: str,
) -> None:
    if endpoint == "api:verification:email-change-complete":
        user = UserFactory.create(email="helen_old@example.com")
        first_party_app_client.set_user(user, scope="")
    response = first_party_app_client.post(
        reverse(endpoint),
        data={
            "id": "019b04e3-90e4-7751-a386-7a4550a69409",
            "code": code,
        },
    )
    assert response.status_code == 400
    assert response.json()["errors"]["code"] == [
        {
            "code": "invalid",
            "message": "Please enter a valid code.",
        }
    ]


@pytest.mark.parametrize(
    "endpoint",
    (
        "api:verification:registration-verify",
        "api:verification:password-reset-verify",
        "api:verification:email-change-complete",
    ),
)
def test_verification_verify_requires_authentication(
    client: OAuthClient,
    endpoint: str,
) -> None:
    response = client.post(
        reverse(endpoint),
        data={
            "id": "019b04e3-90e4-7751-a386-7a4550a69409",
            "code": "123456",
        },
    )
    assert response.status_code == 401


@pytest.mark.django_db
@pytest.mark.parametrize(
    "endpoint",
    (
        "api:verification:registration-verify",
        "api:verification:password-reset-verify",
        "api:verification:email-change-complete",
    ),
)
def test_verification_verify_requires_first_party_app(
    app_client: OAuthClient,
    endpoint: str,
) -> None:
    response = app_client.post(
        reverse(endpoint),
        data={
            "id": "019b04e3-90e4-7751-a386-7a4550a69409",
            "code": "123456",
        },
    )
    assert response.status_code == 403
