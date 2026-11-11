from django import template

from apps.tenants.validators import format_siret

register = template.Library()


@register.filter(name="siret")
def siret(value):
    """ "12345678900012" -> "123 456 789 00012": easier to read and to check by eye."""
    return format_siret(value)
