from rest_framework.decorators import action

from asu.auth.permissions import RequireFirstParty
from asu.utils.views import ExtendedViewSet
from asu.verification.registration import schema
from asu.verification.registration.serializers import (
    RegistrationCheckSerializer,
    RegistrationSerializer,
)


class RegistrationViewSet(ExtendedViewSet):
    """
    This ViewSet is partly responsible for registration flow. The
    flow entails three steps:
    -----
        a. send a code to email [RegistrationViewSet.create]
        b. ask for verification [RegistrationViewSet.check]
        c. ask for other information [UserViewSet.create]
    -----

    The steps 'a' and 'b' done subsequently in client, which ask for the
    email first. Once the email is verified, a consent is issued.

    A 'consent' is a signed token that holds information about the
    verified email. It is not akin to a JWT token since the flow has
    state on the database, in fact, it just contains the ID for that
    verification object.

    During the user creation, the token is used to match the email
    given. If emails do match, the user is saved to the database.

    TODO: After user creation, we need to issue access & refresh tokens
     so they they can be authenticated immediately.
    """

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
