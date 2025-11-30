from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from asu.auth.permissions import RequireFirstParty
from asu.core.utils.views import ExtendedViewSet
from asu.verification.models import RegistrationVerification
from asu.verification.registration import schemas
from asu.verification.registration.serializers import (
    RegistrationVerificationSendSerializer,
    RegistrationVerificationVerifySerializer,
    UserCreateSerializer,
)


class RegistrationViewSet(ExtendedViewSet[RegistrationVerification]):
    schemas = schemas.registration

    @action(
        detail=False,
        methods=["post"],
        serializer_class=RegistrationVerificationSendSerializer,
        permission_classes=[RequireFirstParty],
    )
    def send(self, request: Request) -> Response:
        return self.perform_action(status_code=status.HTTP_201_CREATED)

    @action(
        detail=False,
        methods=["post"],
        serializer_class=RegistrationVerificationVerifySerializer,
        permission_classes=[RequireFirstParty],
    )
    def verify(self, request: Request) -> Response:
        return self.perform_action()

    @action(
        detail=False,
        methods=["post"],
        serializer_class=UserCreateSerializer,
        permission_classes=[RequireFirstParty],
    )
    def complete(self, request: Request) -> Response:
        return self.perform_action(status_code=status.HTTP_201_CREATED)
