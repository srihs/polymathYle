"""
Class allocation for students.

Rules:
- A class is picked when the student is enrolled (from classes at the student's level).
- If no class is picked (e.g. all full), it can be assigned once later.
- Once a student has a class it is locked; changes go through transfer requests
  or promotion, not free-form edits.
"""
from django.db.models import Count, Q

from courses.models import Class

# Schedule preference slots on the application form
MORNING_CUTOFF = '12:00'


def refresh_class_enrollment(class_ids):
    """Recalculate current_enrollment (active students) for the given class ids."""
    class_ids = {cid for cid in class_ids if cid}
    if not class_ids:
        return
    counts = Class.objects.filter(id__in=class_ids).annotate(
        active=Count('enrolled_students', filter=Q(enrolled_students__is_active=True))
    ).values_list('id', 'active')
    for class_id, active in counts:
        Class.objects.filter(id=class_id).update(current_enrollment=active)


def _slot(from_time):
    return 'morning' if (from_time or '') < MORNING_CUTOFF else 'afternoon'


def schedule_summary(class_obj):
    """e.g. 'Monday 14:00-15:30, Saturday 09:00-10:30'"""
    return ', '.join(
        f"{s.get('day', '')} {s.get('from_time', '')}-{s.get('to_time', '')}".strip()
        for s in (class_obj.schedule or [])
    )


def preference_match(class_obj, preferences):
    """
    Compare a class schedule with application schedule preferences
    ({'monday': ['afternoon'], 'saturday': ['morning']}).
    Returns 'full', 'partial', 'none', or None when there's nothing to compare.
    """
    sessions = class_obj.schedule or []
    if not preferences or not isinstance(preferences, dict) or not sessions:
        return None
    matched = sum(
        1 for s in sessions
        if _slot(s.get('from_time')) in (preferences.get(str(s.get('day', '')).lower()) or [])
    )
    if matched == len(sessions):
        return 'full'
    return 'partial' if matched else 'none'


def class_options(preferences=None):
    """
    Active classes with seat and schedule info, best preference matches first.
    Each option: id, label, level (short code), schedule, teachers, seats_left, is_full, match.
    """
    classes = Class.objects.filter(is_active=True).select_related('level').annotate(
        active=Count('enrolled_students', filter=Q(enrolled_students__is_active=True))
    )
    match_rank = {'full': 0, 'partial': 1, None: 2, 'none': 3}
    options = []
    for c in classes:
        seats_left = max(c.max_students - c.active, 0)
        teachers = sorted({s.get('teacher_name') for s in (c.schedule or []) if s.get('teacher_name')})
        options.append({
            'id': c.id,
            'label': f'{c.class_name} ({c.class_code})',
            'level': c.level.short_code.upper(),
            'schedule': schedule_summary(c),
            'teachers': ', '.join(teachers),
            'location': c.get_location_display(),
            'room': c.room_number,
            'seats_left': seats_left,
            'max_students': c.max_students,
            'is_full': seats_left == 0,
            'match': preference_match(c, preferences),
        })
    options.sort(key=lambda o: (o['is_full'], match_rank[o['match']], o['label']))
    return options


class ClassAssignmentError(Exception):
    pass


def assign_class(student, class_id):
    """
    Assign a class to a student who doesn't have one yet.
    Locks the class row so two enrollments can't take the last seat.
    Must be called inside a transaction; the caller saves the student.
    """
    if student.pk and student.assigned_class_id:
        raise ClassAssignmentError(
            'This student already has a class. Use a transfer request or promotion to change it.'
        )
    try:
        class_obj = Class.objects.select_for_update().select_related('level').get(id=class_id, is_active=True)
    except (Class.DoesNotExist, ValueError, TypeError):
        raise ClassAssignmentError('The selected class does not exist or is no longer active.')

    if class_obj.level.short_code.upper() != (student.current_level or '').upper():
        raise ClassAssignmentError(
            f'{class_obj.class_name} is a {class_obj.level.name} class, but the student is at a different level.'
        )

    taken = class_obj.enrolled_students.filter(is_active=True).count()
    if taken >= class_obj.max_students:
        raise ClassAssignmentError(f'{class_obj.class_name} is full ({class_obj.max_students} students).')

    student.assigned_class = class_obj
    return class_obj
