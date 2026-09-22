from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Avg, Count, Max, Min, Q
from django.urls import reverse
from django.utils import timezone
from urllib.parse import urlencode
from datetime import datetime, timedelta, date
from .models import (
    Application, Attendance, ClassTransferRequest, Guardian, QRAttendance, Student, StudentBadge,
)
from .forms import ApplicationForm
from .class_allocation import (
    ClassAssignmentError, approve_transfer, assign_class, class_options, create_transfer_request,
    next_course, promote_students, record_history, reject_transfer, schedule_summary, transfer_options,
)
from courses.models import Course, YLELevel
from payments.application_payments import RATE_PER_APPLICATION
from payments.models import ApplicationPaymentRun
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
import logging

logger = logging.getLogger(__name__)


def _student_level_counts():
    """Active students per active level, for the student list summary."""
    counts = dict(
        Student.objects.filter(is_active=True).values_list('current_level').annotate(n=Count('id')).values_list('current_level', 'n')
    )
    counts = {code.upper(): n for code, n in counts.items() if code}
    return [
        {'level': level, 'count': counts.get(level.short_code.upper(), 0)}
        for level in YLELevel.objects.filter(is_active=True).order_by('order', 'id')
    ]


def _levels_with_class_counts():
    """Active levels in display order, each with class_count (active classes)."""
    return YLELevel.objects.filter(is_active=True).annotate(
        class_count=Count('classes', filter=Q(classes__is_active=True))
    ).order_by('order', 'id')


def _course_groups():
    """Active levels with their active courses (each with class_count), for course pickers."""
    courses = Course.ordered().annotate(class_count=Count('classes', filter=Q(classes__is_active=True)))
    groups = []
    for course in courses:
        if not groups or groups[-1]['level'].id != course.level_id:
            groups.append({'level': course.level, 'courses': []})
        groups[-1]['courses'].append(course)
    return groups


def apply_view(request):
    """
    Online application form for parents
    """
    if request.method == 'POST':
        form = ApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            application = form.save()
            messages.success(request, 'Application submitted successfully!')
            return redirect('application_success', application_id=application.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ApplicationForm()

    return render(request, 'students/apply.html', {
        'form': form
    })


def application_success_view(request, application_id):
    """
    Application success confirmation page
    """
    application = get_object_or_404(Application, id=application_id)

    return render(request, 'students/application_success.html', {
        'application': application
    })


def application_status_view(request):
    """
    Check application status (public)
    """
    application = None
    searched = False

    if request.method == 'POST':
        reference_number = request.POST.get('reference_number')
        email = request.POST.get('email')
        searched = True

        try:
            # Try to find by reference_number first, then by admission_number (backward compatibility)
            application = Application.objects.get(
                Q(reference_number=reference_number) | Q(admission_number=reference_number),
                primary_contact_email=email
            )
        except Application.DoesNotExist:
            messages.warning(request, 'Application not found. Please check your details.')

    return render(request, 'students/application_status.html', {
        'application': application,
        'searched': searched
    })


@login_required
def student_dashboard_view(request):
    """
    Student dashboard (requires student login)
    """
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, 'Student profile not found.')
        return redirect('/')

    # Calculate stats
    # Note: These will work better once Progress and Courses apps are created
    lessons_completed = 0  # TODO: Calculate from LessonProgress when Progress app is created
    total_lessons = 0      # TODO: Calculate from Lesson when Courses app is created

    # Attendance percentage (last 30 days)
    thirty_days_ago = timezone.localdate() - timedelta(days=30)
    recent_attendance = student.attendance_records.filter(date__gte=thirty_days_ago)
    total_days = recent_attendance.count()
    present_days = recent_attendance.filter(status='PRESENT').count()
    attendance_percentage = round((present_days / total_days * 100) if total_days > 0 else 0)

    # Average score - TODO: Calculate from AssessmentResult when Progress app is created
    average_score = 0

    # Skill progress - TODO: Calculate from SkillProgress when Progress app is created
    listening_progress = 0
    reading_progress = 0
    writing_progress = 0
    speaking_progress = 0

    return render(request, 'students/student_dashboard.html', {
        'student': student,
        'lessons_completed': lessons_completed,
        'total_lessons': total_lessons,
        'attendance_percentage': attendance_percentage,
        'average_score': average_score,
        'listening_progress': listening_progress,
        'reading_progress': reading_progress,
        'writing_progress': writing_progress,
        'speaking_progress': speaking_progress,
    })


@login_required
def guardian_portal_view(request):
    """
    Parent portal to view children's progress
    """
    try:
        guardian = Guardian.objects.get(user=request.user)
    except Guardian.DoesNotExist:
        messages.error(request, 'Guardian profile not found.')
        return redirect('/')

    return render(request, 'students/guardian_portal.html', {
        'guardian': guardian
    })


