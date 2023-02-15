from django import template

from asu.models import ProjectVariable

register = template.Library()


@register.simple_tag
def get_variable(name):
    # A function to get some constant values used in templates.
    # todo: use a cache mechanism.
    var = ProjectVariable.objects.only("value").get(name=name)
    return var.value
