from rest_framework.decorators import action

from asu.auth.permissions import RequireFirstParty, RequireUser
from asu.utils.views import ExtendedViewSet
from asu.verification.email import schema
from asu.verification.email.serializers import (
    EmailCheckSerializer,
    EmailSerializer,
)


class EmailViewSet(ExtendedViewSet):
    """
    This ViewSet is responsible for e-email change flow, in which the
    user receives a verification code to their new email address (this
    is done in 'create' action). Once they confirm the code using the
    'check' action, their email is changed.

    This flow does not require consent since it only entails two steps:
    'send' & 'verify' the code. There is no interim step such as in
    registration, where the user fills out profile information or in
    password reset, we ask for new password.

    TODO: Should consider revoking other active tokens when email
     gets changed.
    """

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