# ============== STUDENT MANAGEMENT VIEWS (Staff/Admin) ==============

@login_required
@permission_required('students.view_student', raise_exception=True)
def student_list_view(request):
    """
    List all students with filtering and search
    """
    # Get all students
    students = Student.objects.select_related('user', 'assigned_class', 'current_course').all()

    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        students = students.filter(
            Q(admission_number__icontains=search_query) |
            Q(full_name__icontains=search_query) |
            Q(name_with_initials__icontains=search_query) |
            Q(student_email__icontains=search_query)
        )

    # Filter by level
    level_filter = request.GET.get('level', '')
    if level_filter:
        students = students.filter(current_level=level_filter)

    # Filter by course
    course_filter = request.GET.get('course', '')
    if course_filter.isdigit():
        students = students.filter(current_course_id=course_filter)
    else:
        course_filter = ''

    # Filter by active status
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        students = students.filter(is_active=True)
    elif status_filter == 'inactive':
        students = students.filter(is_active=False)

    # Filter by class
    class_filter = request.GET.get('class_id', '')
    if class_filter:
        students = students.filter(assigned_class_id=class_filter)

    # Sorting
    sort_by = request.GET.get('sort', 'admission_number')
    if sort_by == 'current_level':
        students = students.order_by('current_course__level__order', 'current_course__order', 'admission_number')
    elif sort_by in ['admission_number', 'full_name', 'enrollment_date']:
        students = students.order_by(sort_by)

    # Pagination
    paginator = Paginator(students, 20)  # 20 students per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get classes for filter dropdown
    from courses.models import Class
    classes = Class.objects.filter(is_active=True)

    context = {
        'page_obj': page_obj,
        'students': page_obj.object_list,
        'search_query': search_query,
        'level_filter': level_filter,
        'levels': YLELevel.objects.filter(is_active=True).order_by('order', 'id'),
        'course_filter': course_filter,
        'course_groups': _course_groups(),
        'status_filter': status_filter,
        'class_filter': class_filter,
        'sort_by': sort_by,
        'classes': classes,
        'total_count': students.count(),
        'active_count': Student.objects.filter(is_active=True).count(),
        'level_counts': _student_level_counts(),
    }

    return render(request, 'students/student_list.html', context)


@login_required
@permission_required('students.view_student', raise_exception=True)
def student_detail_view(request, student_id):
    """
    View detailed student information
    """
    student = get_object_or_404(
        Student.objects.select_related('user', 'assigned_class', 'application', 'current_course'),
        id=student_id
    )

    # Get guardians
    guardians = student.guardians.all()

    # Get recent attendance (last 30 days)
    thirty_days_ago = timezone.localdate() - timedelta(days=30)
    recent_attendance = student.attendance_records.filter(
        date__gte=thirty_days_ago
    ).order_by('-date')[:10]

    # Calculate attendance stats
    total_classes = student.attendance_records.filter(date__gte=thirty_days_ago).count()
    present_count = student.attendance_records.filter(
        date__gte=thirty_days_ago,
        status='PRESENT'
    ).count()
    attendance_percentage = round((present_count / total_classes * 100) if total_classes > 0 else 0)

    # Get badges
    badges = student.badges.all()[:5]

    # TODO: Get progress data when Progress app is integrated

    context = {
        'student': student,
        'guardians': guardians,
        'recent_attendance': recent_attendance,
        'total_classes': total_classes,
        'present_count': present_count,
        'attendance_percentage': attendance_percentage,
        'badges': badges,
        'class_history': student.class_history.select_related(
            'from_class', 'to_class', 'from_course', 'to_course', 'changed_by', 'transfer_request'
        )[:20],
        'pending_transfer': student.transfer_requests.filter(status='PENDING').select_related('to_class').first(),
    }

    return render(request, 'students/student_detail.html', context)


