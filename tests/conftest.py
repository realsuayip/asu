from rest_framework.test import APIClient

import pytest

from asu.auth.models import Application, User
from asu.core.models import ProjectVariable
from tests.factories import UserFactory


class OAuthClient(APIClient):
    def set_user(self, user: User) -> None:
        token = user.issue_token()["access_token"]
        self.set_token(token=token)

    def set_token(self, token: str) -> None:
        self.credentials(**{"Authorization": f"Bearer {token}"})


@pytest.fixture
def client() -> OAuthClient:
    app = Application.objects.create(
        client_id="default_client",
        is_first_party=True,
        skip_authorization=True,
        client_type=Application.CLIENT_PUBLIC,
        authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
    )
    ProjectVariable.objects.create(name="DEFAULT_OAUTH_CLIENT", value=app.client_id)
    return OAuthClient()


@pytest.fixture
def user() -> User:
    return UserFactory.create(
        username="test_user",
        email="test_user@example.org",
    )


@pytest.fixture
def user_client(
    client: OAuthClient,
    user: User,
) -> OAuthClient:
    client.set_user(user)
    return client


@pytest.fixture
def client_credentials_app() -> Application:
    return Application.objects.create(
        client_id="third_party_client",
        is_first_party=False,
        skip_authorization=False,
        client_type=Application.CLIENT_PUBLIC,
        authorization_grant_type=Application.GRANT_CLIENT_CREDENTIALS,
    )


@pytest.fixture
def authorization_code_third_party_app() -> Application:
    return Application.objects.create(
        client_id="third-party",
        client_secret="third-secret",
        redirect_uris="http://127.0.0.1/local/",
        client_type=Application.CLIENT_PUBLIC,
        authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
        name="Third party app",
        is_first_party=False,
    )
