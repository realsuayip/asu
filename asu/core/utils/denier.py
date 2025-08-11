from typing import Any

from rest_framework.permissions import BasePermission


class DenyAny(BasePermission):
    """
    Deny all incoming requests.

    This is set as default permission for all views unless overridden so that
    all views explicitly declare their permissions. This bad boy requires its
    own module due to some cyclic import shenanigans.
    """

    def has_permission(self, *args: Any, **kwargs: Any) -> bool:
        return False
