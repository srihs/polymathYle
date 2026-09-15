from django.db import migrations
from django.db.models import Count, Q


def refresh_enrollment(apps, schema_editor):
    """current_enrollment was never updated before; recalculate it from assigned students."""
    Class = apps.get_model('courses', 'Class')
    for class_obj in Class.objects.annotate(
        active=Count('enrolled_students', filter=Q(enrolled_students__is_active=True))
    ):
        Class.objects.filter(id=class_obj.id).update(current_enrollment=class_obj.active)


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0008_application_document1_application_document1_type_and_more'),
        ('courses', '0002_make_cefr_level_optional'),
    ]

    operations = [
        migrations.RunPython(refresh_enrollment, migrations.RunPython.noop),
    ]
