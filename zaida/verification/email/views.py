from rest_framework import permissions
from rest_framework.decorators import action

from zaida.utils.views import ExtendedViewSet
from zaida.verification.email import schema
from zaida.verification.email.serializers import (
    EmailCheckSerializer,
    EmailSerializer,
)


class EmailViewSet(ExtendedViewSet):
    mixins = ("create",)
    serializer_class = EmailSerializer
    permission_classes = [permissions.IsAuthenticated]
    schema_extensions = {"create": schema.email_create}

    @schema.email_check
    @action(
        detail=False,
        methods=["post"],
        serializer_class=EmailCheckSerializer,
    )
    def check(self, request):
        return self.get_action_save_response(request, EmailCheckSerializer)
