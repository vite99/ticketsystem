from django import template

register = template.Library()


@register.filter
def filename(value):
    """Извлечь только имя файла без пути."""
    if not value:
        return ''
    return value.name.split('/')[-1] if hasattr(value, 'name') else str(value).split('/')[-1]


@register.filter
def fix_mojibake(value):
    """Попытаться восстановить строку, если UTF-8 был ошибочно прочитан как cp1251."""
    if value is None:
        return ''

    text = str(value)
    if not text:
        return text

    markers = ('Р', 'С', 'Ñ', 'Ð')
    if not any(marker in text for marker in markers):
        return text

    repaired_variants = []

    for source_encoding in ('cp1251', 'latin1'):
        try:
            repaired = text.encode(source_encoding).decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if repaired and repaired != text:
            repaired_variants.append(repaired)

    if not repaired_variants:
        return text

    def score(candidate):
        bad_patterns = ('Р', 'С', 'Ñ', 'Ð')
        return sum(candidate.count(pattern) for pattern in bad_patterns)

    return sorted(repaired_variants, key=score)[0]
