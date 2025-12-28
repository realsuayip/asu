from typing import cast

from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.views import APIView

from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from oauth2_provider.contrib.rest_framework.permissions import TokenHasScope

from asu.auth.models import AccessToken


class OAuthPermission(BasePermission):
    def has_oauth_permission(self, request: Request, view: APIView) -> bool:
        raise NotImplementedError

    def has_alternative_permission(self, request: Request, view: APIView) -> bool:
        # If authenticated through other mediums such as sessions, allow
        # permission. Useful *ONLY* for browsable api and tests.
        oauth2authenticated = False
        is_authenticated = IsAuthenticated().has_permission(request, view)
        if is_authenticated:
            oauth2authenticated = isinstance(
                request.successful_authenticator, OAuth2Authentication
            )
        return is_authenticated and (not oauth2authenticated)

    def has_permission(self, request: Request, view: APIView) -> bool:
        has_alternative = self.has_alternative_permission(request, view)
        has_oauth = self.has_oauth_permission(request, view)
        return has_alternative or has_oauth


class RequireFirstParty(OAuthPermission):
    """
    Allow permission if the related OAuth application is from first
    party. Identified by 'is_first_party' attribute.
    """

    def has_oauth_permission(self, request: Request, view: APIView) -> bool:
        token = cast("AccessToken", request.auth)
        return bool(token and token.application.is_first_party)


class RequireToken(OAuthPermission):
    """
    Make sure the request has a token associated with it. This way,
    unauthenticated requests are denied. This is a bit similar to
    'permissions.IsAuthenticated' however it does not require a user.
    """

    def has_oauth_permission(self, request: Request, view: APIView) -> bool:
        # In the context of OAuth2 authentication, this is set to
        # a token instance (regardless of the flow).
        return bool(request.auth)


class RequireUser(OAuthPermission):
    """
    Make sure the request has user associated with it, useful in
    contexts where user-specific actions are done, such as editing of
    their profile.
    """

    def has_oauth_permission(self, request: Request, view: APIView) -> bool:
        return bool(request.auth) and bool(request.user)


class RequireScope(OAuthPermission):
    """
    Make sure user has specified scopes; the scopes are specified
    in related view's class body.
    """

    has_oauth_permission = TokenHasScope.has_permission

    def get_scopes(self, request: Request, view: APIView) -> list[str]:
        return view.get_required_scopes()  # type: ignore[attr-defined, no-any-return]
