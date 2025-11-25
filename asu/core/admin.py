from django.contrib import admin

from asu.core.models import ProjectVariable


@admin.register(ProjectVariable)
class ProjectVariableAdmin(admin.ModelAdmin[ProjectVariable]):
    search_fields = ("name", "value")
    list_display = ("name", "value", "updated_at")
    readonly_fields = ("created_at", "updated_at")
