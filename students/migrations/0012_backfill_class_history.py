from django.db import migrations


def backfill(apps, schema_editor):
    """Record the current class of students who were placed before history tracking existed."""
    Student = apps.get_model('students', 'Student')
    StudentClassHistory = apps.get_model('students', 'StudentClassHistory')
    for student in Student.objects.filter(assigned_class__isnull=False):
        if not StudentClassHistory.objects.filter(student=student).exists():
            StudentClassHistory.objects.create(
                student=student,
                change_type='ASSIGNED',
                to_class_id=student.assigned_class_id,
                to_level=student.current_level,
                note='Class assigned before history tracking',
            )


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0011_class_transfers_and_history'),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
