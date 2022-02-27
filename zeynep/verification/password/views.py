from rest_framework.decorators import action
from rest_framework.response import Response

from zeynep.utils.views import ExtendedViewSet
from zeynep.verification.password.serializers import (
    PasswordResetSerializer,
    RegistrationCheckSerializer,
)


class PasswordResetViewSet(ExtendedViewSet):
    mixins = ("create",)
    serializer_class = PasswordResetSerializer

    @action(
        detail=False,
        methods=["post"],
        serializer_class=RegistrationCheckSerializer,
    )
    def check(self, request):
        serializer = RegistrationCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.save(), status=200)