@login_required
@permission_required('students.change_student', raise_exception=True)
def student_edit_view(request, student_id):
    """
    Edit student profile
    """
    student = get_object_or_404(Student, id=student_id)

    if request.method == 'POST':
        # Update basic info
        student.full_name = request.POST.get('full_name', student.full_name)
        student.name_with_initials = request.POST.get('name_with_initials', student.name_with_initials)
        student.student_email = request.POST.get('student_email', student.student_email)
        student.home_address = request.POST.get('home_address', student.home_address)
        student.primary_contact_number = request.POST.get('primary_contact_number', student.primary_contact_number)
        student.whatsapp_number = request.POST.get('whatsapp_number', student.whatsapp_number)
        student.current_school = request.POST.get('current_school', student.current_school)
        # Course (and so level) is locked once the student has a class; it then changes only through promotion
        new_course_id = request.POST.get('current_course', '')
        if not student.assigned_class_id and new_course_id and str(new_course_id) != str(student.current_course_id):
            new_course = Course.ordered().filter(id=new_course_id).first() if str(new_course_id).isdigit() else None
            if not new_course:
                messages.error(request, 'Please select a valid course.')
                return redirect('student_edit', student_id=student.id)
            student.current_course = new_course
        student.is_active = request.POST.get('is_active') == 'on'

        # Handle profile picture upload
        if 'profile_picture' in request.FILES:
            student.profile_picture = request.FILES['profile_picture']

        # Class can be assigned here only if the student has none yet;
        # once assigned it changes only through a transfer request or promotion
        class_id = request.POST.get('assigned_class')
        try:
            with transaction.atomic():
                newly_assigned = assign_class(student, class_id) if class_id and not student.assigned_class_id else None
                student.save()
                if newly_assigned:
                    record_history(student, 'ASSIGNED', request.user, to_class=newly_assigned,
                                   to_level=student.current_level, to_course=student.current_course)
        except ClassAssignmentError as e:
            messages.error(request, str(e))
            return redirect('student_edit', student_id=student.id)

        messages.success(request, 'Student profile updated successfully!')
        return redirect('student_detail', student_id=student.id)

    context = {
        'student': student,
        'course_groups': _course_groups(),
        'class_options': [] if student.assigned_class_id else class_options(
            student.application.schedule_preferences if student.application_id else None
        ),
    }

    return render(request, 'students/student_edit.html', context)


# ============== APPLICATION MANAGEMENT VIEWS ==============

