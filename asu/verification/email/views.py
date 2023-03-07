from rest_framework.decorators import action

from asu.auth.permissions import RequireFirstParty, RequireUser
from asu.utils.views import ExtendedViewSet
from asu.verification.email import schema
from asu.verification.email.serializers import (
    EmailCheckSerializer,
    EmailSerializer,
)


class EmailViewSet(ExtendedViewSet):
    mixins = ("create",)
    serializer_class = EmailSerializer
    permission_classes = [RequireUser, RequireFirstParty]
    schema_extensions = {"create": schema.email_create}

    @schema.email_check
    @action(
        detail=False,
        methods=["post"],
        serializer_class=EmailCheckSerializer,
        permission_classes=[RequireUser, RequireFirstParty],
    )
    def check(self, request):
        return self.get_action_save_response(request, EmailCheckSerializer)
