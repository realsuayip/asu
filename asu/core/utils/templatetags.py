from typing import Any

from django import template

from asu.core.models import ProjectVariable

register = template.Library()


@register.simple_tag
def get_variable(name: str) -> Any:
    """
    A template tag to get some constant values used in templates:
         {% get_variable "build.BRAND" as brand %}
         The brand is: {{ brand }}
    """
    return ProjectVariable.objects.get_value(name=name)
