from django import template

register = template.Library()

@register.filter
def filename(value):
    """Извлечь только имя файла без пути"""
    if not value:
        return ''
    return value.name.split('/')[-1] if hasattr(value, 'name') else str(value).split('/')[-1]
