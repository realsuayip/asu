from django.contrib import admin

from asu.models import ProjectVariable


@admin.register(ProjectVariable)
class ProjectVariableAdmin(admin.ModelAdmin):
    search_fields = ("name", "value")
    list_display = ("name", "value", "date_modified")
    readonly_fields = ("name", "date_created", "date_modified")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