@login_required
@permission_required('students.view_application', raise_exception=True)
def application_list_view(request):
    """
    List all applications with filtering
    """
    applications = Application.objects.all()

    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        applications = applications.filter(
            Q(reference_number__icontains=search_query) |
            Q(admission_number__icontains=search_query) |
            Q(full_name__icontains=search_query) |
            Q(primary_contact_email__icontains=search_query) |
            Q(receipt_number__icontains=search_query)
        )

    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        applications = applications.filter(status=status_filter)

    # Filter by application type
    type_filter = request.GET.get('type', '')
    if type_filter:
        applications = applications.filter(application_type=type_filter)

    # Filter by date range
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        applications = applications.filter(application_date__gte=date_from)
    if date_to:
        applications = applications.filter(application_date__lte=date_to)

    # Sorting
    sort_by = request.GET.get('sort', '-application_date')
    applications = applications.order_by(sort_by)

    # Pagination
    paginator = Paginator(applications, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Statistics
    total_applications = applications.count()
    pending_count = applications.filter(status='PENDING').count()
    approved_count = applications.filter(status='APPROVED').count()
    rejected_count = applications.filter(status='REJECTED').count()

    context = {
        'page_obj': page_obj,
        'applications': page_obj.object_list,
        'search_query': search_query,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'date_from': date_from,
        'date_to': date_to,
        'sort_by': sort_by,
        'total_applications': total_applications,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
    }

    return render(request, 'students/application_list.html', context)


@login_required
@permission_required('students.change_application', raise_exception=True)
def application_review_view(request, application_id):
    """
    Review and approve/reject application
    """
    application = get_object_or_404(Application, id=application_id)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'approve':
            application.status = 'APPROVED'
            application.authorized_by = request.user.get_full_name() or request.user.username
            application.authorization_date = timezone.localdate()
            application.save()

            if application.admission_number and not application.qr_code:
                scan_url = request.build_absolute_uri(
                    reverse('attendance_scan', args=[application.admission_number])
                )
                try:
                    application.generate_qr_code(scan_url)
                except Exception:
                    logger.exception("Failed to generate QR code for application %s", application.id)

            messages.success(request, f'Application approved! Admission Number: {application.admission_number}')

            # Option to create student profile
            return redirect('student_enroll', application_id=application.id)

        elif action == 'reject':
            application.status = 'REJECTED'
            application.save()
            messages.warning(request, 'Application rejected.')
            return redirect('application_list')

        elif action == 'waitlist':
            application.status = 'WAITLIST'
            application.save()
            messages.info(request, 'Application moved to waitlist.')
            return redirect('application_list')

    context = {
        'application': application,
    }

    return render(request, 'students/application_review.html', context)


@login_required
@permission_required('students.add_student', raise_exception=True)
def student_enroll_view(request, application_id):
    """
    Create student profile from approved application
    """
    application = get_object_or_404(Application, id=application_id)

    # Check if already enrolled
    if hasattr(application, 'enrolled_student'):
        messages.warning(request, 'Student already enrolled!')
        return redirect('student_detail', student_id=application.enrolled_student.id)

    # Check if application is approved
    if application.status != 'APPROVED':
        messages.error(request, 'Application must be approved before enrollment.')
        return redirect('application_review', application_id=application.id)

    if request.method == 'POST':
        from django.contrib.auth.models import User, Group
        username = f"student_{application.admission_number.lower().replace('-', '_')}"
        class_id = request.POST.get('assigned_class')
        course_id = request.POST.get('current_course', '')
        current_course = Course.ordered().filter(id=course_id).first() if str(course_id).isdigit() else None
        if not current_course:
            messages.error(request, 'Please select a course.')
            return redirect('student_enroll', application_id=application.id)

        try:
            # All or nothing: a full class must not leave a half-created student behind
            with transaction.atomic():
                # Create or get user account
                user, user_created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'email': application.student_email or application.primary_contact_email,
                        'first_name': application.full_name.split()[0] if application.full_name else '',
                    }
                )

                # Set password only if this is a new user
                if user_created:
                    user.set_password(request.POST.get('password', 'student123'))
                    user.save()

                # Add to Students group (create group if it doesn't exist)
                student_group, created = Group.objects.get_or_create(name='Students')
                user.groups.add(student_group)

                # Create student profile
                student = Student(
                    application=application,
                    user=user,
                    admission_number=application.admission_number,
                    full_name=application.full_name,
                    name_with_initials=application.name_with_initials,
                    date_of_birth=application.date_of_birth,
                    age=application.age,
                    gender=application.gender,
                    nationality=application.nationality,
                    student_email=application.student_email,
                    home_address=application.home_address,
                    primary_contact_number=application.mother_contact_number or application.father_contact_number,
                    whatsapp_number=application.whatsapp_number,
                    current_school=application.current_school,
                    current_course=current_course,
                    current_level=current_course.level.short_code,
                )

                # Class allocation (optional when no class has free seats; can be assigned once later)
                class_obj = assign_class(student, class_id) if class_id else None
                student.save()
                record_history(student, 'ENROLLED', request.user, to_class=class_obj,
                               to_level=student.current_level, to_course=current_course)

                if class_obj:
                    application.selected_class_day = schedule_summary(class_obj)[:100]
                    application.save(update_fields=['selected_class_day'])

                # Create guardian profiles
                # Mother
                if application.mother_name:
                    mother = Guardian.objects.create(
                        full_name=application.mother_name,
                        relationship='MOTHER',
                        contact_number=application.mother_contact_number,
                        email=application.primary_contact_email,
                        occupation=application.mother_occupation,
                    )
                    student.guardians.add(mother)

                # Father
                if application.father_name:
                    father = Guardian.objects.create(
                        full_name=application.father_name,
                        relationship='FATHER',
                        contact_number=application.father_contact_number,
                        email=application.primary_contact_email,
                        occupation=application.father_occupation,
                    )
                    student.guardians.add(father)
        except ClassAssignmentError as e:
            messages.error(request, f'{e} Please choose another class.')
            return redirect('student_enroll', application_id=application.id)

        if class_obj:
            messages.success(
                request,
                f'Student enrolled in {class_obj.class_name} successfully! Username: {username}'
            )
        else:
            messages.warning(
                request,
                f'Student enrolled without a class. Username: {username}. '
                'Assign a class from the student Edit page when a seat is available.'
            )
        return redirect('student_detail', student_id=student.id)

    course_groups = _course_groups()
    courses = [course for group in course_groups for course in group['courses']]

    # Pre-select the course whose age range (or its level's) fits the child most closely, otherwise the first
    def age_range(course):
        low = course.age_range_min if course.age_range_min is not None else course.level.age_range_min
        high = course.age_range_max if course.age_range_max is not None else course.level.age_range_max
        return low, high

    fitting = [c for c in courses if application.age and age_range(c)[0] <= application.age <= age_range(c)[1]]
    suggested = min(fitting, key=lambda c: (age_range(c)[1] - age_range(c)[0], c.level.order, c.order)) if fitting else (
        courses[0] if courses else None
    )

    context = {
        'application': application,
        'class_options': class_options(application.schedule_preferences),
        'course_groups': course_groups,
        'suggested_course': suggested.id if suggested else None,
    }

    return render(request, 'students/student_enroll.html', context)


# ============== ATTENDANCE VIEWS ==============

