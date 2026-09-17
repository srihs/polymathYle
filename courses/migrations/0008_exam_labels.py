from django.db import migrations

# Final level list: CEFR band labelled with its Cambridge exam, A2 split into Flyers and KET.
LEVELS = [
    dict(short_code='PRE_A1', name='Pre A1 (Starters)', cefr_level='Pre A1', order=1),
    dict(short_code='A1', name='A1 (Movers)', cefr_level='A1', order=2),
    dict(short_code='A2', name='A2 (Flyers)', cefr_level='A2', order=3),
    dict(short_code='A2_KET', name='A2 (KET)', cefr_level='A2', order=4),
    dict(short_code='B1', name='B1 (PET)', cefr_level='B1', order=5),
    dict(short_code='B2', name='B2 (FCE)', cefr_level='B2', order=6),
]
NEW_LEVEL_DEFAULTS = {
    'A2_KET': dict(age_range_min=11, age_range_max=14, duration_minutes=110, icon='ri-key-2-line', color_theme='#405189',
                   description='CEFR A2 (KET): everyday written and spoken English at a basic level.'),
}
PLAIN_NAMES = {'PRE_A1': 'Pre A1', 'A1': 'A1', 'A2': 'A2', 'B1': 'B1', 'B2': 'B2'}


def apply_labels(apps, schema_editor):
    """Idempotent: relabel levels, add A2 (KET) where an earlier run merged it into A2."""
    YLELevel = apps.get_model('courses', 'YLELevel')
    Course = apps.get_model('courses', 'Course')

    for spec in LEVELS:
        code = spec['short_code']
        level = YLELevel.objects.filter(short_code__iexact=code).first()
        if level is None:
            level = YLELevel.objects.create(is_active=True, **spec, **NEW_LEVEL_DEFAULTS.get(code, {}))
        else:
            for field, value in spec.items():
                setattr(level, field, value)
            if code == 'A2' and (level.age_range_min, level.age_range_max) == (9, 14):
                level.age_range_min, level.age_range_max = 9, 12  # A2 no longer covers KET ages
            level.save()

        # Every level has at least one course
        if not Course.objects.filter(level=level).exists():
            Course.objects.get_or_create(
                code=code,
                defaults={
                    'level': level, 'name': level.name, 'order': 1,
                    'description': f'Starter course for {level.name}. Rename it or add more courses under {level.name}.',
                    'age_range_min': level.age_range_min, 'age_range_max': level.age_range_max,
                    'is_active': level.is_active,
                },
            )
        # Starter courses still carrying the plain CEFR name get the new label
        plain = PLAIN_NAMES.get(code)
        if plain:
            Course.objects.filter(level=level, code__iexact=code, name=plain).update(name=level.name)


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0007_course'),
    ]

    operations = [
        migrations.RunPython(apply_labels, migrations.RunPython.noop),
    ]
