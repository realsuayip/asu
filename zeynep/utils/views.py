from typing import Dict, Optional, Sequence

from rest_framework import mixins, serializers, status
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from drf_spectacular.utils import extend_schema_view

_viewset_mixin_map = {
    "list": mixins.ListModelMixin,
    "create": mixins.CreateModelMixin,
    "retrieve": mixins.RetrieveModelMixin,
    "update": mixins.UpdateModelMixin,
    "destroy": mixins.DestroyModelMixin,
}


class ViewSetMeta(type):
    def __new__(mcs, name, bases, classdict):
        cls_mixins = classdict.get("mixins")

        if cls_mixins is not None:
            for label in cls_mixins:
                try:
                    mixin = _viewset_mixin_map[label]
                except KeyError:
                    raise ValueError(
                        "%s is not a valid mixin name, use one of these: %s"
                        % (label, tuple(_viewset_mixin_map))
                    )

                if mixin in bases:
                    raise TypeError(
                        "mixins.%s already exists or duplicated in '%s'"
                        % (mixin.__name__, name)
                    )

                bases += (mixin,)

        cls = super().__new__(mcs, name, bases, classdict)
        schema_extensions = classdict.get("schema_extensions")

        if schema_extensions is not None:
            # Get related action and decorate
            # it with extension e.g. extend_schema.
            cls = extend_schema_view(**schema_extensions)(cls)

        return cls


class ExtendedViewSet(GenericViewSet, metaclass=ViewSetMeta):
    mixins: Optional[Sequence[str]] = None
    schema_extensions: Optional[Dict] = None
    serializer_classes: Dict = {}

    def get_action_save_response(
        self,
        request,
        serializer,
        status_code=status.HTTP_200_OK,
    ):
        # Similar functionality from mixins.CreateModelMixin
        # for ViewSet actions.
        assert status.is_success(status_code)
        if not isinstance(serializer, serializers.Serializer):
            serializer = serializer(
                data=request.data, context=self.get_serializer_context()
            )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        data = (
            serializer.data
            if status_code != status.HTTP_204_NO_CONTENT
            else None
        )
        return Response(data, status=status_code)

    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.serializer_class)