@login_required
@permission_required('students.add_attendance', raise_exception=True)
def attendance_mark_view(request):
    """
    Mark attendance for a class
    """
    from courses.models import Class

    # Get all active classes
    classes = Class.objects.filter(is_active=True)
    selected_class = None
    students = []
    attendance_date = timezone.localdate()

    if request.method == 'POST':
        class_id = request.POST.get('class_id')
        attendance_date_str = request.POST.get('attendance_date')

        if attendance_date_str:
            attendance_date = datetime.strptime(attendance_date_str, '%Y-%m-%d').date()

        if class_id:
            selected_class = get_object_or_404(Class, id=class_id)
            students = selected_class.enrolled_students.filter(is_active=True)

            # Save attendance if submitted
            if 'save_attendance' in request.POST:
                for student in students:
                    status = request.POST.get(f'status_{student.id}')
                    notes = request.POST.get(f'notes_{student.id}', '')

                    if status:
                        # Update or create attendance record
                        attendance, created = Attendance.objects.update_or_create(
                            student=student,
                            class_session=selected_class,
                            date=attendance_date,
                            defaults={
                                'status': status,
                                'notes': notes,
                                'marked_by': request.user,
                            }
                        )

                messages.success(request, 'Attendance marked successfully!')
                return redirect('attendance_mark')

    # Get class from query param if provided
    class_id = request.GET.get('class_id')
    if class_id:
        selected_class = get_object_or_404(Class, id=class_id)
        students = selected_class.enrolled_students.filter(is_active=True)

        # Get existing attendance for this date
        for student in students:
            attendance = Attendance.objects.filter(
                student=student,
                class_session=selected_class,
                date=attendance_date
            ).first()
            student.current_attendance = attendance

    context = {
        'classes': classes,
        'selected_class': selected_class,
        'students': students,
        'attendance_date': attendance_date,
    }

    return render(request, 'students/attendance_mark.html', context)


