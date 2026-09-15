from django.db import migrations

# Cambridge English ladder up to B2. Existing levels (matched by short code) are left untouched.
LEVELS = [
    dict(short_code='STARTERS', name='Pre A1 Starters', cefr_level='Pre A1', order=1, age_range_min=6, age_range_max=8,
         duration_minutes=45, icon='ri-seedling-line', color_theme='#299cdb',
         description='Young Learners beginner level: basic vocabulary, simple sentences, listening and speaking focus.'),
    dict(short_code='MOVERS', name='A1 Movers', cefr_level='A1', order=2, age_range_min=8, age_range_max=10,
         duration_minutes=60, icon='ri-run-line', color_theme='#f7b84b',
         description='Young Learners elementary level: expanded vocabulary, short conversations, reading and writing introduction.'),
    dict(short_code='FLYERS', name='A2 Flyers', cefr_level='A2', order=3, age_range_min=9, age_range_max=12,
         duration_minutes=75, icon='ri-rocket-line', color_theme='#0ab39c',
         description='Young Learners pre-intermediate level: advanced vocabulary, complex sentences, all four skills.'),
    dict(short_code='KET', name='A2 Key', cefr_level='A2', order=4, age_range_min=11, age_range_max=14,
         duration_minutes=110, icon='ri-key-2-line', color_theme='#405189',
         description='A2 Key (for Schools): everyday written and spoken English at a basic level.'),
    dict(short_code='PET', name='B1 Preliminary', cefr_level='B1', order=5, age_range_min=12, age_range_max=15,
         duration_minutes=140, icon='ri-medal-line', color_theme='#6559cc',
         description='B1 Preliminary (for Schools): practical everyday English for study and social situations.'),
    dict(short_code='FCE', name='B2 First', cefr_level='B2', order=6, age_range_min=13, age_range_max=17,
         duration_minutes=209, icon='ri-trophy-line', color_theme='#660066',
         description='B2 First (for Schools): confident English for study, work and independent communication.'),
]


def add_levels(apps, schema_editor):
    YLELevel = apps.get_model('courses', 'YLELevel')
    for level in LEVELS:
        YLELevel.objects.get_or_create(short_code=level['short_code'], defaults=level)


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0004_class_location'),
    ]

    operations = [
        migrations.RunPython(add_levels, migrations.RunPython.noop),
    ]
