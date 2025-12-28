from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from asu.auth.permissions import RequireFirstParty
from asu.core.utils.views import ExtendedViewSet, action
from asu.verification.models import PasswordResetVerification
from asu.verification.password import schemas
from asu.verification.password.serializers import (
    PasswordResetSerializer,
    PasswordResetVerificationSendSerializer,
    PasswordResetVerificationVerifySerializer,
)


class PasswordResetViewSet(ExtendedViewSet[PasswordResetVerification]):
    schemas = schemas.password_reset

    @action(
        detail=False,
        methods=["post"],
        serializer_class=PasswordResetVerificationSendSerializer,
        permission_classes=[RequireFirstParty],
    )
    def send(self, request: Request) -> Response:
        return self.perform_action(status_code=status.HTTP_201_CREATED)

    @action(
        detail=False,
        methods=["post"],
        serializer_class=PasswordResetVerificationVerifySerializer,
        permission_classes=[RequireFirstParty],
    )
    def verify(self, request: Request) -> Response:
        return self.perform_action()

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[RequireFirstParty],
        serializer_class=PasswordResetSerializer,
    )
    def complete(self, request: Request) -> Response:
        return self.perform_action()