@login_required
@permission_required('students.view_attendance', raise_exception=True)
def attendance_report_view(request):
    """
    View attendance reports and statistics
    """
    # Default date range: last 30 days
    date_to = timezone.localdate()
    date_from = date_to - timedelta(days=30)

    # Get parameters
    student_id = request.GET.get('student_id')
    class_id = request.GET.get('class_id')
    date_from_str = request.GET.get('date_from')
    date_to_str = request.GET.get('date_to')

    if date_from_str:
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date()
    if date_to_str:
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date()

    # Build query
    attendance_records = Attendance.objects.filter(
        date__gte=date_from,
        date__lte=date_to
    ).select_related('student', 'class_session')

    if student_id:
        attendance_records = attendance_records.filter(student_id=student_id)
        student = get_object_or_404(Student, id=student_id)
    else:
        student = None

    if class_id:
        attendance_records = attendance_records.filter(class_session_id=class_id)
        from courses.models import Class
        selected_class = get_object_or_404(Class, id=class_id)
    else:
        selected_class = None

    # Calculate statistics
    total_records = attendance_records.count()
    present_count = attendance_records.filter(status='PRESENT').count()
    absent_count = attendance_records.filter(status='ABSENT').count()
    late_count = attendance_records.filter(status='LATE').count()
    excused_count = attendance_records.filter(status='EXCUSED').count()

    attendance_percentage = round((present_count / total_records * 100) if total_records > 0 else 0)

    # Pagination
    paginator = Paginator(attendance_records.order_by('-date'), 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get all students and classes for filters
    from courses.models import Class
    students = Student.objects.filter(is_active=True).order_by('full_name')
    classes = Class.objects.filter(is_active=True)

    context = {
        'page_obj': page_obj,
        'attendance_records': page_obj.object_list,
        'date_from': date_from,
        'date_to': date_to,
        'student': student,
        'selected_class': selected_class,
        'students': students,
        'classes': classes,
        'total_records': total_records,
        'present_count': present_count,
        'absent_count': absent_count,
        'late_count': late_count,
        'excused_count': excused_count,
        'attendance_percentage': attendance_percentage,
    }

    return render(request, 'students/attendance_report.html', context)


@login_required
@permission_required('students.add_application', raise_exception=True)
def application_upload_view(request):
    """
    Upload and process scanned application forms
    """
    # The upload page submits in the background so validation errors don't wipe the form
    is_background_submit = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == 'POST':
        form = ApplicationForm(request.POST, request.FILES, require_backside=True)
        if form.is_valid():
            application = form.save(commit=False)

            # Set application type to OFFLINE for scanned forms
            application.application_type = 'OFFLINE'
            application.uploaded_by = request.user

            # Set application date if not provided
            if not application.application_date:
                from datetime import date
                application.application_date = timezone.localdate()

            # Save the application
            application.save()

            messages.success(request, f'Application {application.reference_number} saved successfully!')
            review_url = reverse('application_review', args=[application.id])
            if is_background_submit:
                return JsonResponse({'ok': True, 'redirect': review_url})
            return redirect(review_url)
        else:
            # Log form errors for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Application form validation failed: {form.errors.as_json()}')
            error_list = list(form.non_field_errors())
            field_errors = {}
            for field_name, errors in form.errors.items():
                if field_name != '__all__':
                    label = form.fields[field_name].label if field_name in form.fields else field_name
                    field_errors[field_name] = list(errors)
                    error_list.append(f'{label}: {" ".join(errors)}')

            if is_background_submit:
                # The page stays as it is (scan, extracted data, selected files), so nothing is lost
                return JsonResponse({'ok': False, 'errors': error_list, 'field_errors': field_errors}, status=400)

            messages.error(request, 'Please correct the errors in the form.')
            for error in error_list:
                messages.error(request, error)
    else:
        # Slots start as backside, placement test paper, photo and birth certificate
        form = ApplicationForm(initial={
            type_field: doc_type
            for (_, type_field), doc_type in zip(Application.DOCUMENT_SLOTS, Application.DEFAULT_SLOT_TYPES)
        })

    return render(request, 'students/application_upload.html', {
        'form': form
    })


def attendance_scan_view(request, admission_number):
    """
    Public endpoint hit by phones scanning a student's QR code.
    Records the scan and resolves the related Student (if one exists).
    Intentionally unauthenticated so any device can register a scan.
    """
    student = Student.objects.filter(admission_number__iexact=admission_number).first()

    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        ip_address = forwarded_for.split(',')[0].strip()
    else:
        ip_address = request.META.get('REMOTE_ADDR')

    QRAttendance.objects.create(
        admission_number=admission_number,
        student=student,
        scanned_by=request.user if request.user.is_authenticated else None,
        ip_address=ip_address,
    )

    context = {
        'admission_number': admission_number,
        'student': student,
        'scanned_at': timezone.localtime(),
        'found': student is not None,
    }
    return render(request, 'students/attendance_scan_result.html', context)


@login_required
@permission_required('students.add_application', raise_exception=True)
def admission_number_check_view(request):
    """Check whether an admission number is already used, before the user submits the upload form."""
    number = Application.normalize_admission_number(request.GET.get('number'))
    if not number:
        return JsonResponse({'number': '', 'available': True})
    owner = Application.find_admission_number_owner(number)
    if not owner:
        return JsonResponse({'number': number, 'available': True})
    reference = getattr(owner, 'reference_number', None) or owner.admission_number
    return JsonResponse({
        'number': number,
        'available': False,
        'message': f'Admission number {number} is already used by {owner.full_name} ({reference}).',
    })


@login_required
@permission_required('students.add_application', raise_exception=True)
@require_POST
def ocr_extract_view(request):
    """
    OCR API endpoint to extract text from scanned application forms.
    Accepts POST request with image data (base64 or file upload).

    Request body (JSON):
        - image_data: Base64-encoded image data (data URL format)

    OR multipart form data:
        - image: Uploaded image file

    Returns:
        JSON response with extracted fields or error message
    """
    from .ocr_service import extract_application_data

    try:
        # Check content type
        content_type = request.content_type

        if 'application/json' in content_type:
            # JSON request with base64 image
            try:
                data = json.loads(request.body)
                image_data = data.get('image_data')

                if not image_data:
                    return JsonResponse({
                        'success': False,
                        'error': 'No image data provided'
                    }, status=400)

            except json.JSONDecodeError:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid JSON data'
                }, status=400)

        elif 'multipart/form-data' in content_type:
            # File upload
            image_file = request.FILES.get('image')

            if not image_file:
                return JsonResponse({
                    'success': False,
                    'error': 'No image file provided'
                }, status=400)

            # Read file content
            image_data = image_file.read()

        else:
            return JsonResponse({
                'success': False,
                'error': 'Unsupported content type. Use application/json or multipart/form-data'
            }, status=400)

        # Extract data using OCR service
        result = extract_application_data(image_data)

        if result.get('success'):
            return JsonResponse({
                'success': True,
                'fields': result.get('fields', {}),
                'message': 'Data extracted successfully. Please verify and correct if needed.'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'OCR extraction failed'),
                'setup_instructions': result.get('setup_instructions')
            }, status=500 if 'not configured' in result.get('error', '') else 400)

    except Exception as e:
        logger.exception("OCR extraction error")
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, status=500)


# ============== CLASS TRANSFERS & PROMOTION ==============

def _safe_next(request, fallback):
    from django.utils.http import url_has_allowed_host_and_scheme
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()},
                                                    require_https=request.is_secure()):
        return next_url
    return fallback


@login_required
@permission_required('students.add_classtransferrequest', raise_exception=True)
def transfer_request_create_view(request, student_id):
    """Raise a request to move a student to another class at the same level."""
    student = get_object_or_404(Student.objects.select_related('assigned_class__level', 'application', 'current_course'), id=student_id)

    if not student.assigned_class_id:
        messages.warning(request, 'This student has no class yet. Assign one from the Edit page.')
        return redirect('student_edit', student_id=student.id)

    pending = student.transfer_requests.filter(status='PENDING').select_related('to_class').first()

    if request.method == 'POST':
        try:
            transfer = create_transfer_request(
                student, request.POST.get('to_class'), request.POST.get('reason', ''), request.user
            )
        except ClassAssignmentError as e:
            messages.error(request, str(e))
            retry_url = reverse('transfer_request_create', args=[student.id])
            if request.POST.get('next'):
                retry_url += '?' + urlencode({'next': request.POST['next']})
            return redirect(retry_url)
        messages.success(request, f'Transfer request to {transfer.to_class.class_name} submitted for approval.')
        return redirect(_safe_next(request, reverse('student_detail', args=[student.id])))

    return render(request, 'students/transfer_request_form.html', {
        'student': student,
        'options': transfer_options(student),
        'pending': pending,
        'next': _safe_next(request, ''),
    })


