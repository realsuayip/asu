from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from asu.auth.permissions import RequireFirstParty
from asu.utils.views import ExtendedViewSet
from asu.verification.models import PasswordResetVerification
from asu.verification.password import schemas
from asu.verification.password.serializers import (
    PasswordResetVerificationCheckSerializer,
    PasswordResetVerificationSerializer,
)


class PasswordResetViewSet(ExtendedViewSet[PasswordResetVerification]):
    """
    This ViewSet is partly responsible for password *reset* flow, in
    other words, account recovery, in case the user forgets their
    password. The password change flow is different and not handled
    here.

    The three-step mechanism used in this flow is very similar to
    registration flow. Check out 'RegistrationViewSet' to learn
    about it.

    The only difference is, instead of asking user profile
    information, we just ask for the new password.

    The actual password change endpoint is located in 'reset_password'
    action of 'UserViewSet'.

    TODO: Should consider revoking other active tokens when password
     gets changed.
    """

    mixins = ("create",)
    serializer_class = PasswordResetVerificationSerializer
    schemas = schemas.password_reset
    permission_classes = [RequireFirstParty]

    @action(
        detail=False,
        methods=["post"],
        serializer_class=PasswordResetVerificationCheckSerializer,
        permission_classes=[RequireFirstParty],
    )
    def check(self, request: Request) -> Response:
        return self.get_action_save_response(request)
