from collections.abc import Iterable

from django.conf import settings
from django.db import models
from django.db.models import Func
from django.db.models.base import ModelBase
from django.db.models.expressions import DatabaseDefault
from django.db.models.functions import Now
from django.utils.translation import gettext_lazy as _

# We cannot enforce `updated` field for `update_fields` in these
# models since update is being made in third party code.
THIRD_PARTY_MODELS = (settings.AUTH_USER_MODEL,)


class UUIDv7(Func):
    function = "uuidv7"
    output_field = models.UUIDField()


class AutoUpdatedField(models.DateTimeField):
    def pre_save(self, model_instance: models.Model, add: bool) -> object:
        return self.get_default()


class Base(models.Model):
    id = models.UUIDField(_("id"), primary_key=True, db_default=UUIDv7())

    created = models.DateTimeField(_("created"), db_default=Now())
    updated = AutoUpdatedField(_("updated"), db_default=Now(), editable=False)

    class Meta:
        abstract = True

    def save(
        self,
        *,
        force_insert: bool | tuple[ModelBase, ...] = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> None:
        if (
            not force_insert
            and update_fields is None
            and (force_update or not isinstance(self.pk, DatabaseDefault))
        ):
            raise ValueError("'update_fields' is not set")
        if (
            update_fields is not None
            and "updated" not in update_fields
            and self._meta.label not in THIRD_PARTY_MODELS
            and "updated" in [f.name for f in self._meta.concrete_fields]
        ):
            raise ValueError("'update_fields' must contain the field 'updated'")
        return super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )
