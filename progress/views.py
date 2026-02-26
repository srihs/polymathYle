"""
Progress App Views

Provides views for tracking student progress including:
- Progress dashboard with overall skill progress
- Skill progress tracking (Listening, Reading, Writing, Speaking)
- Unit and lesson progress tracking
- Activity attempt submission and history
- Staff reports for individual students and classes
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Avg, Sum, Count, Q, F
from django.db import transaction
from django.core.paginator import Paginator
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta

from .models import (
    SkillProgress,
    UnitProgress,
    LessonProgress,
    ActivityAttempt,
    AssessmentResult,
)
from students.models import Student
from courses.models import YLELevel, Unit, Lesson, Activity, Assessment, Class


# ============== HELPER FUNCTIONS ==============

def get_student_for_user(user):
    """
    Retrieve student profile for the authenticated user.

    Args:
        user: Django User instance

    Returns:
        Student instance or None if not found
    """
    try:
        return Student.objects.select_related(
            'user', 'assigned_class', 'assigned_class__level'
        ).get(user=user)
    except Student.DoesNotExist:
        return None


def get_or_create_skill_progress(student, level, skill):
    """
    Get or create a SkillProgress record for a student.

    Args:
        student: Student instance
        level: YLELevel instance
        skill: Skill type string (LISTENING, READING, WRITING, SPEAKING)

    Returns:
        SkillProgress instance
    """
    skill_progress, created = SkillProgress.objects.get_or_create(
        student=student,
        level=level,
        skill=skill,
        defaults={
            'mastery_percentage': Decimal('0.00'),
            'total_activities_completed': 0,
            'total_activities_available': 0,
            'average_score': Decimal('0.00'),
            'highest_score': Decimal('0.00'),
            'total_time_spent_minutes': 0,
        }
    )
    return skill_progress


# ============== PROGRESS DASHBOARD ==============

@login_required
def progress_dashboard_view(request):
    """
    Overall progress dashboard for a student showing all skill progress
    and recent activity.

    Displays:
    - Overall mastery percentage across all skills
    - Individual skill progress bars
    - Recent activity attempts
    - Current unit progress
    - Recent assessment results
    """
    student = get_student_for_user(request.user)
    if not student:
        messages.error(request, 'Student profile not found.')
        return redirect('/')

    # Get current level
    level = None
    if student.assigned_class:
        level = student.assigned_class.level
    else:
        # Fallback to student's current_level setting
        level = YLELevel.objects.filter(
            short_code=student.current_level
        ).first()

    if not level:
        messages.warning(request, 'No level assigned. Please contact your teacher.')
        return render(request, 'progress/dashboard.html', {
            'student': student,
            'no_level': True,
        })

    # Get skill progress for current level
    skill_progress_list = SkillProgress.objects.filter(
        student=student,
        level=level
    ).order_by('skill')

    # Create progress records if they don't exist
    skills = ['LISTENING', 'READING', 'WRITING', 'SPEAKING']
    for skill in skills:
        get_or_create_skill_progress(student, level, skill)

    # Refresh skill progress list after creation
    skill_progress_list = SkillProgress.objects.filter(
        student=student,
        level=level
    ).order_by('skill')

    # Calculate overall progress
    overall_mastery = skill_progress_list.aggregate(
        avg_mastery=Avg('mastery_percentage')
    )['avg_mastery'] or Decimal('0.00')

    total_time_spent = skill_progress_list.aggregate(
        total_time=Sum('total_time_spent_minutes')
    )['total_time'] or 0

    # Get unit progress
    unit_progress_list = UnitProgress.objects.filter(
        student=student,
        unit__level=level
    ).select_related('unit').order_by('unit__order')[:5]

    # Get recent activity attempts
    recent_attempts = ActivityAttempt.objects.filter(
        student=student
    ).select_related(
        'activity', 'activity__lesson', 'activity__lesson__unit'
    ).order_by('-created_at')[:10]

    # Get recent assessment results
    recent_assessments = AssessmentResult.objects.filter(
        student=student
    ).select_related('assessment').order_by('-completed_at')[:5]

    # Calculate completion stats
    total_units = Unit.objects.filter(level=level, is_active=True).count()
    completed_units = UnitProgress.objects.filter(
        student=student,
        unit__level=level,
        status='COMPLETED'
    ).count()

    total_lessons = Lesson.objects.filter(
        unit__level=level,
        is_active=True
    ).count()
    completed_lessons = LessonProgress.objects.filter(
        student=student,
        lesson__unit__level=level,
        is_completed=True
    ).count()

    context = {
        'student': student,
        'level': level,
        'skill_progress_list': skill_progress_list,
        'overall_mastery': overall_mastery,
        'total_time_spent': total_time_spent,
        'unit_progress_list': unit_progress_list,
        'recent_attempts': recent_attempts,
        'recent_assessments': recent_assessments,
        'total_units': total_units,
        'completed_units': completed_units,
        'total_lessons': total_lessons,
        'completed_lessons': completed_lessons,
    }

    return render(request, 'progress/dashboard.html', context)


# ============== SKILL PROGRESS VIEWS ==============

@login_required
def skill_progress_list_view(request):
    """
    List skill progress across all skills for the current level.

    Shows detailed breakdown of each skill including:
    - Mastery percentage
    - Activities completed
    - Average and highest scores
    - Time spent
    """
    student = get_student_for_user(request.user)
    if not student:
        messages.error(request, 'Student profile not found.')
        return redirect('/')

    # Get current level
    level = None
    if student.assigned_class:
        level = student.assigned_class.level
    else:
        level = YLELevel.objects.filter(
            short_code=student.current_level
        ).first()

    if not level:
        messages.warning(request, 'No level assigned.')
        return render(request, 'progress/skill_progress_list.html', {
            'student': student,
            'no_level': True,
        })

    # Ensure all skill progress records exist
    skills = ['LISTENING', 'READING', 'WRITING', 'SPEAKING']
    for skill in skills:
        get_or_create_skill_progress(student, level, skill)

    # Get skill progress with annotations
    skill_progress_list = SkillProgress.objects.filter(
        student=student,
        level=level
    ).order_by('skill')

    # Enrich with additional stats per skill
    for progress in skill_progress_list:
        # Get recent attempts for this skill
        progress.recent_attempts = ActivityAttempt.objects.filter(
            student=student,
            skill_type=progress.skill
        ).order_by('-created_at')[:5]

        # Calculate trend (improvement over last 10 attempts)
        last_10_scores = ActivityAttempt.objects.filter(
            student=student,
            skill_type=progress.skill
        ).order_by('-created_at')[:10].values_list('percentage', flat=True)

        if len(last_10_scores) >= 2:
            recent_avg = sum(last_10_scores[:5]) / min(5, len(last_10_scores[:5]))
            older_avg = sum(last_10_scores[5:]) / max(1, len(last_10_scores[5:]))
            progress.trend = 'improving' if recent_avg > older_avg else (
                'declining' if recent_avg < older_avg else 'stable'
            )
        else:
            progress.trend = 'insufficient_data'

    context = {
        'student': student,
        'level': level,
        'skill_progress_list': skill_progress_list,
    }

    return render(request, 'progress/skill_progress_list.html', context)


@login_required
def skill_progress_detail_view(request, skill):
    """
    Detailed progress view for a specific skill.

    Args:
        skill: Skill type (listening, reading, writing, speaking)

    Shows:
    - Detailed progress metrics for the skill
    - Activity history for this skill
    - Lessons focusing on this skill
    - Recommendations for improvement
    """
    student = get_student_for_user(request.user)
    if not student:
        messages.error(request, 'Student profile not found.')
        return redirect('/')

    # Normalize skill name
    skill_upper = skill.upper()
    valid_skills = ['LISTENING', 'READING', 'WRITING', 'SPEAKING']
    if skill_upper not in valid_skills:
        messages.error(request, 'Invalid skill type.')
        return redirect('skill_progress_list')

    # Get current level
    level = None
    if student.assigned_class:
        level = student.assigned_class.level
    else:
        level = YLELevel.objects.filter(
            short_code=student.current_level
        ).first()

    if not level:
        messages.warning(request, 'No level assigned.')
        return redirect('progress_dashboard')

    # Get or create skill progress
    skill_progress = get_or_create_skill_progress(student, level, skill_upper)

    # Get all activity attempts for this skill
    attempts = ActivityAttempt.objects.filter(
        student=student,
        skill_type=skill_upper
    ).select_related(
        'activity', 'activity__lesson', 'activity__lesson__unit'
    ).order_by('-created_at')

    # Pagination for attempts
    paginator = Paginator(attempts, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get lessons that focus on this skill
    skill_field_map = {
        'LISTENING': 'skill_listening',
        'READING': 'skill_reading',
        'WRITING': 'skill_writing',
        'SPEAKING': 'skill_speaking',
    }
    skill_filter = {skill_field_map[skill_upper]: True}

    related_lessons = Lesson.objects.filter(
        unit__level=level,
        is_active=True,
        **skill_filter
    ).select_related('unit').order_by('unit__order', 'order')[:10]

    # Check completion status for each lesson
    for lesson in related_lessons:
        lesson_progress = LessonProgress.objects.filter(
            student=student,
            lesson=lesson
        ).first()
        lesson.is_completed = lesson_progress.is_completed if lesson_progress else False

    # Calculate score distribution
    score_ranges = {
        '0-20': attempts.filter(percentage__lt=20).count(),
        '20-40': attempts.filter(percentage__gte=20, percentage__lt=40).count(),
        '40-60': attempts.filter(percentage__gte=40, percentage__lt=60).count(),
        '60-80': attempts.filter(percentage__gte=60, percentage__lt=80).count(),
        '80-100': attempts.filter(percentage__gte=80).count(),
    }

    context = {
        'student': student,
        'level': level,
        'skill': skill_upper,
        'skill_display': skill.capitalize(),
        'skill_progress': skill_progress,
        'page_obj': page_obj,
        'attempts': page_obj.object_list,
        'related_lessons': related_lessons,
        'score_ranges': score_ranges,
        'total_attempts': attempts.count(),
    }

    return render(request, 'progress/skill_progress_detail.html', context)


# ============== UNIT PROGRESS VIEWS ==============

@login_required
def unit_progress_list_view(request):
    """
    List all unit progress for a student.

    Shows:
    - All units in current level with progress status
    - Completion percentage for each unit
    - Lessons completed vs total
    - Unit scores if available
    """
    student = get_student_for_user(request.user)
    if not student:
        messages.error(request, 'Student profile not found.')
        return redirect('/')

    # Get current level
    level = None
    if student.assigned_class:
        level = student.assigned_class.level
    else:
        level = YLELevel.objects.filter(
            short_code=student.current_level
        ).first()

    if not level:
        messages.warning(request, 'No level assigned.')
        return render(request, 'progress/unit_progress_list.html', {
            'student': student,
            'no_level': True,
        })

    # Get all units for this level
    units = Unit.objects.filter(
        level=level,
        is_active=True
    ).prefetch_related('lessons').order_by('order')

    # Build unit progress data
    unit_data = []
    for unit in units:
        # Get or create unit progress
        unit_progress, created = UnitProgress.objects.get_or_create(
            student=student,
            unit=unit,
            defaults={
                'status': 'NOT_STARTED',
                'lessons_completed': 0,
                'total_lessons': unit.lessons.filter(is_active=True).count(),
                'completion_percentage': Decimal('0.00'),
            }
        )

        # Update total lessons count if needed
        total_lessons = unit.lessons.filter(is_active=True).count()
        if unit_progress.total_lessons != total_lessons:
            unit_progress.total_lessons = total_lessons
            unit_progress.save(update_fields=['total_lessons'])

        # Check prerequisites
        unit_progress.is_locked = False
        if unit.requires_completion_of:
            prereq_progress = UnitProgress.objects.filter(
                student=student,
                unit=unit.requires_completion_of,
                status='COMPLETED'
            ).exists()
            unit_progress.is_locked = not prereq_progress

        unit_data.append({
            'unit': unit,
            'progress': unit_progress,
            'lesson_count': total_lessons,
        })

    context = {
        'student': student,
        'level': level,
        'unit_data': unit_data,
    }

    return render(request, 'progress/unit_progress_list.html', context)


@login_required
def unit_progress_detail_view(request, unit_id):
    """
    Detailed progress for a specific unit.

    Args:
        unit_id: ID of the unit

    Shows:
    - Unit overview and description
    - Lesson-by-lesson progress
    - Activity completion within each lesson
    - Unit assessment results if available
    """
    student = get_student_for_user(request.user)
    if not student:
        messages.error(request, 'Student profile not found.')
        return redirect('/')

    unit = get_object_or_404(
        Unit.objects.select_related('level').prefetch_related('lessons'),
        id=unit_id,
        is_active=True
    )

    # Get or create unit progress
    unit_progress, created = UnitProgress.objects.get_or_create(
        student=student,
        unit=unit,
        defaults={
            'status': 'NOT_STARTED',
            'lessons_completed': 0,
            'total_lessons': unit.lessons.filter(is_active=True).count(),
            'completion_percentage': Decimal('0.00'),
        }
    )

    # Get lessons with progress
    lessons = unit.lessons.filter(is_active=True).order_by('order')
    lesson_data = []

    for lesson in lessons:
        lesson_progress, _ = LessonProgress.objects.get_or_create(
            student=student,
            lesson=lesson,
            defaults={
                'is_completed': False,
                'attempts_count': 0,
                'time_spent_minutes': 0,
                'activities_completed': 0,
                'total_activities': lesson.activities.filter(is_active=True).count(),
            }
        )

        # Get activity data for this lesson
        activities = lesson.activities.filter(is_active=True).order_by('order')
        activity_attempts = ActivityAttempt.objects.filter(
            student=student,
            activity__in=activities
        ).values('activity_id').annotate(
            best_score=Avg('percentage'),
            attempt_count=Count('id')
        )

        activity_dict = {a['activity_id']: a for a in activity_attempts}

        activity_data = []
        for activity in activities:
            attempt_info = activity_dict.get(activity.id, {})
            activity_data.append({
                'activity': activity,
                'best_score': attempt_info.get('best_score'),
                'attempt_count': attempt_info.get('attempt_count', 0),
            })

        lesson_data.append({
            'lesson': lesson,
            'progress': lesson_progress,
            'activities': activity_data,
        })

    # Get unit assessments
    assessments = Assessment.objects.filter(
        unit=unit,
        is_active=True
    )

    assessment_results = AssessmentResult.objects.filter(
        student=student,
        assessment__in=assessments
    ).select_related('assessment').order_by('-completed_at')

    context = {
        'student': student,
        'unit': unit,
        'unit_progress': unit_progress,
        'lesson_data': lesson_data,
        'assessments': assessments,
        'assessment_results': assessment_results,
    }

    return render(request, 'progress/unit_progress_detail.html', context)


# ============== LESSON PROGRESS VIEWS ==============

@login_required
def lesson_progress_view(request, lesson_id):
    """
    View lesson completion status and details.

    Args:
        lesson_id: ID of the lesson

    Shows:
    - Lesson details and content
    - Completion status
    - Activity list with completion status
    - Time spent on lesson
    """
    student = get_student_for_user(request.user)
    if not student:
        messages.error(request, 'Student profile not found.')
        return redirect('/')

    lesson = get_object_or_404(
        Lesson.objects.select_related('unit', 'unit__level').prefetch_related('activities'),
        id=lesson_id,
        is_active=True
    )

    # Get or create lesson progress
    lesson_progress, created = LessonProgress.objects.get_or_create(
        student=student,
        lesson=lesson,
        defaults={
            'is_completed': False,
            'attempts_count': 0,
            'time_spent_minutes': 0,
            'activities_completed': 0,
            'total_activities': lesson.activities.filter(is_active=True).count(),
        }
    )

    # Get activities with attempt data
    activities = lesson.activities.filter(is_active=True).order_by('order')
    activity_data = []

    for activity in activities:
        attempts = ActivityAttempt.objects.filter(
            student=student,
            activity=activity
        ).order_by('-created_at')

        best_attempt = attempts.order_by('-percentage').first()

        activity_data.append({
            'activity': activity,
            'attempts': attempts[:5],
            'best_attempt': best_attempt,
            'total_attempts': attempts.count(),
        })

    # Get skills covered in this lesson
    skills_covered = []
    if lesson.skill_listening:
        skills_covered.append('Listening')
    if lesson.skill_reading:
        skills_covered.append('Reading')
    if lesson.skill_writing:
        skills_covered.append('Writing')
    if lesson.skill_speaking:
        skills_covered.append('Speaking')

    context = {
        'student': student,
        'lesson': lesson,
        'lesson_progress': lesson_progress,
        'activity_data': activity_data,
        'skills_covered': skills_covered,
    }

    return render(request, 'progress/lesson_progress.html', context)


@login_required
def mark_lesson_complete_view(request, lesson_id):
    """
    Mark a lesson as complete.

    Args:
        lesson_id: ID of the lesson to mark complete

    Handles both regular POST and AJAX requests.
    Updates related unit progress after marking lesson complete.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    student = get_student_for_user(request.user)
    if not student:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Student profile not found'}, status=404)
        messages.error(request, 'Student profile not found.')
        return redirect('/')

    lesson = get_object_or_404(Lesson, id=lesson_id, is_active=True)

    with transaction.atomic():
        # Get or create lesson progress
        lesson_progress, created = LessonProgress.objects.get_or_create(
            student=student,
            lesson=lesson,
            defaults={
                'is_completed': False,
                'attempts_count': 0,
                'time_spent_minutes': 0,
                'activities_completed': 0,
                'total_activities': lesson.activities.filter(is_active=True).count(),
            }
        )

        # Mark as complete
        if not lesson_progress.is_completed:
            lesson_progress.is_completed = True
            lesson_progress.completion_date = timezone.now()
            lesson_progress.attempts_count = F('attempts_count') + 1
            lesson_progress.save(update_fields=[
                'is_completed', 'completion_date', 'attempts_count', 'updated_at'
            ])

            # Update unit progress
            unit = lesson.unit
            unit_progress, _ = UnitProgress.objects.get_or_create(
                student=student,
                unit=unit,
                defaults={
                    'status': 'NOT_STARTED',
                    'lessons_completed': 0,
                    'total_lessons': unit.lessons.filter(is_active=True).count(),
                    'completion_percentage': Decimal('0.00'),
                }
            )

            # Update lesson count
            completed_lessons = LessonProgress.objects.filter(
                student=student,
                lesson__unit=unit,
                is_completed=True
            ).count()

            total_lessons = unit.lessons.filter(is_active=True).count()
            completion_percentage = (
                Decimal(completed_lessons) / Decimal(total_lessons) * 100
            ) if total_lessons > 0 else Decimal('0.00')

            # Determine unit status
            if completed_lessons >= total_lessons:
                unit_status = 'COMPLETED'
                completed_at = timezone.now()
            elif completed_lessons > 0:
                unit_status = 'IN_PROGRESS'
                completed_at = None
            else:
                unit_status = 'NOT_STARTED'
                completed_at = None

            # Update unit progress
            unit_progress.lessons_completed = completed_lessons
            unit_progress.total_lessons = total_lessons
            unit_progress.completion_percentage = completion_percentage
            unit_progress.status = unit_status
            if completed_at:
                unit_progress.completed_at = completed_at
            if unit_status == 'IN_PROGRESS' and not unit_progress.started_at:
                unit_progress.started_at = timezone.now()
            unit_progress.save()

            # Award points to student
            student.total_points = F('total_points') + lesson.completion_points
            student.save(update_fields=['total_points', 'last_activity'])

            success_message = f'Lesson "{lesson.title}" marked as complete!'
        else:
            success_message = 'Lesson was already completed.'

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': success_message,
            'is_completed': True,
            'completion_date': lesson_progress.completion_date.isoformat() if lesson_progress.completion_date else None,
        })

    messages.success(request, success_message)
    return redirect('lesson_progress', lesson_id=lesson_id)


