from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('teachers', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='teacher',
            name='specializes_listening',
        ),
        migrations.RemoveField(
            model_name='teacher',
            name='specializes_reading',
        ),
        migrations.RemoveField(
            model_name='teacher',
            name='specializes_writing',
        ),
        migrations.RemoveField(
            model_name='teacher',
            name='specializes_speaking',
        ),
    ]
