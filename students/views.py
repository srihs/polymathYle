from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Avg, Count, Q
from datetime import datetime, timedelta, date
from .models import Application, Student, Guardian, Attendance, StudentBadge
from .forms import ApplicationForm
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
import logging

logger = logging.getLogger(__name__)


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
    thirty_days_ago = datetime.now().date() - timedelta(days=30)
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
    students = Student.objects.select_related('user', 'assigned_class').all()

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
    if sort_by in ['admission_number', 'full_name', 'enrollment_date', 'current_level']:
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
        'status_filter': status_filter,
        'class_filter': class_filter,
        'sort_by': sort_by,
        'classes': classes,
        'total_count': students.count(),
    }

    return render(request, 'students/student_list.html', context)


@login_required
@permission_required('students.view_student', raise_exception=True)
def student_detail_view(request, student_id):
    """
    View detailed student information
    """
    student = get_object_or_404(
        Student.objects.select_related('user', 'assigned_class', 'application'),
        id=student_id
    )

    # Get guardians
    guardians = student.guardians.all()

    # Get recent attendance (last 30 days)
    thirty_days_ago = date.today() - timedelta(days=30)
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
        student.current_level = request.POST.get('current_level', student.current_level)
        student.is_active = request.POST.get('is_active') == 'on'

        # Handle class assignment
        class_id = request.POST.get('assigned_class')
        if class_id:
            from courses.models import Class
            student.assigned_class = get_object_or_404(Class, id=class_id)

        # Handle profile picture upload
        if 'profile_picture' in request.FILES:
            student.profile_picture = request.FILES['profile_picture']

        student.save()
        messages.success(request, 'Student profile updated successfully!')
        return redirect('student_detail', student_id=student.id)

    # Get classes for dropdown
    from courses.models import Class
    classes = Class.objects.filter(is_active=True)

    context = {
        'student': student,
        'classes': classes,
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
            application.authorization_date = date.today()
            application.save()
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
        # Create user account
        from django.contrib.auth.models import User, Group
        username = f"student_{application.admission_number.lower().replace('-', '_')}"

        user = User.objects.create_user(
            username=username,
            email=application.student_email or application.primary_contact_email,
            password=request.POST.get('password', 'student123'),  # Default password
            first_name=application.full_name.split()[0] if application.full_name else '',
        )

        # Add to Students group
        student_group = Group.objects.get(name='Students')
        user.groups.add(student_group)

        # Create student profile
        student = Student.objects.create(
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
            current_level=request.POST.get('current_level', 'STARTERS'),
        )

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

        messages.success(request, f'Student enrolled successfully! Username: {username}')
        return redirect('student_detail', student_id=student.id)

    context = {
        'application': application,
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
    attendance_date = date.today()

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
    date_to = date.today()
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
    if request.method == 'POST':
        form = ApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            application = form.save(commit=False)

            # Set application type to OFFLINE for scanned forms
            application.application_type = 'OFFLINE'

            # Handle office use fields (not in ApplicationForm)
            admission_number = request.POST.get('admission_number', '').strip()
            if admission_number:
                application.admission_number = admission_number

            application_date = request.POST.get('application_date', '').strip()
            if application_date:
                try:
                    from datetime import datetime
                    # Parse date from form (YYYY-MM-DD format)
                    parsed_date = datetime.strptime(application_date, '%Y-%m-%d').date()
                    application.application_date = parsed_date
                except (ValueError, TypeError):
                    # If parsing fails, use current date as default
                    from datetime import date
                    application.application_date = date.today()
            else:
                # No date provided, use current date
                from datetime import date
                application.application_date = date.today()

            receipt_number = request.POST.get('receipt_number', '').strip()
            if receipt_number:
                application.receipt_number = receipt_number

            # Save the application
            application.save()

            messages.success(request, f'Application {application.reference_number} saved successfully!')
            return redirect('application_review', application_id=application.id)
        else:
            messages.error(request, 'Please correct the errors in the form.')
    else:
        form = ApplicationForm()

    return render(request, 'students/application_upload.html', {
        'form': form
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

