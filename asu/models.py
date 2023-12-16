from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.utils.translation import gettext_lazy as _

from asu.utils.cache import build_vary_key, cached_context


class ProjectVariableManager(models.Manager["ProjectVariable"]):
    BUILD_VARS: dict[str, str] = {
        "BRAND": settings.PROJECT_BRAND,
        "SUPPORT_EMAIL": settings.PROJECT_SUPPORT_EMAIL,
        "URL_ACCOUNT_CREATION": settings.PROJECT_URL_ACCOUNT_CREATION,
        "URL_PASSWORD_RESET": settings.PROJECT_URL_PASSWORD_RESET,
        "URL_TERMS": settings.PROJECT_URL_TERMS,
        "URL_PRIVACY": settings.PROJECT_URL_PRIVACY,
        "URL_SECURITY": settings.PROJECT_URL_SECURITY,
        "URL_CONTACT": settings.PROJECT_URL_CONTACT,
    }

    def get_value(self, *, name: str) -> Any:
        """
        Get a project variable, either from database or some build
        variables defined above. This function includes a subset of
        build variables which is going to be used in some restricted
        contexts such as in templates.
        """

        try:
            prefix, name = name.split(".")
            assert prefix in ["db", "build"]
        except (ValueError, AssertionError) as exc:
            raise KeyError(
                "name should contain a valid prefix i.e,"
                " 'build.VARIABLE' or 'db.VARIABLE'"
            ) from exc

        if prefix == "db":
            return self.from_db(name)
        return self.BUILD_VARS[name]

    @cached_context(key="variable", vary="name")
    def from_db(self, name: str) -> Any:
        try:
            var = self.only("value").get(name=name)
        except self.model.DoesNotExist as exc:
            raise KeyError(
                "variable '%s' could not be found in the database" % name
            ) from exc
        return var.value


class ProjectVariable(models.Model):
    name = models.TextField(_("name"), unique=True)
    value = models.JSONField(_("value"))

    date_modified = models.DateTimeField(_("date modified"), auto_now=True)
    date_created = models.DateTimeField(_("date created"), auto_now_add=True)

    objects = ProjectVariableManager()

    class Meta:
        verbose_name = _("project variable")
        verbose_name_plural = _("project variables")

    def __str__(self) -> str:
        return self.name

    def save(self, *args: Any, **kwargs: Any) -> None:
        super().save(*args, **kwargs)
        cache.delete(build_vary_key("variable", "name", self.name))
