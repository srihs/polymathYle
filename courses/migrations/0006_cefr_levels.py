from django.db import migrations

# Levels are the CEFR bands up to B2, labelled with their Cambridge exam. Existing exam levels are
# renamed in place (so classes, units, certificates, templates and teachers keep pointing at them).
# A2 has two levels: A2 (Flyers) and A2 (KET).
CEFR_LEVELS = [
    dict(short_code='PRE_A1', name='Pre A1 (Starters)', cefr_level='Pre A1', order=1, age_range_min=6, age_range_max=8,
         duration_minutes=45, icon='ri-seedling-line', color_theme='#299cdb',
         description='CEFR Pre A1: basic vocabulary, simple sentences, listening and speaking focus.'),
    dict(short_code='A1', name='A1 (Movers)', cefr_level='A1', order=2, age_range_min=8, age_range_max=10,
         duration_minutes=60, icon='ri-run-line', color_theme='#f7b84b',
         description='CEFR A1: expanded vocabulary, short conversations, introduction to reading and writing.'),
    dict(short_code='A2', name='A2 (Flyers)', cefr_level='A2', order=3, age_range_min=9, age_range_max=12,
         duration_minutes=75, icon='ri-rocket-line', color_theme='#0ab39c',
         description='CEFR A2 (Flyers): everyday English, all four skills at a basic level.'),
    dict(short_code='A2_KET', name='A2 (KET)', cefr_level='A2', order=4, age_range_min=11, age_range_max=14,
         duration_minutes=110, icon='ri-key-2-line', color_theme='#405189',
         description='CEFR A2 (KET): everyday written and spoken English at a basic level.'),
    dict(short_code='B1', name='B1 (PET)', cefr_level='B1', order=5, age_range_min=12, age_range_max=15,
         duration_minutes=140, icon='ri-medal-line', color_theme='#f06548',
         description='CEFR B1: practical everyday English for study and social situations.'),
    dict(short_code='B2', name='B2 (FCE)', cefr_level='B2', order=6, age_range_min=13, age_range_max=17,
         duration_minutes=209, icon='ri-trophy-line', color_theme='#660066',
         description='CEFR B2: confident English for study, work and independent communication.'),
]

# old short code -> CEFR short code
RENAMES = {'STARTERS': 'PRE_A1', 'MOVERS': 'A1', 'FLYERS': 'A2', 'KET': 'A2_KET', 'PET': 'B1', 'FCE': 'B2'}


def to_cefr(apps, schema_editor):
    YLELevel = apps.get_model('courses', 'YLELevel')
    Class = apps.get_model('courses', 'Class')
    Unit = apps.get_model('courses', 'Unit')
    Certificate = apps.get_model('certification', 'Certificate')
    CertificateTemplate = apps.get_model('certification', 'CertificateTemplate')
    Teacher = apps.get_model('teachers', 'Teacher')
    Student = apps.get_model('students', 'Student')
    BaselineTest = apps.get_model('students', 'BaselineTest')
    StudentClassHistory = apps.get_model('students', 'StudentClassHistory')

    by_code = {level.short_code.upper(): level for level in YLELevel.objects.all()}

    for spec in CEFR_LEVELS:
        code = spec['short_code']
        target = by_code.get(code)
        sources = [by_code[old] for old, new in RENAMES.items() if new == code and old in by_code]

        if target is None and sources:
            # Rename the first matching exam level into the CEFR level
            target = sources.pop(0)
            for field, value in spec.items():
                setattr(target, field, value)
            target.is_active = True
            target.save()
            by_code[code] = target
        elif target is None:
            target = YLELevel.objects.create(**spec)
            by_code[code] = target

        # Merge any remaining source levels into the CEFR level
        for source in sources:
            if source.pk == target.pk:
                continue
            Class.objects.filter(level=source).update(level=target)
            Unit.objects.filter(level=source).update(level=target)
            Certificate.objects.filter(level=source).update(level=target)
            CertificateTemplate.objects.filter(level=source).update(level=target)
            for teacher in Teacher.objects.filter(levels=source):
                teacher.levels.add(target)
                teacher.levels.remove(source)
            source.delete()

    # Level codes stored as text
    for old, new in RENAMES.items():
        Student.objects.filter(current_level__iexact=old).update(current_level=new)
        BaselineTest.objects.filter(recommended_level__iexact=old).update(recommended_level=new)
        BaselineTest.objects.filter(assigned_level__iexact=old).update(assigned_level=new)
        StudentClassHistory.objects.filter(from_level__iexact=old).update(from_level=new)
        StudentClassHistory.objects.filter(to_level__iexact=old).update(to_level=new)


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0005_cambridge_levels_to_b2'),
        ('teachers', '0006_teacher_levels'),
        ('certification', '0002_certificate_template_level'),
        ('students', '0015_baseline_levels_from_yle_levels'),
    ]

    operations = [
        migrations.RunPython(to_cefr, migrations.RunPython.noop),
    ]
