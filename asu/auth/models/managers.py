from typing import TYPE_CHECKING

from django.contrib.auth.models import UserManager as DjangoUserManager
from django.core import signing
from django.db.models import Q, QuerySet

if TYPE_CHECKING:
    from asu.auth.models import User


class UserManager(DjangoUserManager["User"]):
    def public(self) -> QuerySet["User"]:
        """
        Users who are publicly available.
        """
        return self.exclude(
            Q(is_active=False) | Q(is_frozen=True) | Q(is_private=True)
        )

    def active(self) -> QuerySet["User"]:
        """
        Users who are publicly available and can
        perform actions on the application.
        """
        return self.exclude(Q(is_active=False) | Q(is_frozen=True))

    def verify_ticket(
        self, ticket: str, *, ident: str, max_age: int
    ) -> tuple[int, str]:
        signer = signing.TimestampSigner()
        obj = signer.unsign_object(ticket, max_age=max_age)
        given_ident, value = obj.get("ident"), obj.get("value")
        if (not ident) or (not value) or ident != given_ident:
            raise signing.BadSignature
        pk, uuid = value
        return pk, uuid
