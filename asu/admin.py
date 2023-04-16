from django.contrib import admin
from django.http import HttpRequest

from asu.models import ProjectVariable


@admin.register(ProjectVariable)
class ProjectVariableAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    search_fields = ("name", "value")
    list_display = ("name", "value", "date_modified")
    readonly_fields = ("name", "date_created", "date_modified")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: ProjectVariable | None = None
    ) -> bool:
        return False
