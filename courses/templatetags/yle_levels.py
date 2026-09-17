"""
Template helpers for YLE levels, so templates never hard-code level codes.

Usage (after {% load yle_levels %}):
    {{ student.current_level|level_name }}      -> "B1"
    {{ certificate.level|level_color }}         -> "danger" (Bootstrap contextual colour)
    {{ class.level|level_icon }}                -> "ri-medal-line"

Each filter accepts a YLELevel, a short code ("B1") or a level id.
"""
from django import template

from courses.models import YLELevel

register = template.Library()

# Bootstrap colour per known level; any other level gets the fallback.
LEVEL_COLORS = {
    'PRE_A1': 'info',
    'A1': 'warning',
    'A2': 'success',
    'A2_KET': 'primary',
    'B1': 'danger',
    'B2': 'dark',
}
FALLBACK_COLOR = 'secondary'
FALLBACK_ICON = 'ri-medal-line'


def _resolve(value):
    if value is None or value == '':
        return None
    if isinstance(value, YLELevel):
        return value
    text = str(value).strip()
    if text.isdigit():
        return YLELevel.objects.filter(pk=int(text)).first()
    return YLELevel.objects.filter(short_code__iexact=text).first()


def _code(value):
    if isinstance(value, YLELevel):
        return value.short_code.upper()
    return str(value or '').strip().upper()


@register.filter
def level_color(value):
    # Short codes map directly; objects and ids are resolved to their code first
    if isinstance(value, YLELevel) or str(value or '').strip().isdigit():
        level = _resolve(value)
        code = level.short_code.upper() if level else ''
    else:
        code = _code(value)
    return LEVEL_COLORS.get(code, FALLBACK_COLOR)


@register.filter
def level_name(value):
    level = _resolve(value)
    if level:
        return level.name
    return str(value or '')


@register.filter
def level_icon(value):
    level = _resolve(value)
    return (level.icon if level and level.icon else FALLBACK_ICON)


@register.simple_tag
def active_levels():
    """{% active_levels as levels %} -> active levels in display order."""
    return YLELevel.objects.filter(is_active=True).order_by('order', 'id')
