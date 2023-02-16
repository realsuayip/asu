from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class ProjectVariableManager(models.Manager):
    BUILD_VARS = {
        "BRAND": settings.PROJECT_BRAND,
        "SUPPORT_EMAIL": settings.PROJECT_SUPPORT_EMAIL,
    }

    def get_value(self, *, name: str) -> str:
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
            # Todo: Employ a cache mechanism here.
            try:
                var = self.only("value").get(name=name)
            except self.model.DoesNotExist as exc:
                raise KeyError(
                    "variable '%s' could not be found in the database" % name
                ) from exc

            return var.value
        return self.BUILD_VARS[name]


class ProjectVariable(models.Model):
    name = models.TextField(_("name"), unique=True)
    value = models.TextField(_("value"))

    date_modified = models.DateTimeField(_("date modified"), auto_now=True)
    date_created = models.DateTimeField(_("date created"), auto_now_add=True)

    objects = ProjectVariableManager()

    class Meta:
        verbose_name = _("project variable")
        verbose_name_plural = _("project variables")

    def __str__(self):
        return self.name
