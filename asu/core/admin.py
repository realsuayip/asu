from django.contrib import admin

from asu.core.models import ProjectVariable


@admin.register(ProjectVariable)
class ProjectVariableAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    search_fields = ("name", "value")
    list_display = ("name", "value", "date_modified")
    readonly_fields = ("date_created", "date_modified")
