from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, 0)

@register.filter
def id_list(queryset):
    return ','.join(str(obj.id) for obj in queryset)