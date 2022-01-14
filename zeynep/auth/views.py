from rest_framework import mixins, permissions, serializers, viewsets

from zeynep.auth.models import User


class UserPublicReadSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "display_name",
            "username",
            "date_joined",
            "url",
        )
        extra_kwargs = {"url": {"lookup_field": "username"}}


class UserUpdateSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "display_name",
            "username",
            "gender",
            "birth_date",
            "url",
        )
        extra_kwargs = {"url": {"lookup_field": "username"}}


class UserPermissions(permissions.IsAuthenticatedOrReadOnly):
    def has_object_permission(self, request, view, obj):
        has_base_permission = super().has_object_permission(request, view, obj)

        if view.action == "partial_update":
            # Only self-update allowed.
            return (request.user == obj) and has_base_permission

        return has_base_permission


class UserViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    lookup_field = "username"
    http_method_names = ["get", "patch", "head", "options"]
    permission_classes = [UserPermissions]

    def get_queryset(self):
        if self.action == "partial_update":
            return User.objects.active()
        return User.objects.visible()

    def get_serializer_class(self):
        if self.action == "partial_update":
            return UserUpdateSerializer
        return UserPublicReadSerializer