# ============== ACTIVITY VIEWS ==============

@login_required
def activity_attempt_view(request, activity_id):
    """
    Submit an activity attempt.

    Args:
        activity_id: ID of the activity

    Handles AJAX POST requests with student answers.
    Calculates score and updates progress records.
    """
    student = get_student_for_user(request.user)
    if not student:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Student profile not found'}, status=404)
        messages.error(request, 'Student profile not found.')
        return redirect('/')

    activity = get_object_or_404(
        Activity.objects.select_related('lesson', 'lesson__unit', 'lesson__unit__level'),
        id=activity_id,
        is_active=True
    )

    if request.method == 'POST':
        # Parse request data
        import json

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        else:
            data = request.POST

        student_answers = data.get('answers', {})
        time_taken_seconds = int(data.get('time_taken', 0))

        # Calculate score based on activity type and answers
        score, max_score, percentage = calculate_activity_score(
            activity, student_answers
        )

        # Determine skill type from lesson
        skill_type = None
        lesson = activity.lesson
        if lesson.skill_listening:
            skill_type = 'LISTENING'
        elif lesson.skill_reading:
            skill_type = 'READING'
        elif lesson.skill_writing:
            skill_type = 'WRITING'
        elif lesson.skill_speaking:
            skill_type = 'SPEAKING'

        with transaction.atomic():
            # Get attempt number
            previous_attempts = ActivityAttempt.objects.filter(
                student=student,
                activity=activity
            ).count()

            # Create attempt record
            attempt = ActivityAttempt.objects.create(
                student=student,
                activity=activity,
                attempt_number=previous_attempts + 1,
                student_answers=student_answers,
                score=score,
                max_score=max_score,
                percentage=percentage,
                skill_type=skill_type,
                time_taken_seconds=time_taken_seconds,
                is_completed=True,
                completed_at=timezone.now(),
            )

            # Update lesson progress
            lesson_progress, _ = LessonProgress.objects.get_or_create(
                student=student,
                lesson=lesson,
                defaults={
                    'is_completed': False,
                    'attempts_count': 0,
                    'time_spent_minutes': 0,
                    'activities_completed': 0,
                    'total_activities': lesson.activities.filter(is_active=True).count(),
                }
            )

            # Check if this is first completion of this activity
            is_first_completion = previous_attempts == 0
            if is_first_completion:
                lesson_progress.activities_completed = F('activities_completed') + 1

            lesson_progress.time_spent_minutes = F('time_spent_minutes') + (
                time_taken_seconds // 60
            )
            lesson_progress.save(update_fields=[
                'activities_completed', 'time_spent_minutes', 'updated_at'
            ])

            # Update skill progress
            if skill_type:
                level = lesson.unit.level
                skill_progress = get_or_create_skill_progress(
                    student, level, skill_type
                )

                # Update skill metrics
                if is_first_completion:
                    skill_progress.total_activities_completed = F(
                        'total_activities_completed'
                    ) + 1

                skill_progress.total_time_spent_minutes = F(
                    'total_time_spent_minutes'
                ) + (time_taken_seconds // 60)
                skill_progress.last_activity_date = timezone.now()

                # Recalculate average and highest scores
                all_attempts = ActivityAttempt.objects.filter(
                    student=student,
                    skill_type=skill_type
                )
                avg_score = all_attempts.aggregate(
                    avg=Avg('percentage')
                )['avg'] or Decimal('0.00')
                highest = all_attempts.aggregate(
                    max=Avg('percentage')
                )['max'] or Decimal('0.00')

                skill_progress.average_score = avg_score
                if percentage > skill_progress.highest_score:
                    skill_progress.highest_score = percentage

                skill_progress.save()
                skill_progress.update_progress()

            # Update student points and activity
            points_earned = int(activity.max_points * (percentage / 100))
            student.total_points = F('total_points') + points_earned
            student.save(update_fields=['total_points', 'last_activity'])

        response_data = {
            'success': True,
            'attempt_id': attempt.id,
            'score': float(score),
            'max_score': float(max_score),
            'percentage': float(percentage),
            'attempt_number': attempt.attempt_number,
            'points_earned': points_earned,
            'is_first_completion': is_first_completion,
        }

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse(response_data)

        messages.success(
            request,
            f'Activity completed! Score: {percentage:.1f}% (+{points_earned} points)'
        )
        return redirect('lesson_progress', lesson_id=activity.lesson.id)

    # GET request - show activity page
    previous_attempts = ActivityAttempt.objects.filter(
        student=student,
        activity=activity
    ).order_by('-created_at')[:5]

    context = {
        'student': student,
        'activity': activity,
        'previous_attempts': previous_attempts,
    }

    return render(request, 'progress/activity_attempt.html', context)


def calculate_activity_score(activity, student_answers):
    """
    Calculate score for an activity based on type and answers.

    Args:
        activity: Activity instance
        student_answers: Dict of student's answers

    Returns:
        Tuple of (score, max_score, percentage)
    """
    activity_data = activity.activity_data or {}
    correct_answers = activity_data.get('answers', {})
    max_score = Decimal(str(activity.max_points))

    if not correct_answers:
        # If no correct answers defined, give full marks
        return max_score, max_score, Decimal('100.00')

    correct_count = 0
    total_questions = len(correct_answers)

    for question_id, correct_answer in correct_answers.items():
        student_answer = student_answers.get(str(question_id))

        if isinstance(correct_answer, list):
            # Multiple correct answers or ordered list
            if isinstance(student_answer, list):
                if student_answer == correct_answer:
                    correct_count += 1
            elif student_answer in correct_answer:
                correct_count += 1
        else:
            # Single correct answer
            if str(student_answer).lower().strip() == str(correct_answer).lower().strip():
                correct_count += 1

    if total_questions > 0:
        percentage = Decimal(correct_count) / Decimal(total_questions) * 100
        score = max_score * Decimal(correct_count) / Decimal(total_questions)
    else:
        percentage = Decimal('100.00')
        score = max_score

    return score.quantize(Decimal('0.01')), max_score, percentage.quantize(Decimal('0.01'))


@login_required
def activity_history_view(request, activity_id):
    """
    View past attempts for an activity.

    Args:
        activity_id: ID of the activity

    Shows complete history of attempts with scores and timestamps.
    """
    student = get_student_for_user(request.user)
    if not student:
        messages.error(request, 'Student profile not found.')
        return redirect('/')

    activity = get_object_or_404(
        Activity.objects.select_related('lesson', 'lesson__unit'),
        id=activity_id,
        is_active=True
    )

    attempts = ActivityAttempt.objects.filter(
        student=student,
        activity=activity
    ).order_by('-created_at')

    # Pagination
    paginator = Paginator(attempts, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Calculate stats
    stats = attempts.aggregate(
        best_score=Avg('percentage'),
        avg_score=Avg('percentage'),
        total_time=Sum('time_taken_seconds'),
    )

    best_attempt = attempts.order_by('-percentage').first()

    context = {
        'student': student,
        'activity': activity,
        'page_obj': page_obj,
        'attempts': page_obj.object_list,
        'stats': stats,
        'best_attempt': best_attempt,
        'total_attempts': attempts.count(),
    }

    return render(request, 'progress/activity_history.html', context)


# ============== STAFF REPORT VIEWS ==============

@login_required
@permission_required('progress.view_skillprogress', raise_exception=True)
def student_progress_report_view(request, student_id):
    """
    Staff view of a student's complete progress report.

    Args:
        student_id: ID of the student

    Comprehensive report including:
    - Overall progress summary
    - Skill breakdown
    - Unit completion status
    - Recent activity
    - Assessment results
    - Recommendations
    """
    student = get_object_or_404(
        Student.objects.select_related(
            'user', 'assigned_class', 'assigned_class__level', 'assigned_class__teacher'
        ),
        id=student_id
    )

    # Get level
    level = student.assigned_class.level if student.assigned_class else None

    if not level:
        level = YLELevel.objects.filter(short_code=student.current_level).first()

    # Get skill progress
    skill_progress_list = SkillProgress.objects.filter(
        student=student,
        level=level
    ).order_by('skill') if level else []

    # Get unit progress
    unit_progress_list = UnitProgress.objects.filter(
        student=student
    ).select_related('unit', 'unit__level').order_by(
        'unit__level__order', 'unit__order'
    ) if level else []

    # Get all assessment results
    assessment_results = AssessmentResult.objects.filter(
        student=student
    ).select_related('assessment').order_by('-completed_at')

    # Calculate overall statistics
    total_activities_completed = ActivityAttempt.objects.filter(
        student=student,
        is_completed=True
    ).values('activity').distinct().count()

    total_time_spent = ActivityAttempt.objects.filter(
        student=student
    ).aggregate(total=Sum('time_taken_seconds'))['total'] or 0
    total_time_hours = total_time_spent // 3600
    total_time_minutes = (total_time_spent % 3600) // 60

    avg_score = ActivityAttempt.objects.filter(
        student=student
    ).aggregate(avg=Avg('percentage'))['avg'] or Decimal('0.00')

    # Get recent activity (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_attempts = ActivityAttempt.objects.filter(
        student=student,
        created_at__gte=thirty_days_ago
    ).select_related('activity').order_by('-created_at')[:20]

    # Calculate engagement metrics
    active_days = ActivityAttempt.objects.filter(
        student=student,
        created_at__gte=thirty_days_ago
    ).dates('created_at', 'day').count()

    context = {
        'student': student,
        'level': level,
        'skill_progress_list': skill_progress_list,
        'unit_progress_list': unit_progress_list,
        'assessment_results': assessment_results,
        'total_activities_completed': total_activities_completed,
        'total_time_hours': total_time_hours,
        'total_time_minutes': total_time_minutes,
        'avg_score': avg_score,
        'recent_attempts': recent_attempts,
        'active_days': active_days,
    }

    return render(request, 'progress/student_report.html', context)


@login_required
@permission_required('progress.view_skillprogress', raise_exception=True)
def class_progress_report_view(request, class_id):
    """
    Progress report for an entire class.

    Args:
        class_id: ID of the class

    Shows:
    - Class overview and statistics
    - Student-by-student progress summary
    - Skill averages across class
    - Unit completion rates
    - Struggling students identification
    """
    class_obj = get_object_or_404(
        Class.objects.select_related('level', 'teacher'),
        id=class_id
    )

    # Get all students in this class
    students = Student.objects.filter(
        assigned_class=class_obj,
        is_active=True
    ).order_by('full_name')

    # Build student progress data
    student_data = []
    for student in students:
        # Get overall progress
        skill_progress = SkillProgress.objects.filter(
            student=student,
            level=class_obj.level
        )

        avg_mastery = skill_progress.aggregate(
            avg=Avg('mastery_percentage')
        )['avg'] or Decimal('0.00')

        # Get unit completion
        units_completed = UnitProgress.objects.filter(
            student=student,
            unit__level=class_obj.level,
            status='COMPLETED'
        ).count()

        total_units = Unit.objects.filter(
            level=class_obj.level,
            is_active=True
        ).count()

        # Get recent activity
        last_activity = ActivityAttempt.objects.filter(
            student=student
        ).order_by('-created_at').first()

        # Get average score
        avg_score = ActivityAttempt.objects.filter(
            student=student
        ).aggregate(avg=Avg('percentage'))['avg'] or Decimal('0.00')

        student_data.append({
            'student': student,
            'avg_mastery': avg_mastery,
            'units_completed': units_completed,
            'total_units': total_units,
            'last_activity': last_activity,
            'avg_score': avg_score,
        })

    # Calculate class averages by skill
    skill_averages = {}
    for skill in ['LISTENING', 'READING', 'WRITING', 'SPEAKING']:
        avg = SkillProgress.objects.filter(
            student__in=students,
            level=class_obj.level,
            skill=skill
        ).aggregate(avg=Avg('mastery_percentage'))['avg'] or Decimal('0.00')
        skill_averages[skill] = avg

    # Get unit completion rates for class
    total_students = students.count()
    unit_completion_rates = []

    units = Unit.objects.filter(
        level=class_obj.level,
        is_active=True
    ).order_by('order')

    for unit in units:
        completed_count = UnitProgress.objects.filter(
            student__in=students,
            unit=unit,
            status='COMPLETED'
        ).count()

        rate = (completed_count / total_students * 100) if total_students > 0 else 0
        unit_completion_rates.append({
            'unit': unit,
            'completed_count': completed_count,
            'completion_rate': rate,
        })

    # Identify struggling students (below 50% mastery)
    struggling_students = [
        sd for sd in student_data if sd['avg_mastery'] < 50
    ]

    # Identify top performers (above 80% mastery)
    top_performers = [
        sd for sd in student_data if sd['avg_mastery'] >= 80
    ]

    context = {
        'class_obj': class_obj,
        'students': students,
        'student_data': student_data,
        'skill_averages': skill_averages,
        'unit_completion_rates': unit_completion_rates,
        'struggling_students': struggling_students,
        'top_performers': top_performers,
        'total_students': total_students,
    }

    return render(request, 'progress/class_report.html', context)
