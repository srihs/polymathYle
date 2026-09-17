"""
Class allocation for students.

Rules:
- A class is picked when the student is enrolled (from classes of the student's course).
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
    Each option: id, label, course_id, course, level (short code), schedule, teachers, seats_left, is_full, match.
    """
    classes = Class.objects.filter(is_active=True).select_related('level', 'course').annotate(
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
            'course_id': c.course_id,
            'course': c.course.name if c.course_id else '',
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


def _same_course(class_obj, student):
    """A class fits a student when it runs the student's course (or, with no course yet, their level)."""
    if student.current_course_id:
        return class_obj.course_id == student.current_course_id
    return class_obj.level.short_code.upper() == (student.current_level or '').upper()


def _course_label(class_obj):
    return class_obj.course.name if class_obj.course_id else class_obj.level.name


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
        class_obj = Class.objects.select_for_update().select_related('level', 'course').get(id=class_id, is_active=True)
    except (Class.DoesNotExist, ValueError, TypeError):
        raise ClassAssignmentError('The selected class does not exist or is no longer active.')

    if not _same_course(class_obj, student):
        raise ClassAssignmentError(
            f'{class_obj.class_name} runs {_course_label(class_obj)}, but the student is in a different course.'
        )

    taken = class_obj.enrolled_students.filter(is_active=True).count()
    if taken >= class_obj.max_students:
        raise ClassAssignmentError(f'{class_obj.class_name} is full ({class_obj.max_students} students).')

    student.assigned_class = class_obj
    return class_obj


# ============== HISTORY, TRANSFERS AND PROMOTION ==============

def record_history(student, change_type, user=None, from_class=None, to_class=None,
                   from_level='', to_level='', note='', transfer_request=None, from_course=None, to_course=None):
    from .models import StudentClassHistory
    return StudentClassHistory.objects.create(
        student=student, change_type=change_type, changed_by=user,
        from_class=from_class, to_class=to_class,
        from_level=from_level or '', to_level=to_level or '',
        from_course=from_course, to_course=to_course,
        note=note, transfer_request=transfer_request,
    )


def transfer_options(student):
    """Classes a student can transfer to: same course, active, not their current class."""
    prefs = student.application.schedule_preferences if student.application_id else None
    return [
        o for o in class_options(prefs)
        if o['id'] != student.assigned_class_id and (
            o['course_id'] == student.current_course_id if student.current_course_id
            else o['level'] == (student.current_level or '').upper()
        )
    ]


def create_transfer_request(student, to_class_id, reason, user):
    from .models import ClassTransferRequest
    if not student.assigned_class_id:
        raise ClassAssignmentError('This student has no class yet. Assign one from the Edit page instead.')
    if not (reason or '').strip():
        raise ClassAssignmentError('Please give a reason for the transfer.')
    if student.transfer_requests.filter(status='PENDING').exists():
        raise ClassAssignmentError('This student already has a pending transfer request.')
    try:
        to_class = Class.objects.select_related('level', 'course').get(id=to_class_id, is_active=True)
    except (Class.DoesNotExist, ValueError, TypeError):
        raise ClassAssignmentError('The selected class does not exist or is no longer active.')
    if to_class.id == student.assigned_class_id:
        raise ClassAssignmentError('The student is already in that class.')
    if not _same_course(to_class, student):
        raise ClassAssignmentError('Transfers must be to a class of the same course. Use promotion to change course.')
    return ClassTransferRequest.objects.create(
        student=student, from_class_id=student.assigned_class_id, to_class=to_class,
        reason=reason.strip(), requested_by=user,
    )


def approve_transfer(transfer, user, note=''):
    """Move the student. Must be called inside a transaction."""
    from django.utils import timezone
    from .models import ClassTransferRequest, Student

    transfer = ClassTransferRequest.objects.select_for_update().get(pk=transfer.pk)
    if transfer.status != 'PENDING':
        raise ClassAssignmentError(f'This request has already been {transfer.get_status_display().lower()}.')
    student = Student.objects.select_for_update().get(pk=transfer.student_id)
    if student.assigned_class_id != transfer.from_class_id:
        raise ClassAssignmentError(
            "The student's class has changed since this request was made. Reject it and raise a new request."
        )
    if not transfer.to_class_id:
        raise ClassAssignmentError('The target class no longer exists.')
    to_class = Class.objects.select_for_update().select_related('level', 'course').get(pk=transfer.to_class_id)
    if not to_class.is_active:
        raise ClassAssignmentError(f'{to_class.class_name} is no longer active.')
    if not _same_course(to_class, student):
        raise ClassAssignmentError(f'{to_class.class_name} does not run the student\'s current course.')
    if to_class.enrolled_students.filter(is_active=True).count() >= to_class.max_students:
        raise ClassAssignmentError(f'{to_class.class_name} is full ({to_class.max_students} students).')

    from_class = student.assigned_class
    student.assigned_class = to_class
    student.save()

    transfer.status = 'APPROVED'
    transfer.decided_by = user
    transfer.decided_at = timezone.now()
    transfer.decision_note = note or ''
    transfer.save()

    record_history(
        student, 'TRANSFERRED', user, from_class=from_class, to_class=to_class,
        from_level=student.current_level, to_level=student.current_level,
        from_course=student.current_course, to_course=student.current_course,
        note=transfer.reason, transfer_request=transfer,
    )
    return transfer


def reject_transfer(transfer, user, note='', status='REJECTED'):
    from django.utils import timezone
    from .models import ClassTransferRequest

    transfer = ClassTransferRequest.objects.select_for_update().get(pk=transfer.pk)
    if transfer.status != 'PENDING':
        raise ClassAssignmentError(f'This request has already been {transfer.get_status_display().lower()}.')
    transfer.status = status
    transfer.decided_by = user
    transfer.decided_at = timezone.now()
    transfer.decision_note = note or ''
    transfer.save()
    return transfer


def next_course(course):
    """The next active course in progression order (level order, then course order), or None."""
    return course.next_course() if course else None


def promote_students(from_class, student_ids, to_class_id, user, note=''):
    """
    Promote selected students of `from_class` into a class of the next course.
    Must be called inside a transaction. Returns the list of promoted students.
    """
    from .models import Student

    if not from_class.course_id:
        raise ClassAssignmentError(f'{from_class.class_name} has no course, so its students cannot be promoted.')
    target_course = next_course(from_class.course)
    if not target_course:
        raise ClassAssignmentError(f'{from_class.course.name} is the last course; there is no course to promote to.')
    try:
        to_class = Class.objects.select_for_update().select_related('level', 'course').get(id=to_class_id, is_active=True)
    except (Class.DoesNotExist, ValueError, TypeError):
        raise ClassAssignmentError('Please choose an active class to promote into.')
    if to_class.course_id != target_course.id:
        raise ClassAssignmentError(f'Students can only be promoted to {target_course.name} classes.')

    ids = {int(i) for i in student_ids if str(i).isdigit()}
    if not ids:
        raise ClassAssignmentError('Select at least one student to promote.')
    students = list(
        Student.objects.select_for_update().select_related('current_course').filter(
            id__in=ids, assigned_class=from_class, is_active=True
        )
    )
    if len(students) != len(ids):
        raise ClassAssignmentError('Some selected students are no longer active in this class. Reload and try again.')

    seats_left = to_class.max_students - to_class.enrolled_students.filter(is_active=True).count()
    if len(students) > seats_left:
        raise ClassAssignmentError(
            f'{to_class.class_name} has {max(seats_left, 0)} seat(s) left, but {len(students)} students were selected.'
        )

    for student in students:
        old_level, old_course = student.current_level, student.current_course
        student.assigned_class = to_class
        student.current_course = target_course
        student.save()  # current_level follows the course
        record_history(
            student, 'PROMOTED', user, from_class=from_class, to_class=to_class,
            from_level=old_level, to_level=student.current_level, note=note,
            from_course=old_course, to_course=target_course,
        )
    return students
