from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0003_make_class_dates_optional'),
    ]

    operations = [
        migrations.AddField(
            model_name='class',
            name='location',
            # Existing classes get an empty location; it is required when they are next edited
            field=models.CharField(
                choices=[('NAWINNA', 'Nawinna'), ('WATTEGEDARA', 'Wattegedara'), ('KOTTAWA', 'Kottawa')],
                default='',
                max_length=20,
            ),
            preserve_default=False,
        ),
    ]