@login_required
@permission_required('students.add_classtransferrequest', raise_exception=True)
def transfer_request_new_view(request):
    """Pick a student (who has a class) to raise a transfer request for."""
    search_query = request.GET.get('search', '').strip()
    students = Student.objects.filter(is_active=True, assigned_class__isnull=False).select_related(
        'assigned_class', 'current_course'
    ).annotate(
        pending_count=Count('transfer_requests', filter=Q(transfer_requests__status='PENDING'))
    ).order_by('full_name')

    if search_query:
        students = students.filter(
            Q(full_name__icontains=search_query) |
            Q(name_with_initials__icontains=search_query) |
            Q(admission_number__icontains=search_query) |
            Q(assigned_class__class_name__icontains=search_query) |
            Q(assigned_class__class_code__icontains=search_query)
        )

    page_obj = Paginator(students, 20).get_page(request.GET.get('page'))
    return render(request, 'students/transfer_request_new.html', {
        'page_obj': page_obj,
        'students': page_obj.object_list,
        'search_query': search_query,
    })


@login_required
@permission_required('students.view_classtransferrequest', raise_exception=True)
def transfer_request_list_view(request):
    """Transfer requests, pending first by default."""
    status_filter = request.GET.get('status', 'PENDING')
    transfers = ClassTransferRequest.objects.select_related(
        'student', 'from_class__level', 'to_class__level', 'requested_by', 'decided_by'
    )
    if status_filter in dict(ClassTransferRequest.STATUS_CHOICES):
        transfers = transfers.filter(status=status_filter)
    else:
        status_filter = ''

    counts = dict(ClassTransferRequest.objects.values_list('status').annotate(n=Count('id')))
    page_obj = Paginator(transfers, 20).get_page(request.GET.get('page'))

    return render(request, 'students/transfer_request_list.html', {
        'page_obj': page_obj,
        'transfers': page_obj.object_list,
        'status_filter': status_filter,
        'status_choices': [(value, label, counts.get(value, 0)) for value, label in ClassTransferRequest.STATUS_CHOICES],
        'total_count': sum(counts.values()),
    })


@login_required
@permission_required('students.approve_classtransferrequest', raise_exception=True)
@require_POST
def transfer_request_decide_view(request, transfer_id):
    """Approve (moves the student) or reject a pending transfer request."""
    transfer = get_object_or_404(ClassTransferRequest.objects.select_related('student', 'to_class'), id=transfer_id)
    action = request.POST.get('action')
    note = request.POST.get('decision_note', '').strip()

    try:
        with transaction.atomic():
            if action == 'approve':
                approve_transfer(transfer, request.user, note)
                messages.success(request, f'{transfer.student.full_name} moved to {transfer.to_class.class_name}.')
            elif action == 'reject':
                reject_transfer(transfer, request.user, note)
                messages.info(request, f'Transfer request for {transfer.student.full_name} rejected.')
            else:
                raise ClassAssignmentError('Unknown action.')
    except ClassAssignmentError as e:
        messages.error(request, str(e))

    return redirect(_safe_next(request, reverse('transfer_request_list')))


@login_required
@require_POST
def transfer_request_cancel_view(request, transfer_id):
    """The requester, or anyone who can approve transfers, can cancel a pending request."""
    transfer = get_object_or_404(ClassTransferRequest.objects.select_related('student'), id=transfer_id)
    if not (transfer.requested_by_id == request.user.id
            or request.user.has_perm('students.approve_classtransferrequest')):
        raise PermissionDenied

    try:
        with transaction.atomic():
            reject_transfer(transfer, request.user, request.POST.get('decision_note', '').strip(), status='CANCELLED')
        messages.info(request, f'Transfer request for {transfer.student.full_name} cancelled.')
    except ClassAssignmentError as e:
        messages.error(request, str(e))

    return redirect(_safe_next(request, reverse('student_detail', args=[transfer.student_id])))


