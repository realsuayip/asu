from django.urls import reverse

import pytest

from tests.conftest import OAuthClient
from tests.factories import UserFactory


@pytest.mark.django_db
@pytest.mark.parametrize(
    "endpoint",
    (
        "api:verification:registration-verification-check",
        "api:verification:password-reset-check",
        "api:verification:email-verification-check",
    ),
)
def test_verification_check_missing(
    first_party_app_client: OAuthClient,
    endpoint: str,
) -> None:
    if endpoint == "api:verification:email-verification-check":
        user = UserFactory.create(email="helen_old@example.com")
        first_party_app_client.set_user(user, scope="")
    response = first_party_app_client.post(
        reverse(endpoint),
        data={
            "email": "helen@example.com",
            "code": "987654",
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
@pytest.mark.parametrize(
    "endpoint",
    (
        "api:verification:registration-verification-check",
        "api:verification:password-reset-check",
        "api:verification:email-verification-check",
    ),
)
def test_verification_check_invalid_code(
    first_party_app_client: OAuthClient,
    endpoint: str,
    code: str,
    errorlist: list[dict[str, str]],
) -> None:
    if endpoint == "api:verification:email-verification-check":
        user = UserFactory.create(email="helen_old@example.com")
        first_party_app_client.set_user(user, scope="")
    response = first_party_app_client.post(
        reverse(endpoint),
        data={
            "email": "helen@example.com",
            "code": code,
        },
    )
    assert response.status_code == 400
    assert response.json()["errors"]["code"] == errorlist


@pytest.mark.parametrize(
    "endpoint",
    (
        "api:verification:registration-verification-check",
        "api:verification:password-reset-check",
        "api:verification:email-verification-check",
    ),
)
def test_verification_check_requires_authentication(
    client: OAuthClient,
    endpoint: str,
) -> None:
    response = client.post(
        reverse(endpoint),
        data={
            "email": "helen@example.com",
            "code": "123456",
        },
    )
    assert response.status_code == 401


@pytest.mark.django_db
@pytest.mark.parametrize(
    "endpoint",
    (
        "api:verification:registration-verification-check",
        "api:verification:password-reset-check",
        "api:verification:email-verification-check",
    ),
)
def test_verification_check_requires_first_party_app(
    app_client: OAuthClient,
    endpoint: str,
) -> None:
    response = app_client.post(
        reverse(endpoint),
        data={
            "email": "helen@example.com",
            "code": "123456",
        },
    )
    assert response.status_code == 403
