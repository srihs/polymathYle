from django.db import migrations

# Polymath's own level, before Pre A1. It is not a CEFR band, so it carries no cefr_level.
PRE_JUNIOR = dict(
    short_code='PRE_JUNIOR', name='Pre-Junior', cefr_level='', order=1,
    age_range_min=3, age_range_max=5, duration_minutes=30,
    icon='ri-emotion-happy-line', color_theme='#6559cc',
    description="Polymath's own starting level, before CEFR Pre A1: listening, speaking and play-based English.",
)
# The CEFR levels move down one place to make room for it
CEFR_ORDER = ['PRE_A1', 'A1', 'A2', 'A2_KET', 'B1', 'B2']


def add_pre_junior(apps, schema_editor):
    """Idempotent: add the Pre-Junior level first in the order, with a starter course."""
    YLELevel = apps.get_model('courses', 'YLELevel')
    Course = apps.get_model('courses', 'Course')

    level = YLELevel.objects.filter(short_code__iexact=PRE_JUNIOR['short_code']).first()
    if level is None:
        level = YLELevel.objects.create(is_active=True, **PRE_JUNIOR)
    else:
        for field, value in PRE_JUNIOR.items():
            setattr(level, field, value)
        level.save()

    for position, code in enumerate(CEFR_ORDER, start=2):
        YLELevel.objects.filter(short_code__iexact=code).update(order=position)

    if not Course.objects.filter(level=level).exists():
        Course.objects.get_or_create(
            code=PRE_JUNIOR['short_code'],
            defaults={
                'level': level, 'name': level.name, 'order': 1,
                'description': f'Starter course for {level.name}. Rename it or add more courses under {level.name}.',
                'age_range_min': level.age_range_min, 'age_range_max': level.age_range_max,
                'is_active': True,
            },
        )


def remove_pre_junior(apps, schema_editor):
    """Put the CEFR order back and drop Pre-Junior, unless something is using it."""
    YLELevel = apps.get_model('courses', 'YLELevel')
    Course = apps.get_model('courses', 'Course')

    for position, code in enumerate(CEFR_ORDER, start=1):
        YLELevel.objects.filter(short_code__iexact=code).update(order=position)

    level = YLELevel.objects.filter(short_code__iexact=PRE_JUNIOR['short_code']).first()
    if level is None:
        return
    in_use = (
        level.classes.exists()
        or level.units.exists()
        or Course.objects.filter(level=level).exclude(code=PRE_JUNIOR['short_code']).exists()
        or Course.objects.filter(level=level, classes__isnull=False).exists()
    )
    if in_use:
        return
    Course.objects.filter(level=level, code=PRE_JUNIOR['short_code']).delete()
    level.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0008_exam_labels'),
    ]

    operations = [
        migrations.RunPython(add_pre_junior, remove_pre_junior),
    ]
