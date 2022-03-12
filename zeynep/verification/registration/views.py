from rest_framework.decorators import action

from zeynep.utils.views import ExtendedViewSet
from zeynep.verification.registration import schema
from zeynep.verification.registration.serializers import (
    RegistrationCheckSerializer,
    RegistrationSerializer,
)


class RegistrationViewSet(ExtendedViewSet):
    mixins = ("create",)
    serializer_class = RegistrationSerializer
    schema_extensions = {"create": schema.registration_create}

    @schema.registration_check
    @action(
        detail=False,
        methods=["post"],
        serializer_class=RegistrationCheckSerializer,
    )
    def check(self, request):
        return self.get_action_save_response(
            request, RegistrationCheckSerializer
        )
