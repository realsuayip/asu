from rest_framework.decorators import action

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
        return self.get_action_save_response(
            request, RegistrationCheckSerializer
        )
