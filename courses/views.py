"""
Views for the courses app.

Handles YLE Levels, Classes, Units, Lessons, and Activities.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Count, Avg, Prefetch
from django.core.paginator import Paginator
from django.http import JsonResponse, Http404
from django.utils import timezone
from datetime import datetime, timedelta
import logging

from .models import YLELevel, Course, Class, Unit, Lesson, Activity
from teachers.models import Teacher
from students.models import Student

logger = logging.getLogger(__name__)


def _course_groups(include_inactive_ids=()):
    """Active CEFR levels with their active courses, for grouped course pickers."""
    groups = []
    for level in YLELevel.objects.filter(is_active=True).order_by('order', 'id'):
        courses = [
            c for c in level.courses.order_by('order', 'id')
            if c.is_active or c.id in include_inactive_ids
        ]
        if courses:
            groups.append({'level': level, 'courses': courses})
    return groups


# ============== YLE LEVEL VIEWS ==============

@login_required
def level_list_view(request):
    """CEFR levels are fixed; the level list now lives on the course list (courses grouped by level)."""
    return redirect('course_list')


@login_required
def yle_level_add_view(request):
    """CEFR levels are a fixed list (Pre A1 to B2); what staff add here are courses under a level."""
    messages.info(request, 'CEFR levels are fixed. Add a course under a level instead.')
    return redirect('course_add')


@login_required
@permission_required('courses.view_ylelevel', raise_exception=True)
def level_detail_view(request, level_id):
    """
    Detail view for a specific YLE level.
    Shows units, classes, and summary statistics for the level.
    """
    level = get_object_or_404(
        YLELevel.objects.prefetch_related(
            Prefetch('units', queryset=Unit.objects.filter(is_active=True).order_by('order')),
            Prefetch('classes', queryset=Class.objects.filter(is_active=True).select_related('teacher')),
        ),
        id=level_id,
        is_active=True
    )

    # Get statistics
    units = level.units.filter(is_active=True)
    classes = level.classes.filter(is_active=True)

    # Count lessons and activities
    total_lessons = Lesson.objects.filter(unit__level=level, is_active=True).count()
    total_activities = Activity.objects.filter(lesson__unit__level=level, is_active=True).count()

    # Get enrolled students count
    enrolled_students = Student.objects.filter(
        assigned_class__level=level,
        is_active=True
    ).count()

    context = {
        'level': level,
        'units': units,
        'classes': classes,
        'total_lessons': total_lessons,
        'total_activities': total_activities,
        'enrolled_students': enrolled_students,
    }

    return render(request, 'courses/level_detail.html', context)


# ============== CLASS VIEWS ==============

@login_required
@permission_required('courses.view_class', raise_exception=True)
def class_list_view(request):
    """
    List all classes with filtering by level, teacher, and status.
    """
    classes = Class.objects.select_related('level', 'course', 'teacher').all()

    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        classes = classes.filter(
            Q(class_name__icontains=search_query) |
            Q(class_code__icontains=search_query) |
            Q(teacher__full_name__icontains=search_query) |
            Q(room_number__icontains=search_query) |
            Q(location__icontains=search_query)
        )

    # Filter by level
    level_filter = request.GET.get('level', '')
    if level_filter:
        classes = classes.filter(level_id=level_filter)

    # Filter by teacher
    teacher_filter = request.GET.get('teacher', '')
    if teacher_filter:
        classes = classes.filter(teacher_id=teacher_filter)

    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        classes = classes.filter(is_active=True)
    elif status_filter == 'inactive':
        classes = classes.filter(is_active=False)

    # Sorting
    sort_by = request.GET.get('sort', 'level')
    if sort_by in ['level', 'class_name', 'start_date', 'teacher__full_name']:
        classes = classes.order_by(sort_by)

    # Pagination
    paginator = Paginator(classes, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get filter options
    levels = YLELevel.objects.filter(is_active=True).order_by('order', 'id')
    teachers = Teacher.objects.filter(is_active=True)

    context = {
        'page_obj': page_obj,
        'classes': page_obj.object_list,
        'search_query': search_query,
        'level_filter': level_filter,
        'teacher_filter': teacher_filter,
        'status_filter': status_filter,
        'sort_by': sort_by,
        'levels': levels,
        'teachers': teachers,
        'total_count': classes.count(),
    }

    return render(request, 'courses/class_list.html', context)


@login_required
@permission_required('courses.view_class', raise_exception=True)
def class_detail_view(request, class_id):
    """
    Detail view for a class showing enrolled students and schedule.
    """
    class_obj = get_object_or_404(
        Class.objects.select_related('level', 'teacher').prefetch_related(
            Prefetch(
                'enrolled_students',
                queryset=Student.objects.filter(is_active=True).order_by('full_name')
            )
        ),
        id=class_id
    )

    # Get enrolled students
    enrolled_students = class_obj.enrolled_students.filter(is_active=True)

    # Parse schedule for display
    schedule = class_obj.schedule or []

    # Calculate capacity info
    available_seats = class_obj.max_students - class_obj.current_enrollment
    capacity_percentage = (
        (class_obj.current_enrollment / class_obj.max_students * 100)
        if class_obj.max_students > 0 else 0
    )

    # Get units for this level (for curriculum overview)
    units = Unit.objects.filter(level=class_obj.level, is_active=True).order_by('order')

    context = {
        'class': class_obj,
        'enrolled_students': enrolled_students,
        'students': enrolled_students,  # Alias for template compatibility
        'schedule': schedule,
        'available_seats': available_seats,
        'capacity_percentage': round(capacity_percentage),
        'units': units,
    }

    return render(request, 'courses/class_detail.html', context)


def _parse_date(value):
    """Parse 'YYYY-MM-DD' (or a date); empty/None gives None."""
    if not value:
        return None
    if hasattr(value, 'year'):
        return value
    return datetime.strptime(value, '%Y-%m-%d').date()


def _date_ranges_overlap(start_a, end_a, start_b, end_b):
    """Date ranges overlap; None on either side is treated as open-ended."""
    return (end_a is None or start_b is None or end_a >= start_b) and \
           (start_a is None or end_b is None or start_a <= end_b)


def check_teacher_schedule_overlap(teacher_id, day, from_time, to_time, start_date, end_date, exclude_class_id=None):
    """
    Check if a teacher has overlapping schedules with the proposed schedule.

    Args:
        teacher_id: ID of the teacher to check
        day: Day of the week (e.g., 'Monday')
        from_time: Start time (e.g., '09:00')
        to_time: End time (e.g., '10:30')
        start_date: Class start date
        end_date: Class end date
        exclude_class_id: Optional class ID to exclude (for editing)

    Returns:
        tuple: (has_overlap: bool, overlapping_class: Class or None)
    """
    if not teacher_id:
        return False, None

    # Get all active classes that have schedules with this teacher
    classes_query = Class.objects.filter(is_active=True)
    if exclude_class_id:
        classes_query = classes_query.exclude(id=exclude_class_id)

    new_start = _parse_date(start_date)
    new_end = _parse_date(end_date)

    for cls in classes_query:
        # Check if date ranges overlap (a missing date means open-ended)
        if _date_ranges_overlap(cls.start_date, cls.end_date, new_start, new_end):
            # Date ranges overlap, check schedule
            for sched in cls.schedule or []:
                # Check if this schedule has the same teacher
                if str(sched.get('teacher_id')) == str(teacher_id) and sched.get('day') == day:
                    sched_from = sched.get('from_time')
                    sched_to = sched.get('to_time')

                    # Check time overlap: NOT (new_end <= existing_start OR new_start >= existing_end)
                    if not (to_time <= sched_from or from_time >= sched_to):
                        return True, cls

    return False, None


@login_required
@permission_required('courses.add_class', raise_exception=True)
def class_add_view(request):
    """
    Add a new class (staff only).
    Each schedule slot can have its own teacher assignment.
    Validates that teachers do not have overlapping schedules.
    """
    if request.method == 'POST':
        # Get form data
        level_id = request.POST.get('level')
        class_name = request.POST.get('class_name')
        class_code = request.POST.get('class_code')
        max_students = request.POST.get('max_students', 25)
        room_number = request.POST.get('room_number', '')
        location = request.POST.get('location', '')
        course_id = request.POST.get('course', '')

        # Validate required fields (name the missing ones so the user knows what to fix)
        required = {'Class name': class_name, 'Class code': class_code, 'Course': course_id, 'Location': location}
        missing = [label for label, value in required.items() if not (value or '').strip()]
        if missing:
            logger.warning('Class add rejected, missing fields: %s', missing)
            messages.error(request, f'Please fill in: {", ".join(missing)}.')
            return redirect('class_add')

        if location not in dict(Class.LOCATION_CHOICES):
            messages.error(request, 'Please select a valid location.')
            return redirect('class_add')

        # Check for duplicate class code
        if Class.objects.filter(class_code__iexact=class_code).exists():
            messages.error(request, f'Class code "{class_code}" already exists.')
            return redirect('class_add')

        # Get related objects (the class's CEFR level follows its course)
        course = Course.objects.select_related('level').filter(id=course_id, is_active=True).first() if str(course_id).isdigit() else None
        if not course:
            messages.error(request, 'Please select an active course.')
            return redirect('class_add')
        level = course.level

        # Parse schedule from form (now includes per-schedule teacher)
        schedule = []
        schedule_days = request.POST.getlist('schedule_day[]')
        schedule_from_times = request.POST.getlist('schedule_from_time[]')
        schedule_to_times = request.POST.getlist('schedule_to_time[]')
        schedule_teachers = request.POST.getlist('schedule_teacher[]')

        # Build schedule entries and validate
        for i in range(len(schedule_days)):
            if schedule_days[i] and i < len(schedule_from_times) and i < len(schedule_to_times):
                from_time = schedule_from_times[i]
                to_time = schedule_to_times[i]
                teacher_id = schedule_teachers[i] if i < len(schedule_teachers) else ''

                # Validate time range
                if from_time and to_time:
                    if from_time >= to_time:
                        messages.error(request, f'Invalid time range for {schedule_days[i]}: End time must be after start time.')
                        return redirect('class_add')

                    # Check for teacher schedule overlap
                    if teacher_id:
                        has_overlap, overlapping_class = check_teacher_schedule_overlap(
                            teacher_id, schedule_days[i], from_time, to_time, None, None
                        )
                        if has_overlap:
                            teacher = Teacher.objects.get(id=teacher_id)
                            messages.error(
                                request,
                                f'Teacher "{teacher.full_name}" has a schedule conflict on {schedule_days[i]} '
                                f'({from_time}-{to_time}) with class "{overlapping_class.class_name}".'
                            )
                            return redirect('class_add')

                    schedule_entry = {
                        'day': schedule_days[i],
                        'from_time': from_time,
                        'to_time': to_time
                    }
                    if teacher_id:
                        schedule_entry['teacher_id'] = int(teacher_id)
                        # Also store teacher name for display purposes
                        teacher = Teacher.objects.get(id=teacher_id)
                        schedule_entry['teacher_name'] = teacher.full_name

                    schedule.append(schedule_entry)

        # Create class (teacher field no longer used - teachers are per-schedule)
        new_class = Class.objects.create(
            course=course,
            level=level,
            class_name=class_name,
            class_code=class_code.upper(),
            schedule=schedule,
            max_students=int(max_students),
            location=location,
            room_number=room_number,
            is_active=True,
        )

        messages.success(request, f'Class "{new_class.class_name}" created successfully!')
        return redirect('class_detail', class_id=new_class.id)

    # GET request - show form
    teachers = Teacher.objects.filter(is_active=True)

    context = {
        'course_groups': _course_groups(),
        'selected_course': request.GET.get('course', ''),
        'teachers': teachers,
        'locations': Class.LOCATION_CHOICES,
    }

    return render(request, 'courses/class_add.html', context)


@login_required
@permission_required('courses.change_class', raise_exception=True)
def class_edit_view(request, class_id):
    """
    Edit class details (staff only).
    Each schedule slot can have its own teacher assignment.
    Validates that teachers do not have overlapping schedules.
    """
    class_obj = get_object_or_404(Class, id=class_id)

    if request.method == 'POST':
        # Update fields
        class_obj.class_name = request.POST.get('class_name', class_obj.class_name)

        # Handle class code change
        new_class_code = request.POST.get('class_code', class_obj.class_code).upper()
        if new_class_code != class_obj.class_code:
            if Class.objects.filter(class_code=new_class_code).exclude(id=class_id).exists():
                messages.error(request, f'Class code "{new_class_code}" already exists.')
                return redirect('class_edit', class_id=class_id)
            class_obj.class_code = new_class_code

        # Update course (the class's CEFR level follows it). A class with students keeps its course:
        # students move between courses through transfers and promotion.
        course_id = request.POST.get('course')
        if course_id and str(course_id) != str(class_obj.course_id):
            new_course = Course.objects.select_related('level').filter(id=course_id, is_active=True).first() if str(course_id).isdigit() else None
            if not new_course:
                messages.error(request, 'Please select an active course.')
                return redirect('class_edit', class_id=class_id)
            if class_obj.enrolled_students.filter(is_active=True).exists():
                messages.error(request, 'This class has students, so its course cannot be changed. Use promotion or transfers to move students.')
                return redirect('class_edit', class_id=class_id)
            class_obj.course = new_course
            class_obj.level = new_course.level

        # Update other fields
        class_obj.max_students = int(request.POST.get('max_students', class_obj.max_students))
        class_obj.room_number = request.POST.get('room_number', class_obj.room_number)
        class_obj.is_active = request.POST.get('is_active') == 'on'

        # Location is required
        location = request.POST.get('location', '')
        if location not in dict(Class.LOCATION_CHOICES):
            messages.error(request, 'Please select the class location.')
            return redirect('class_edit', class_id=class_id)
        class_obj.location = location


        # Parse schedule from form (now includes per-schedule teacher)
        schedule = []
        schedule_days = request.POST.getlist('schedule_day[]')
        schedule_from_times = request.POST.getlist('schedule_from_time[]')
        schedule_to_times = request.POST.getlist('schedule_to_time[]')
        schedule_teachers = request.POST.getlist('schedule_teacher[]')

        for i in range(len(schedule_days)):
            if schedule_days[i] and i < len(schedule_from_times) and i < len(schedule_to_times):
                from_time = schedule_from_times[i]
                to_time = schedule_to_times[i]
                teacher_id = schedule_teachers[i] if i < len(schedule_teachers) else ''

                # Validate time range
                if from_time and to_time:
                    if from_time >= to_time:
                        messages.error(request, f'Invalid time range for {schedule_days[i]}: End time must be after start time.')
                        return redirect('class_edit', class_id=class_id)

                    # Check for teacher schedule overlap (exclude current class)
                    if teacher_id:
                        has_overlap, overlapping_class = check_teacher_schedule_overlap(
                            teacher_id, schedule_days[i], from_time, to_time,
                            class_obj.start_date,
                            class_obj.end_date,
                            exclude_class_id=class_id
                        )
                        if has_overlap:
                            teacher = Teacher.objects.get(id=teacher_id)
                            messages.error(
                                request,
                                f'Teacher "{teacher.full_name}" has a schedule conflict on {schedule_days[i]} '
                                f'({from_time}-{to_time}) with class "{overlapping_class.class_name}".'
                            )
                            return redirect('class_edit', class_id=class_id)

                    schedule_entry = {
                        'day': schedule_days[i],
                        'from_time': from_time,
                        'to_time': to_time
                    }
                    if teacher_id:
                        schedule_entry['teacher_id'] = int(teacher_id)
                        # Also store teacher name for display purposes
                        teacher = Teacher.objects.get(id=teacher_id)
                        schedule_entry['teacher_name'] = teacher.full_name

                    schedule.append(schedule_entry)

        class_obj.schedule = schedule

        class_obj.save(update_fields=['class_name', 'class_code', 'course', 'level', 'max_students',
                                       'location', 'room_number', 'is_active', 'schedule'])
        messages.success(request, f'Class "{class_obj.class_name}" updated successfully!')
        return redirect('class_detail', class_id=class_obj.id)

    # GET request - show form
    teachers = Teacher.objects.filter(is_active=True)

    context = {
        'class': class_obj,
        'course_groups': _course_groups(),
        'selected_course': str(class_obj.course_id or ''),
        'course_locked': class_obj.enrolled_students.filter(is_active=True).exists(),
        'teachers': teachers,
        'locations': Class.LOCATION_CHOICES,
    }

    return render(request, 'courses/class_form.html', context)


# ============== UNIT VIEWS ==============

@login_required
@permission_required('courses.add_unit', raise_exception=True)
def unit_add_view(request):
    """
    Add a new unit to a YLE level (staff only).
    Units are learning modules that contain lessons.
    """
    if request.method == 'POST':
        # Get form data
        level_id = request.POST.get('level')
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        order = request.POST.get('order', '0')
        requires_completion_of_id = request.POST.get('requires_completion_of', '')
        is_active = request.POST.get('is_active') == 'on'

        # Validate required fields
        if not all([level_id, title, description]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('unit_add')

        # Get the level
        level = get_object_or_404(YLELevel, id=level_id)

        try:
            unit_order = int(order)

            # Check if order already exists for this level
            if Unit.objects.filter(level=level, order=unit_order).exists():
                messages.error(request, f'A unit with order {unit_order} already exists for this level. Please choose a different order.')
                return redirect('unit_add')

            # Get prerequisite unit if specified
            requires_completion_of = None
            if requires_completion_of_id:
                requires_completion_of = get_object_or_404(Unit, id=requires_completion_of_id)

            # Create the unit
            new_unit = Unit.objects.create(
                level=level,
                title=title,
                description=description,
                order=unit_order,
                requires_completion_of=requires_completion_of,
                is_active=is_active,
            )

            # Handle thumbnail upload
            if 'thumbnail' in request.FILES:
                new_unit.thumbnail = request.FILES['thumbnail']
                new_unit.save(update_fields=['thumbnail'])

            messages.success(request, f'Unit "{new_unit.title}" created successfully!')
            return redirect('unit_detail', unit_id=new_unit.id)

        except ValueError as e:
            messages.error(request, f'Invalid data provided: {str(e)}')
            return redirect('unit_add')
        except Exception as e:
            messages.error(request, f'An error occurred while creating the unit: {str(e)}')
            return redirect('unit_add')

    # GET request - show form
    levels = YLELevel.objects.filter(is_active=True).order_by('order')

    # Get level_id from query parameter if provided (for pre-selection)
    preselected_level_id = request.GET.get('level', '')
    preselected_level = None
    if preselected_level_id:
        try:
            preselected_level = YLELevel.objects.get(id=preselected_level_id)
        except YLELevel.DoesNotExist:
            pass

    # Get all units for prerequisite selection (grouped by level)
    all_units = Unit.objects.filter(is_active=True).select_related('level').order_by('level__order', 'order')

    # Get suggested order for preselected level
    suggested_order = 0
    if preselected_level:
        max_order = Unit.objects.filter(level=preselected_level).order_by('-order').first()
        suggested_order = (max_order.order + 1) if max_order else 0

    context = {
        'levels': levels,
        'preselected_level': preselected_level,
        'preselected_level_id': preselected_level_id,
        'all_units': all_units,
        'suggested_order': suggested_order,
    }

    return render(request, 'courses/unit_add.html', context)


@login_required
@permission_required('courses.view_unit', raise_exception=True)
def unit_list_view(request, level_id):
    """
    List all units for a specific YLE level.
    """
    level = get_object_or_404(YLELevel, id=level_id, is_active=True)

    units = Unit.objects.filter(
        level=level,
        is_active=True
    ).annotate(
        lesson_count=Count('lessons', filter=Q(lessons__is_active=True))
    ).order_by('order')

    all_levels = YLELevel.objects.filter(is_active=True).annotate(
        unit_count=Count('units', filter=Q(units__is_active=True))
    ).order_by('order', 'id')

    context = {
        'level': level,
        'units': units,
        'level_counts': [{'level': l, 'count': l.unit_count} for l in all_levels],
    }

    return render(request, 'courses/unit_list.html', context)


@login_required
@permission_required('courses.view_unit', raise_exception=True)
def unit_detail_view(request, unit_id):
    """
    Detail view for a unit showing lessons.
    """
    unit = get_object_or_404(
        Unit.objects.select_related('level', 'requires_completion_of').prefetch_related(
            Prefetch(
                'lessons',
                queryset=Lesson.objects.filter(is_active=True).order_by('order')
            )
        ),
        id=unit_id,
        is_active=True
    )

    # Get lessons
    lessons = unit.lessons.filter(is_active=True).order_by('order')

    # Calculate total duration
    total_duration = sum(lesson.duration_minutes for lesson in lessons)

    # Check if user is a student and get progress
    student_progress = None
    if hasattr(request.user, 'student'):
        from progress.models import UnitProgress
        student_progress = UnitProgress.objects.filter(
            student=request.user.student,
            unit=unit
        ).first()

    context = {
        'unit': unit,
        'lessons': lessons,
        'total_duration': total_duration,
        'student_progress': student_progress,
    }

    return render(request, 'courses/unit_detail.html', context)


# ============== LESSON VIEWS ==============

@login_required
@permission_required('courses.view_lesson', raise_exception=True)
def lesson_list_view(request, unit_id):
    """
    List all lessons in a unit.
    """
    unit = get_object_or_404(
        Unit.objects.select_related('level'),
        id=unit_id,
        is_active=True
    )

    lessons = Lesson.objects.filter(
        unit=unit,
        is_active=True
    ).annotate(
        activity_count=Count('activities', filter=Q(activities__is_active=True))
    ).order_by('order')

    # Check if user is a student and get lesson progress
    if hasattr(request.user, 'student'):
        from progress.models import LessonProgress
        for lesson in lessons:
            progress = LessonProgress.objects.filter(
                student=request.user.student,
                lesson=lesson
            ).first()
            lesson.user_progress = progress

    context = {
        'unit': unit,
        'lessons': lessons,
    }

    return render(request, 'courses/lesson_list.html', context)


@login_required
@permission_required('courses.view_lesson', raise_exception=True)
def lesson_detail_view(request, lesson_id):
    """
    Detail view for a lesson with activities.
    """
    lesson = get_object_or_404(
        Lesson.objects.select_related('unit__level').prefetch_related(
            Prefetch(
                'activities',
                queryset=Activity.objects.filter(is_active=True).order_by('order')
            )
        ),
        id=lesson_id,
        is_active=True
    )

    # Get activities
    activities = lesson.activities.filter(is_active=True).order_by('order')

    # Get skills covered
    skills_covered = []
    if lesson.skill_listening:
        skills_covered.append('Listening')
    if lesson.skill_reading:
        skills_covered.append('Reading')
    if lesson.skill_writing:
        skills_covered.append('Writing')
    if lesson.skill_speaking:
        skills_covered.append('Speaking')

    # Check if user is a student and get progress
    student_progress = None
    activity_progress = {}
    if hasattr(request.user, 'student'):
        from progress.models import LessonProgress, ActivityAttempt
        student_progress = LessonProgress.objects.filter(
            student=request.user.student,
            lesson=lesson
        ).first()

        # Get activity attempts
        for activity in activities:
            attempts = ActivityAttempt.objects.filter(
                student=request.user.student,
                activity=activity
            ).order_by('-created_at')
            activity_progress[activity.id] = {
                'attempts': attempts.count(),
                'best_score': attempts.order_by('-percentage').first() if attempts else None,
                'completed': attempts.filter(is_completed=True).exists()
            }

    # Get next and previous lessons
    next_lesson = Lesson.objects.filter(
        unit=lesson.unit,
        order__gt=lesson.order,
        is_active=True
    ).order_by('order').first()

    prev_lesson = Lesson.objects.filter(
        unit=lesson.unit,
        order__lt=lesson.order,
        is_active=True
    ).order_by('-order').first()

    context = {
        'lesson': lesson,
        'activities': activities,
        'skills_covered': skills_covered,
        'student_progress': student_progress,
        'activity_progress': activity_progress,
        'next_lesson': next_lesson,
        'prev_lesson': prev_lesson,
    }

    return render(request, 'courses/lesson_detail.html', context)


# ============== AJAX/API ENDPOINTS ==============

@login_required
@permission_required('courses.view_class', raise_exception=True)
def api_class_students(request, class_id):
    """
    API endpoint to get students enrolled in a class.
    """
    class_obj = get_object_or_404(Class, id=class_id)
    students = class_obj.enrolled_students.filter(is_active=True).values(
        'id', 'admission_number', 'full_name', 'current_level'
    )

    return JsonResponse({'students': list(students)})


@login_required
@permission_required('courses.view_unit', raise_exception=True)
def api_level_units(request, level_id):
    """
    API endpoint to get units for a level.
    """
    level = get_object_or_404(YLELevel, id=level_id)
    units = level.units.filter(is_active=True).values(
        'id', 'title', 'order'
    )

    return JsonResponse({'units': list(units)})


# ============== COURSE VIEWS ==============
# Courses (e.g. Pre1, Pre2, Pre3) belong to a CEFR level. Classes run a course and
# students progress course by course.

def _course_form_data(request, course=None):
    data = {
        'name': request.POST.get('name', '').strip(),
        'code': request.POST.get('code', '').strip().upper(),
        'level_id': request.POST.get('level', ''),
        'order': request.POST.get('order', '').strip(),
        'description': request.POST.get('description', '').strip(),
        'age_range_min': request.POST.get('age_range_min', '').strip(),
        'age_range_max': request.POST.get('age_range_max', '').strip(),
        'is_active': request.POST.get('is_active') == 'on',
    }
    errors = []
    if not data['name']:
        errors.append('Course name is required.')
    if not data['code']:
        errors.append('Course code is required.')
    elif Course.objects.filter(code__iexact=data['code']).exclude(pk=getattr(course, 'pk', None)).exists():
        errors.append(f'Course code "{data["code"]}" is already used.')
    level = YLELevel.objects.filter(pk=data['level_id']).first() if str(data['level_id']).isdigit() else None
    if not level:
        errors.append('Please choose the CEFR level.')
    for field, label in (('order', 'Order'), ('age_range_min', 'Minimum age'), ('age_range_max', 'Maximum age')):
        value = data[field]
        if value and not value.lstrip('-').isdigit():
            errors.append(f'{label} must be a whole number.')
    if (data['age_range_min'].isdigit() and data['age_range_max'].isdigit()
            and int(data['age_range_min']) > int(data['age_range_max'])):
        errors.append('Minimum age cannot be greater than maximum age.')
    return data, level, errors


def _apply_course_data(course, data, level):
    course.name = data['name']
    course.code = data['code']
    course.level = level
    course.order = int(data['order']) if data['order'] else 0
    course.description = data['description']
    course.age_range_min = int(data['age_range_min']) if data['age_range_min'] else None
    course.age_range_max = int(data['age_range_max']) if data['age_range_max'] else None
    course.is_active = data['is_active']


@login_required
@permission_required('courses.view_course', raise_exception=True)
def course_list_view(request):
    """Courses grouped by CEFR level, with class and student counts per course and teacher counts per level."""
    show_inactive = request.GET.get('inactive') == '1'
    courses = Course.objects.select_related('level').annotate(
        class_count=Count('classes', filter=Q(classes__is_active=True), distinct=True),
        student_count=Count('students', filter=Q(students__is_active=True), distinct=True),
        all_class_count=Count('classes', distinct=True),
        all_student_count=Count('students', distinct=True),
    ).order_by('level__order', 'level__id', 'order', 'id')
    if not show_inactive:
        courses = courses.filter(is_active=True)

    by_level = {}
    for course in courses:
        by_level.setdefault(course.level_id, []).append(course)
    levels = YLELevel.objects.filter(is_active=True).annotate(
        teacher_count=Count('teachers', filter=Q(teachers__is_active=True), distinct=True)
    ).order_by('order', 'id')
    groups = [{'level': level, 'courses': by_level.get(level.id, [])} for level in levels]

    return render(request, 'courses/course_list.html', {
        'groups': groups,
        'show_inactive': show_inactive,
        'total_courses': sum(len(g['courses']) for g in groups),
        'total_classes': sum(c.class_count for g in groups for c in g['courses']),
        'total_students': sum(c.student_count for g in groups for c in g['courses']),
    })


@login_required
@permission_required('courses.add_course', raise_exception=True)
def course_add_view(request):
    levels = YLELevel.objects.filter(is_active=True).order_by('order', 'id')
    data = {'level_id': request.GET.get('level', ''), 'is_active': True, 'order': ''}

    if request.method == 'POST':
        data, level, errors = _course_form_data(request)
        if not errors:
            course = Course()
            _apply_course_data(course, data, level)
            course.save()
            messages.success(request, f'Course "{course.name}" created under {level.name}.')
            return redirect('course_detail', course_id=course.id)
        for error in errors:
            messages.error(request, error)

    if not data.get('order') and str(data.get('level_id', '')).isdigit():
        last = Course.objects.filter(level_id=int(data['level_id'])).order_by('-order').first()
        data['order'] = (last.order + 1) if last else 1

    return render(request, 'courses/course_form.html', {'levels': levels, 'data': data, 'course': None})


@login_required
@permission_required('courses.change_course', raise_exception=True)
def course_edit_view(request, course_id):
    course = get_object_or_404(Course.objects.select_related('level'), id=course_id)
    levels = YLELevel.objects.filter(is_active=True).order_by('order', 'id')
    data = {
        'name': course.name, 'code': course.code, 'level_id': course.level_id, 'order': course.order,
        'description': course.description, 'age_range_min': course.age_range_min or '',
        'age_range_max': course.age_range_max or '', 'is_active': course.is_active,
    }

    if request.method == 'POST':
        data, level, errors = _course_form_data(request, course)
        if not errors:
            level_changed = course.level_id != level.id
            _apply_course_data(course, data, level)
            with transaction.atomic():
                course.save()
                if level_changed:
                    # Keep classes and students of this course on the course's CEFR level
                    Class.objects.filter(course=course).update(level=level)
                    Student.objects.filter(current_course=course).update(current_level=level.short_code)
            messages.success(request, f'Course "{course.name}" updated.')
            return redirect('course_detail', course_id=course.id)
        for error in errors:
            messages.error(request, error)

    return render(request, 'courses/course_form.html', {'levels': levels, 'data': data, 'course': course})


def _back_to_courses(request):
    """Return to the page the form was posted from (course list with its filters), else the course list."""
    from django.utils.http import url_has_allowed_host_and_scheme
    next_url = request.POST.get('next', '')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()},
                                                    require_https=request.is_secure()):
        return redirect(next_url)
    return redirect('course_list')


def course_delete_blockers(course):
    """Reasons a course can't be deleted (it still has classes, students or class history)."""
    from students.models import StudentClassHistory
    blockers = []
    class_count = course.classes.count()
    if class_count:
        blockers.append(f'{class_count} class{"es" if class_count != 1 else ""}')
    student_count = course.students.count()
    if student_count:
        blockers.append(f'{student_count} student{"s" if student_count != 1 else ""}')
    if StudentClassHistory.objects.filter(Q(from_course=course) | Q(to_course=course)).exists():
        blockers.append('class history records')
    return blockers


