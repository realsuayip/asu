from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from zeynep.utils.views import ExtendedViewSet
from zeynep.verification.email.serializers import (
    EmailCheckSerializer,
    EmailSerializer,
)


class EmailViewSet(ExtendedViewSet):
    mixins = ("create",)
    serializer_class = EmailSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(
        detail=False,
        methods=["post"],
        serializer_class=EmailCheckSerializer,
    )
    def check(self, request):
        serializer = EmailCheckSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        return Response(serializer.save(), status=200)
