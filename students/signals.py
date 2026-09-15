"""
Keep Class.current_enrollment in sync with the students assigned to each class,
whatever changes the student (enrollment, edit page, admin, deactivation, deletion).
"""
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .class_allocation import refresh_class_enrollment
from .models import Student


@receiver(pre_save, sender=Student)
def remember_previous_class(sender, instance, **kwargs):
    previous = None
    if instance.pk:
        previous = Student.objects.filter(pk=instance.pk).values_list('assigned_class_id', flat=True).first()
    instance._previous_class_id = previous


@receiver(post_save, sender=Student)
def update_enrollment_after_save(sender, instance, **kwargs):
    refresh_class_enrollment({instance.assigned_class_id, getattr(instance, '_previous_class_id', None)})


@receiver(post_delete, sender=Student)
def update_enrollment_after_delete(sender, instance, **kwargs):
    refresh_class_enrollment({instance.assigned_class_id})
