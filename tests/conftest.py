from datetime import timedelta
from functools import cached_property

from django.utils import timezone

from rest_framework.test import APIClient

import pytest
from oauth2_provider.settings import oauth2_settings

from asu.auth.models import AccessToken, Application, User
from asu.core.models import ProjectVariable
from tests.factories import UserFactory


def create_default_application() -> Application:
    app = Application.objects.create(
        client_id="default_client",
        is_first_party=True,
        skip_authorization=True,
        client_type=Application.CLIENT_PUBLIC,
        authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
    )
    ProjectVariable.objects.create(name="DEFAULT_OAUTH_CLIENT", value=app.client_id)
    return app


class OAuthClient(APIClient):
    @cached_property
    def _default_application(self) -> Application:
        return create_default_application()

    def _create_access_token(
        self,
        user: User,
        scope: str,
        application: Application | None = None,
    ) -> AccessToken:
        return AccessToken.objects.create(
            user=user,
            scope=scope,
            expires=timezone.now() + timedelta(minutes=15),
            token=f"some-token-{user.pk}",
            application=application,
        )

    def set_user(
        self,
        user: User,
        /,
        *,
        scope: str | None = None,
        app: Application | None = None,
    ) -> None:
        if scope is None:
            scope = " ".join(oauth2_settings.SCOPES.keys())
        if app is None:
            app = self._default_application
        oauth = getattr(self, "_oauth", {})
        try:
            access = oauth[user.pk]
        except KeyError:
            access = self._create_access_token(user, scope, app)
        else:
            access.scope = scope
            access.user = user
            access.application = app
            access.save(update_fields=["scope", "user", "application"])
        oauth[user.pk] = access
        self._oauth = oauth
        self.set_token(access.token)

    def set_token(self, token: str) -> None:
        self.credentials(Authorization=f"Bearer {token}")


@pytest.fixture
def client() -> OAuthClient:
    return OAuthClient()


@pytest.fixture
def user() -> User:
    return UserFactory.create(
        username="test_user",
        email="test_user@example.org",
    )


@pytest.fixture
def user_client(user: User) -> OAuthClient:
    client = OAuthClient()
    client.set_user(user)
    return client


@pytest.fixture
def app_client(client_credentials_app: Application) -> OAuthClient:
    access = AccessToken.objects.create(
        scope="",
        expires=timezone.now() + timedelta(minutes=15),
        token="some-client-token",
        application=client_credentials_app,
    )
    client = OAuthClient()
    client.set_token(access.token)
    return client


@pytest.fixture
def first_party_app_client(
    client_credentials_first_party_app: Application,
) -> OAuthClient:
    access = AccessToken.objects.create(
        scope="",
        expires=timezone.now() + timedelta(minutes=15),
        token="some-client-token",
        application=client_credentials_first_party_app,
    )
    client = OAuthClient()
    client.set_token(access.token)
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
def client_credentials_first_party_app() -> Application:
    return Application.objects.create(
        client_id="first_party_client",
        is_first_party=True,
        skip_authorization=True,
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