@login_required
@permission_required('courses.change_course', raise_exception=True)
def course_rename_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if request.method != 'POST':
        return redirect('course_edit', course_id=course.id)
    name = request.POST.get('name', '').strip()
    max_length = Course._meta.get_field('name').max_length
    if not name:
        messages.error(request, 'Course name is required.')
    elif len(name) > max_length:
        messages.error(request, f'Course name can be at most {max_length} characters.')
    elif name == course.name:
        messages.info(request, 'The name is unchanged.')
    else:
        old_name = course.name
        course.name = name
        course.save(update_fields=['name', 'updated_at'])
        messages.success(request, f'Course "{old_name}" renamed to "{name}".')
    return _back_to_courses(request)


@login_required
@permission_required('courses.delete_course', raise_exception=True)
def course_delete_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if request.method != 'POST':
        return redirect('course_detail', course_id=course.id)
    blockers = course_delete_blockers(course)
    if blockers:
        messages.error(
            request,
            f'"{course.name}" can\'t be deleted because it has {", ".join(blockers)}. '
            f'Mark it inactive instead (Edit → Active).'
        )
        return _back_to_courses(request)
    name = course.name
    course.delete()
    messages.success(request, f'Course "{name}" deleted.')
    return _back_to_courses(request)


@login_required
@permission_required('courses.view_course', raise_exception=True)
def course_detail_view(request, course_id):
    course = get_object_or_404(Course.objects.select_related('level'), id=course_id)
    classes = course.classes.select_related('level').annotate(
        active_students=Count('enrolled_students', filter=Q(enrolled_students__is_active=True))
    ).order_by('-is_active', 'class_name')
    students = course.students.filter(is_active=True).select_related('assigned_class').order_by('full_name')
    return render(request, 'courses/course_detail.html', {
        'course': course,
        'classes': classes,
        'students': students,
        'teachers': course.level.teachers.filter(is_active=True).order_by('full_name'),
        'next_course': course.next_course(),
    })
