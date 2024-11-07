from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from asu.auth.permissions import RequireFirstParty, RequireUser
from asu.utils.views import ExtendedViewSet
from asu.verification.email import schemas
from asu.verification.email.serializers import EmailCheckSerializer, EmailSerializer
from asu.verification.models import EmailVerification


class EmailViewSet(mixins.CreateModelMixin, ExtendedViewSet[EmailVerification]):
    """
    This ViewSet is responsible for e-email change flow, in which the
    user receives a verification code to their new email address (this
    is done in 'create' action). Once they confirm the code using the
    'check' action, their email is changed.

    This flow does not require consent since it only entails two steps:
    'send' & 'verify' the code. There is no interim step such as in
    registration, where the user fills out profile information or in
    password reset, we ask for new password.
    """

    serializer_class = EmailSerializer
    permission_classes = [RequireUser, RequireFirstParty]
    schemas = schemas.email

    @action(
        detail=False,
        methods=["post"],
        serializer_class=EmailCheckSerializer,
        permission_classes=[RequireUser, RequireFirstParty],
    )
    def check(self, request: Request) -> Response:
        return self.get_action_save_response(request)
