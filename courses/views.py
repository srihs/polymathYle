"""
Views for the courses app.

Handles YLE Levels, Classes, Units, Lessons, Activities, and Assessments.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Q, Count, Avg, Prefetch
from django.core.paginator import Paginator
from django.http import JsonResponse, Http404
from django.utils import timezone
from datetime import datetime, timedelta

from .models import YLELevel, Class, Unit, Lesson, Activity, Assessment
from teachers.models import Teacher
from students.models import Student


# ============== YLE LEVEL VIEWS ==============

@login_required
def level_list_view(request):
    """
    List all YLE levels (Starters, Movers, Flyers).
    Shows active levels with counts of units and classes.
    """
    levels = YLELevel.objects.filter(is_active=True).annotate(
        unit_count=Count('units', filter=Q(units__is_active=True)),
        class_count=Count('classes', filter=Q(classes__is_active=True)),
        student_count=Count(
            'classes__enrolled_students',
            filter=Q(classes__is_active=True, classes__enrolled_students__is_active=True)
        )
    ).order_by('order')

    context = {
        'levels': levels,
    }

    return render(request, 'courses/level_list.html', context)


@login_required
@permission_required('courses.add_ylelevel', raise_exception=True)
def yle_level_add_view(request):
    """
    Add a new YLE level (admin/staff only).
    """
    if request.method == 'POST':
        # Get form data
        name = request.POST.get('name', '').strip()
        short_code = request.POST.get('short_code', '').strip().upper()
        cefr_level = request.POST.get('cefr_level', '').strip()
        description = request.POST.get('description', '').strip()
        age_range_min = request.POST.get('age_range_min')
        age_range_max = request.POST.get('age_range_max')
        duration_minutes = request.POST.get('duration_minutes')
        order = request.POST.get('order', '0')
        icon = request.POST.get('icon', 'ri-medal-line').strip()
        color_theme = request.POST.get('color_theme', '#660066').strip()
        is_active = request.POST.get('is_active') == 'on'

        # Validate required fields
        if not all([name, short_code, cefr_level, description, age_range_min, age_range_max, duration_minutes, icon, color_theme]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('yle_level_add')

        # Check for duplicate short code
        if YLELevel.objects.filter(short_code=short_code).exists():
            messages.error(request, f'A YLE level with short code "{short_code}" already exists.')
            return redirect('yle_level_add')

        try:
            # Convert numeric fields to integers
            age_min = int(age_range_min)
            age_max = int(age_range_max)
            duration = int(duration_minutes)
            level_order = int(order)

            # Validate age ranges
            if age_min < 4 or age_min > 18:
                messages.error(request, 'Minimum age must be between 4 and 18 years.')
                return redirect('yle_level_add')

            if age_max < 4 or age_max > 18:
                messages.error(request, 'Maximum age must be between 4 and 18 years.')
                return redirect('yle_level_add')

            if age_min >= age_max:
                messages.error(request, 'Maximum age must be greater than minimum age.')
                return redirect('yle_level_add')

            # Validate duration
            if duration < 30 or duration > 300:
                messages.error(request, 'Exam duration must be between 30 and 300 minutes.')
                return redirect('yle_level_add')

            # Create YLE Level
            new_level = YLELevel.objects.create(
                name=name,
                short_code=short_code,
                cefr_level=cefr_level,
                description=description,
                age_range_min=age_min,
                age_range_max=age_max,
                duration_minutes=duration,
                order=level_order,
                icon=icon,
                color_theme=color_theme,
                is_active=is_active,
            )

            messages.success(request, f'YLE Level "{new_level.name}" created successfully!')
            return redirect('level_detail', level_id=new_level.id)

        except ValueError as e:
            messages.error(request, f'Invalid data provided: {str(e)}')
            return redirect('yle_level_add')
        except Exception as e:
            messages.error(request, f'An error occurred while creating the level: {str(e)}')
            return redirect('yle_level_add')

    # GET request - show form
    # Get existing levels count for order suggestion
    levels_count = YLELevel.objects.count()

    context = {
        'levels_count': levels_count,
    }

    return render(request, 'courses/yle_level_add.html', context)


@login_required
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
def class_list_view(request):
    """
    List all classes with filtering by level, teacher, and status.
    """
    classes = Class.objects.select_related('level', 'teacher').all()

    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        classes = classes.filter(
            Q(class_name__icontains=search_query) |
            Q(class_code__icontains=search_query) |
            Q(teacher__full_name__icontains=search_query) |
            Q(room_number__icontains=search_query)
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
    levels = YLELevel.objects.filter(is_active=True)
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
        'class_obj': class_obj,
        'enrolled_students': enrolled_students,
        'schedule': schedule,
        'available_seats': available_seats,
        'capacity_percentage': round(capacity_percentage),
        'units': units,
    }

    return render(request, 'courses/class_detail.html', context)


@login_required
@staff_member_required
def class_add_view(request):
    """
    Add a new class (staff only).
    """
    if request.method == 'POST':
        # Get form data
        level_id = request.POST.get('level')
        class_name = request.POST.get('class_name')
        class_code = request.POST.get('class_code')
        teacher_id = request.POST.get('teacher')
        max_students = request.POST.get('max_students', 25)
        room_number = request.POST.get('room_number', '')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        # Validate required fields
        if not all([level_id, class_name, class_code, start_date, end_date]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('class_add')

        # Check for duplicate class code
        if Class.objects.filter(class_code=class_code).exists():
            messages.error(request, f'Class code "{class_code}" already exists.')
            return redirect('class_add')

        # Get related objects
        level = get_object_or_404(YLELevel, id=level_id)
        teacher = None
        if teacher_id:
            teacher = get_object_or_404(Teacher, id=teacher_id)

        # Parse schedule from form
        schedule = []
        schedule_days = request.POST.getlist('schedule_day')
        schedule_times = request.POST.getlist('schedule_time')
        schedule_durations = request.POST.getlist('schedule_duration')

        for i in range(len(schedule_days)):
            if schedule_days[i] and schedule_times[i]:
                schedule.append({
                    'day': schedule_days[i],
                    'time': schedule_times[i],
                    'duration_minutes': int(schedule_durations[i]) if i < len(schedule_durations) and schedule_durations[i] else 90
                })

        # Create class
        new_class = Class.objects.create(
            level=level,
            class_name=class_name,
            class_code=class_code.upper(),
            teacher=teacher,
            schedule=schedule,
            max_students=int(max_students),
            room_number=room_number,
            start_date=start_date,
            end_date=end_date,
            is_active=True,
        )

        messages.success(request, f'Class "{new_class.class_name}" created successfully!')
        return redirect('class_detail', class_id=new_class.id)

    # GET request - show form
    levels = YLELevel.objects.filter(is_active=True)
    teachers = Teacher.objects.filter(is_active=True)

    context = {
        'levels': levels,
        'teachers': teachers,
    }

    return render(request, 'courses/class_add.html', context)


@login_required
@staff_member_required
def class_edit_view(request, class_id):
    """
    Edit class details (staff only).
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

        # Update level
        level_id = request.POST.get('level')
        if level_id:
            class_obj.level = get_object_or_404(YLELevel, id=level_id)

        # Update teacher
        teacher_id = request.POST.get('teacher')
        if teacher_id:
            class_obj.teacher = get_object_or_404(Teacher, id=teacher_id)
        else:
            class_obj.teacher = None

        # Update other fields
        class_obj.max_students = int(request.POST.get('max_students', class_obj.max_students))
        class_obj.room_number = request.POST.get('room_number', class_obj.room_number)
        class_obj.is_active = request.POST.get('is_active') == 'on'

        # Update dates
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        if start_date:
            class_obj.start_date = start_date
        if end_date:
            class_obj.end_date = end_date

        # Parse schedule from form
        schedule = []
        schedule_days = request.POST.getlist('schedule_day')
        schedule_times = request.POST.getlist('schedule_time')
        schedule_durations = request.POST.getlist('schedule_duration')

        for i in range(len(schedule_days)):
            if schedule_days[i] and schedule_times[i]:
                schedule.append({
                    'day': schedule_days[i],
                    'time': schedule_times[i],
                    'duration_minutes': int(schedule_durations[i]) if i < len(schedule_durations) and schedule_durations[i] else 90
                })

        class_obj.schedule = schedule

        class_obj.save()
        messages.success(request, f'Class "{class_obj.class_name}" updated successfully!')
        return redirect('class_detail', class_id=class_obj.id)

    # GET request - show form
    levels = YLELevel.objects.filter(is_active=True)
    teachers = Teacher.objects.filter(is_active=True)

    context = {
        'class_obj': class_obj,
        'levels': levels,
        'teachers': teachers,
    }

    return render(request, 'courses/class_edit.html', context)


