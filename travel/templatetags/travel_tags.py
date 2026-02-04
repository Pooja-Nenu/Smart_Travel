from django import template

register = template.Library()

@register.filter
def clean_priority(value):
    """Remove priority text in parentheses from item name."""
    if ' (' in value:
        return value.split(' (')[0]
    return value