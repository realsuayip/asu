from rest_framework.decorators import action

from asu.auth.permissions import RequireFirstParty
from asu.utils.views import ExtendedViewSet
from asu.verification.registration import schema
from asu.verification.registration.serializers import (
    RegistrationCheckSerializer,
    RegistrationSerializer,
)


class RegistrationViewSet(ExtendedViewSet):
    mixins = ("create",)
    serializer_class = RegistrationSerializer
    permission_classes = [RequireFirstParty]
    schema_extensions = {"create": schema.registration_create}

    @schema.registration_check
    @action(
        detail=False,
        methods=["post"],
        serializer_class=RegistrationCheckSerializer,
        permission_classes=[RequireFirstParty],
    )
    def check(self, request):
        return self.get_action_save_response(
            request, RegistrationCheckSerializer
        )
