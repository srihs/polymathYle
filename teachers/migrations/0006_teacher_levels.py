from django.db import migrations, models


def copy_level_flags(apps, schema_editor):
    """Move teaches_starters/movers/flyers flags onto the new levels relation."""
    Teacher = apps.get_model('teachers', 'Teacher')
    YLELevel = apps.get_model('courses', 'YLELevel')
    levels = {level.short_code.upper(): level for level in YLELevel.objects.all()}
    for teacher in Teacher.objects.all():
        for flag, code in (('teaches_starters', 'STARTERS'), ('teaches_movers', 'MOVERS'), ('teaches_flyers', 'FLYERS')):
            if getattr(teacher, flag) and code in levels:
                teacher.levels.add(levels[code])


def restore_level_flags(apps, schema_editor):
    Teacher = apps.get_model('teachers', 'Teacher')
    for teacher in Teacher.objects.all():
        codes = {code.upper() for code in teacher.levels.values_list('short_code', flat=True)}
        teacher.teaches_starters = 'STARTERS' in codes
        teacher.teaches_movers = 'MOVERS' in codes
        teacher.teaches_flyers = 'FLYERS' in codes
        teacher.save(update_fields=['teaches_starters', 'teaches_movers', 'teaches_flyers'])


class Migration(migrations.Migration):

    dependencies = [
        ('teachers', '0005_delete_teacherhourlyrate'),
        ('courses', '0005_cambridge_levels_to_b2'),
    ]

    operations = [
        migrations.AddField(
            model_name='teacher',
            name='levels',
            field=models.ManyToManyField(blank=True, related_name='teachers', to='courses.ylelevel'),
        ),
        migrations.RunPython(copy_level_flags, restore_level_flags),
        migrations.RemoveField(model_name='teacher', name='teaches_starters'),
        migrations.RemoveField(model_name='teacher', name='teaches_movers'),
        migrations.RemoveField(model_name='teacher', name='teaches_flyers'),
    ]
