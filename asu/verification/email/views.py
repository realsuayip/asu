from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from asu.auth.permissions import RequireFirstParty, RequireUser
from asu.core.utils.views import ExtendedViewSet, action
from asu.verification.email import schemas
from asu.verification.email.serializers import (
    ChangeEmailSerializer,
    EmailVerificationSendSerializer,
)
from asu.verification.models import EmailVerification


class EmailViewSet(ExtendedViewSet[EmailVerification]):
    schemas = schemas.email

    @action(
        detail=False,
        methods=["post"],
        serializer_class=EmailVerificationSendSerializer,
        permission_classes=[RequireUser, RequireFirstParty],
    )
    def send(self, request: Request) -> Response:
        return self.perform_action(status_code=status.HTTP_201_CREATED)

    @action(
        detail=False,
        methods=["post"],
        serializer_class=ChangeEmailSerializer,
        permission_classes=[RequireUser, RequireFirstParty],
    )
    def complete(self, request: Request) -> Response:
        return self.perform_action()