@login_required
@permission_required('students.promote_student', raise_exception=True)
def class_promote_view(request, class_id):
    """Promote selected students of a class into a class of the next course."""
    from courses.models import Class

    class_obj = get_object_or_404(Class.objects.select_related('level', 'course'), id=class_id)
    target_course = next_course(class_obj.course)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                promoted = promote_students(
                    class_obj, request.POST.getlist('students'), request.POST.get('to_class'),
                    request.user, request.POST.get('note', '').strip(),
                )
        except ClassAssignmentError as e:
            messages.error(request, str(e))
            return redirect('class_promote', class_id=class_obj.id)
        to_class = promoted[0].assigned_class
        plural = 's' if len(promoted) != 1 else ''
        messages.success(
            request, f'{len(promoted)} student{plural} promoted to {to_class.class_name} ({to_class.course.name}, {to_class.level.name}).'
        )
        return redirect('class_detail', class_id=class_obj.id)

    target_options = [o for o in class_options() if target_course and o['course_id'] == target_course.id]
    return render(request, 'students/class_promote.html', {
        'class_obj': class_obj,
        'students': class_obj.enrolled_students.filter(is_active=True).order_by('full_name'),
        'target_course': target_course,
        'target_options': target_options,
    })


# ============== APPLICATION UPLOAD LOG ==============

@login_required
def application_upload_log_view(request):
    """Which scanned applications were uploaded, by whom, and how many per user. Superusers only."""
    if not request.user.is_superuser:
        raise PermissionDenied
    from django.contrib.auth.models import User

    all_uploads = Application.objects.filter(application_type='OFFLINE').select_related('uploaded_by', 'payment_run')
    uploads = all_uploads

    # Date range on upload time (created_at); invalid dates are ignored
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    try:
        if date_from:
            uploads = uploads.filter(created_at__date__gte=datetime.strptime(date_from, '%Y-%m-%d').date())
        if date_to:
            uploads = uploads.filter(created_at__date__lte=datetime.strptime(date_to, '%Y-%m-%d').date())
    except ValueError:
        messages.warning(request, 'Invalid date format. Showing all dates.')
        date_from = date_to = ''
        uploads = all_uploads

    # Per-user totals for the selected dates (before the user filter), with what is still unpaid
    users_by_id = {u.id: u for u in User.objects.filter(uploaded_applications__in=uploads).distinct()}
    summary = [
        {
            'user': users_by_id.get(row['uploaded_by']),
            'user_id': row['uploaded_by'],
            'total': row['total'],
            'unpaid': row['unpaid'],
            'paid': row['total'] - row['unpaid'],
            'amount': RATE_PER_APPLICATION * row['unpaid'],
        }
        for row in uploads.values('uploaded_by').annotate(
            total=Count('id'), unpaid=Count('id', filter=Q(payment_run__isnull=True))
        ).order_by('-total')
    ]
    total_uploads = sum(r['total'] for r in summary)
    unpaid_uploads = sum(r['unpaid'] for r in summary)
    payable_amount = RATE_PER_APPLICATION * unpaid_uploads

    user_filter = request.GET.get('user', '')
    if user_filter == 'unknown':
        uploads = uploads.filter(uploaded_by__isnull=True)
    elif user_filter.isdigit():
        uploads = uploads.filter(uploaded_by_id=int(user_filter))
    else:
        user_filter = ''

    uploads = uploads.order_by('-created_at')

    if request.GET.get('export') == 'csv':
        import csv
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="application_upload_log.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow(['Uploaded At', 'Uploaded By', 'Reference Number', 'Student Name', 'Status', 'Payment'])
        for app in uploads:
            uploader = app.uploaded_by
            writer.writerow([
                timezone.localtime(app.created_at).strftime('%Y-%m-%d %H:%M'),
                (uploader.get_full_name() or uploader.username) if uploader else 'Not recorded',
                app.reference_number or '', app.full_name, app.get_status_display(),
                f'Paid (payment {app.payment_run_id})' if app.payment_run_id else 'Not paid',
            ])
        return response

    page_obj = Paginator(uploads, 25).get_page(request.GET.get('page'))
    filter_query = urlencode({k: v for k, v in {
        'date_from': date_from, 'date_to': date_to, 'user': user_filter,
    }.items() if v})

    return render(request, 'students/application_upload_log.html', {
        'page_obj': page_obj,
        'uploads': page_obj.object_list,
        'summary': summary,
        'total_uploads': total_uploads,
        'unpaid_uploads': unpaid_uploads,
        'payable_amount': payable_amount,
        'rate': RATE_PER_APPLICATION,
        'unpaid_range': all_uploads.filter(payment_run__isnull=True).aggregate(
            first=Min('created_at'), last=Max('created_at')
        ),
        'latest_runs': ApplicationPaymentRun.objects.select_related('processed_by')[:5],
        'uploaders': User.objects.filter(uploaded_applications__isnull=False).distinct().order_by('username'),
        'has_unrecorded': all_uploads.filter(uploaded_by__isnull=True).exists(),
        'date_from': date_from,
        'date_to': date_to,
        'user_filter': user_filter,
        'filter_query': filter_query,
    })
