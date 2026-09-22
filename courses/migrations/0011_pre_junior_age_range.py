from django.db import migrations

# Pre-Junior takes 4 and 5 year olds; Pre A1 (Starters) begins at 6.
AGES = (4, 5)
PREVIOUS_AGES = (3, 5)


def set_ages(apps, schema_editor):
    _apply(apps, AGES)


def restore_ages(apps, schema_editor):
    _apply(apps, PREVIOUS_AGES)


def _apply(apps, ages):
    YLELevel = apps.get_model('courses', 'YLELevel')
    Course = apps.get_model('courses', 'Course')
    low, high = ages

    level = YLELevel.objects.filter(short_code__iexact='PRE_JUNIOR').first()
    if level is None:
        return
    YLELevel.objects.filter(pk=level.pk).update(age_range_min=low, age_range_max=high)
    # The starter course follows the level; courses staff have edited keep their own ages
    Course.objects.filter(level=level, code__iexact='PRE_JUNIOR').update(age_range_min=low, age_range_max=high)


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0010_course_order_help_text'),
    ]

    operations = [
        migrations.RunPython(set_ages, restore_ages),
    ]
