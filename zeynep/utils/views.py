from typing import Dict, Optional

from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet

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

        return super().__new__(mcs, name, bases, classdict)


class ExtendedViewSet(GenericViewSet, metaclass=ViewSetMeta):
    schema_extensions: Optional[Dict] = None

    def __new__(cls, *args, **kwargs):
        if cls.schema_extensions is not None:
            # Get related action and decorate
            # it with extension e.g. extend_schema.
            for name, extension in cls.schema_extensions.items():
                action = getattr(cls, name)
                setattr(cls, name, extension(action))

        return super().__new__(cls)
