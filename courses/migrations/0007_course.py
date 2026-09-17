import django.db.models.deletion
from django.db import migrations, models


def create_starter_courses(apps, schema_editor):
    """One course per CEFR level (named like the level) so existing classes keep a course."""
    YLELevel = apps.get_model('courses', 'YLELevel')
    Course = apps.get_model('courses', 'Course')
    Class = apps.get_model('courses', 'Class')
    for level in YLELevel.objects.all():
        course, _ = Course.objects.get_or_create(
            code=level.short_code.upper(),
            defaults={
                'level': level, 'name': level.name, 'order': 1,
                'description': f'Starter course for {level.name}. Rename it or add more courses under {level.name}.',
                'age_range_min': level.age_range_min, 'age_range_max': level.age_range_max,
                'is_active': level.is_active,
            },
        )
        Class.objects.filter(level=level, course__isnull=True).update(course=course)


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0006_cefr_levels'),
    ]

    operations = [
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('code', models.CharField(max_length=20, unique=True)),
                ('description', models.TextField(blank=True)),
                ('order', models.IntegerField(default=0, help_text='Order within the CEFR level')),
                ('age_range_min', models.IntegerField(blank=True, null=True)),
                ('age_range_max', models.IntegerField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('level', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='courses', to='courses.ylelevel')),
            ],
            options={'ordering': ['level__order', 'order', 'name']},
        ),
        migrations.AddField(
            model_name='class',
            name='course',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='classes', to='courses.course'),
        ),
        migrations.RunPython(create_starter_courses, migrations.RunPython.noop),
    ]
