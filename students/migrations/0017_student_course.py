import django.db.models.deletion
from django.db import migrations, models


def link_students_to_courses(apps, schema_editor):
    """Students and history entries point at the starter course of their level."""
    Student = apps.get_model('students', 'Student')
    StudentClassHistory = apps.get_model('students', 'StudentClassHistory')
    Course = apps.get_model('courses', 'Course')
    starter = {c.code.upper(): c for c in Course.objects.all()}
    for student in Student.objects.filter(current_course__isnull=True):
        # Prefer the course of the student's class; otherwise the starter course for their level
        course = None
        if student.assigned_class_id:
            course = Course.objects.filter(classes__id=student.assigned_class_id).first()
        course = course or starter.get((student.current_level or '').upper())
        if course:
            student.current_course = course
            student.save(update_fields=['current_course'])
    for entry in StudentClassHistory.objects.all():
        changed = []
        if entry.from_class_id and not entry.from_course_id:
            entry.from_course = Course.objects.filter(classes__id=entry.from_class_id).first()
            changed.append('from_course')
        if entry.to_class_id and not entry.to_course_id:
            entry.to_course = Course.objects.filter(classes__id=entry.to_class_id).first()
            changed.append('to_course')
        if changed:
            entry.save(update_fields=changed)


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0016_student_default_level_pre_a1'),
        ('courses', '0007_course'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='current_course',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='students', to='courses.course'),
        ),
        migrations.AddField(
            model_name='studentclasshistory',
            name='from_course',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='courses.course'),
        ),
        migrations.AddField(
            model_name='studentclasshistory',
            name='to_course',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='courses.course'),
        ),
        migrations.RunPython(link_students_to_courses, migrations.RunPython.noop),
    ]
