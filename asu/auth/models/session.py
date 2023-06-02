from django.contrib.sessions.base_session import AbstractBaseSession
from django.db import models
from django.utils.translation import gettext_lazy as _


class Session(AbstractBaseSession):
    """
    Extends Django's default session model to include the additional
    fields below. `user` is not set as foreign key to keep the session
    data even if the user gets deleted.
    """

    user = models.BigIntegerField(_("user"), null=True, blank=True)
    user_agent = models.TextField(_("user agent"), blank=True)
    ip = models.GenericIPAddressField(_("ip address"), null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["user"])]
