from rest_framework.request import Request

from asu.auth.models import AccessToken, User


class UserRequest(Request):
    """
    WARNING: `request.user` will be `None` in case 'RequireUser'
    permission is not specified and client-credentials flow is used.
    Be sure to include 'RequireUser' permission class when using
    `request.user`.
    """

    user: User
    auth: AccessToken | None
