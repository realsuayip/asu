from rest_framework.decorators import action

from asu.utils.views import ExtendedViewSet
from asu.verification.password import schema
from asu.verification.password.serializers import (
    PasswordResetVerificationCheckSerializer,
    PasswordResetVerificationSerializer,
)


class PasswordResetViewSet(ExtendedViewSet):
    mixins = ("create",)
    serializer_class = PasswordResetVerificationSerializer
    schema_extensions = {"create": schema.password_reset_create}

    @schema.password_reset_check
    @action(
        detail=False,
        methods=["post"],
        serializer_class=PasswordResetVerificationCheckSerializer,
    )
    def check(self, request):
        return self.get_action_save_response(
            request, PasswordResetVerificationCheckSerializer
        )
