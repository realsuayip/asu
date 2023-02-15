from django.db import models
from django.utils.translation import gettext_lazy as _


class ProjectVariable(models.Model):
    name = models.TextField(_("name"), unique=True)
    value = models.TextField(_("value"))

    date_modified = models.DateTimeField(_("date modified"), auto_now=True)
    date_created = models.DateTimeField(_("date created"), auto_now_add=True)

    class Meta:
        verbose_name = _("project variable")
        verbose_name_plural = _("project variables")

    def __str__(self):
        return self.name
