from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from asu.auth.permissions import RequireFirstParty
from asu.core.utils.views import ExtendedViewSet
from asu.verification.models import RegistrationVerification
from asu.verification.registration import schemas
from asu.verification.registration.serializers import (
    RegistrationCheckSerializer,
    RegistrationSerializer,
)


class RegistrationViewSet(
    mixins.CreateModelMixin, ExtendedViewSet[RegistrationVerification]
):
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
    """

    serializer_class = RegistrationSerializer
    permission_classes = [RequireFirstParty]
    schemas = schemas.registration

    @action(
        detail=False,
        methods=["post"],
        serializer_class=RegistrationCheckSerializer,
        permission_classes=[RequireFirstParty],
    )
    def check(self, request: Request) -> Response:
        return self.get_action_save_response(request)
