from django.contrib.auth.models import UserManager as DjangoUserManager
from django.core import signing
from django.db.models import Q


class UserManager(DjangoUserManager):
    def public(self):
        """
        Users who are publicly available.
        """
        return self.exclude(
            Q(is_active=False) | Q(is_frozen=True) | Q(is_private=True)
        )

    def active(self):
        """
        Users who are publicly available and can
        perform actions on the application.
        """
        return self.exclude(Q(is_active=False) | Q(is_frozen=True))

    def verify_ticket(self, ticket, scope, *, max_age):  # noqa
        signer = signing.TimestampSigner(salt=scope)
        return signer.unsign(ticket, max_age=max_age)