# ============== UNIT VIEWS ==============

@login_required
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

    context = {
        'level': level,
        'units': units,
    }

    return render(request, 'courses/unit_list.html', context)


@login_required
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

    # Get assessments for this unit
    assessments = Assessment.objects.filter(unit=unit, is_active=True)

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
        'assessments': assessments,
        'total_duration': total_duration,
        'student_progress': student_progress,
    }

    return render(request, 'courses/unit_detail.html', context)


# ============== LESSON VIEWS ==============

@login_required
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


# ============== ASSESSMENT VIEWS ==============

@login_required
def assessment_list_view(request):
    """
    List all assessments with filtering.
    """
    assessments = Assessment.objects.select_related('unit', 'level').filter(is_active=True)

    # Filter by type
    type_filter = request.GET.get('type', '')
    if type_filter:
        assessments = assessments.filter(assessment_type=type_filter)

    # Filter by level
    level_filter = request.GET.get('level', '')
    if level_filter:
        assessments = assessments.filter(
            Q(level_id=level_filter) | Q(unit__level_id=level_filter)
        )

    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        assessments = assessments.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Sorting
    sort_by = request.GET.get('sort', '-created_at')
    assessments = assessments.order_by(sort_by)

    # Pagination
    paginator = Paginator(assessments, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get filter options
    levels = YLELevel.objects.filter(is_active=True)

    context = {
        'page_obj': page_obj,
        'assessments': page_obj.object_list,
        'type_filter': type_filter,
        'level_filter': level_filter,
        'search_query': search_query,
        'sort_by': sort_by,
        'levels': levels,
        'assessment_types': Assessment.ASSESSMENT_TYPE_CHOICES,
    }

    return render(request, 'courses/assessment_list.html', context)


@login_required
def assessment_detail_view(request, assessment_id):
    """
    Detail view for an assessment.
    """
    assessment = get_object_or_404(
        Assessment.objects.select_related('unit', 'level'),
        id=assessment_id,
        is_active=True
    )

    # Get skills tested
    skills_tested = []
    if assessment.tests_listening:
        skills_tested.append('Listening')
    if assessment.tests_reading:
        skills_tested.append('Reading')
    if assessment.tests_writing:
        skills_tested.append('Writing')
    if assessment.tests_speaking:
        skills_tested.append('Speaking')

    # Check if user is a student and get their results
    student_results = None
    if hasattr(request.user, 'student'):
        from progress.models import AssessmentResult
        student_results = AssessmentResult.objects.filter(
            student=request.user.student,
            assessment=assessment
        ).order_by('-completed_at')

    # Get question count from questions_data
    question_count = 0
    if assessment.questions_data:
        if isinstance(assessment.questions_data, list):
            question_count = len(assessment.questions_data)
        elif isinstance(assessment.questions_data, dict) and 'questions' in assessment.questions_data:
            question_count = len(assessment.questions_data['questions'])

    context = {
        'assessment': assessment,
        'skills_tested': skills_tested,
        'student_results': student_results,
        'question_count': question_count,
    }

    return render(request, 'courses/assessment_detail.html', context)


@login_required
def assessment_take_view(request, assessment_id):
    """
    View for students to take an assessment.
    """
    # Check if user is a student
    if not hasattr(request.user, 'student'):
        messages.error(request, 'Only students can take assessments.')
        return redirect('assessment_detail', assessment_id=assessment_id)

    student = request.user.student
    assessment = get_object_or_404(
        Assessment.objects.select_related('unit', 'level'),
        id=assessment_id,
        is_active=True
    )

    # Check prerequisites (if unit assessment, check unit access)
    if assessment.unit:
        # Check if student is enrolled in a class for this level
        if not student.assigned_class or student.assigned_class.level != assessment.unit.level:
            messages.error(request, 'You are not enrolled in a class for this level.')
            return redirect('assessment_detail', assessment_id=assessment_id)

    if request.method == 'POST':
        from progress.models import AssessmentResult

        # Calculate time taken
        start_time = request.POST.get('start_time')
        if start_time:
            start_datetime = datetime.fromisoformat(start_time)
            time_taken = int((timezone.now() - start_datetime).total_seconds() / 60)
        else:
            time_taken = 0

        # Get student answers
        student_answers = {}
        for key, value in request.POST.items():
            if key.startswith('question_'):
                question_id = key.replace('question_', '')
                student_answers[question_id] = value

        # Calculate scores
        total_score = 0
        max_score = assessment.max_score
        questions = assessment.questions_data

        # Initialize skill scores
        skill_scores = {
            'listening': {'score': 0, 'max': 0},
            'reading': {'score': 0, 'max': 0},
            'writing': {'score': 0, 'max': 0},
            'speaking': {'score': 0, 'max': 0},
        }

        # Calculate score for each question
        if isinstance(questions, list):
            for i, question in enumerate(questions):
                question_id = str(i)
                correct_answer = question.get('correct_answer')
                student_answer = student_answers.get(question_id)
                points = question.get('points', 1)
                skill = question.get('skill', '').lower()

                if skill in skill_scores:
                    skill_scores[skill]['max'] += points

                if student_answer and correct_answer:
                    if str(student_answer).strip().lower() == str(correct_answer).strip().lower():
                        total_score += points
                        if skill in skill_scores:
                            skill_scores[skill]['score'] += points

        # Calculate percentage
        percentage = (total_score / max_score * 100) if max_score > 0 else 0
        passed = percentage >= float(assessment.passing_percentage)

        # Get attempt number
        previous_attempts = AssessmentResult.objects.filter(
            student=student,
            assessment=assessment
        ).count()

        # Create assessment result
        result = AssessmentResult.objects.create(
            student=student,
            assessment=assessment,
            total_score=total_score,
            max_score=max_score,
            percentage=round(percentage, 2),
            listening_score=skill_scores['listening']['score'] if skill_scores['listening']['max'] > 0 else None,
            reading_score=skill_scores['reading']['score'] if skill_scores['reading']['max'] > 0 else None,
            writing_score=skill_scores['writing']['score'] if skill_scores['writing']['max'] > 0 else None,
            speaking_score=skill_scores['speaking']['score'] if skill_scores['speaking']['max'] > 0 else None,
            passed=passed,
            attempt_number=previous_attempts + 1,
            student_answers=student_answers,
            time_taken_minutes=time_taken,
        )

        messages.success(
            request,
            f'Assessment completed! Score: {total_score}/{max_score} ({percentage:.1f}%)'
        )
        return redirect('assessment_result', result_id=result.id)

    # GET request - show assessment questions
    questions = assessment.questions_data or []

    context = {
        'assessment': assessment,
        'questions': questions,
        'start_time': timezone.now().isoformat(),
    }

    return render(request, 'courses/assessment_take.html', context)


@login_required
def assessment_result_view(request, result_id):
    """
    Show assessment results for a student.
    """
    from progress.models import AssessmentResult

    result = get_object_or_404(
        AssessmentResult.objects.select_related('assessment', 'student'),
        id=result_id
    )

    # Check if user has permission to view this result
    if hasattr(request.user, 'student'):
        if result.student != request.user.student:
            messages.error(request, 'You do not have permission to view this result.')
            return redirect('assessment_list')
    elif not request.user.is_staff:
        # Teachers can view results for their students
        if hasattr(request.user, 'teacher_profile'):
            teacher = request.user.teacher_profile
            student_classes = Class.objects.filter(teacher=teacher)
            if result.student.assigned_class not in student_classes:
                messages.error(request, 'You do not have permission to view this result.')
                return redirect('assessment_list')

    # Get questions for review
    questions = result.assessment.questions_data or []

    # Get previous attempts
    previous_attempts = AssessmentResult.objects.filter(
        student=result.student,
        assessment=result.assessment
    ).exclude(id=result_id).order_by('-completed_at')

    context = {
        'result': result,
        'questions': questions,
        'previous_attempts': previous_attempts,
    }

    return render(request, 'courses/assessment_result.html', context)


# ============== AJAX/API ENDPOINTS ==============

@login_required
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
def api_level_units(request, level_id):
    """
    API endpoint to get units for a level.
    """
    level = get_object_or_404(YLELevel, id=level_id)
    units = level.units.filter(is_active=True).values(
        'id', 'title', 'order'
    )

    return JsonResponse({'units': list(units)})
