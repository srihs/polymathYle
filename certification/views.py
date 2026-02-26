"""
Views for the certification app.

Handles Certificates, Achievements, Certificate Templates, and Reports.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Q, Count, Avg
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse, Http404
from django.utils import timezone
from datetime import datetime, timedelta, date

from .models import Certificate, CertificateTemplate, Achievement
from students.models import Student
from courses.models import YLELevel, Unit, Lesson


# ============== CERTIFICATE VIEWS ==============

@login_required
def certificate_list_view(request):
    """
    List certificates.
    Staff can see all certificates, students see only their own.
    """
    # Determine if user is a student
    is_student = hasattr(request.user, 'student')

    if is_student:
        # Students see only their own certificates
        certificates = Certificate.objects.filter(
            student=request.user.student
        ).select_related('student', 'level')
    elif request.user.is_staff:
        # Staff sees all certificates
        certificates = Certificate.objects.select_related('student', 'level').all()
    else:
        messages.error(request, 'You do not have permission to view certificates.')
        return redirect('/')

    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        certificates = certificates.filter(
            Q(certificate_number__icontains=search_query) |
            Q(title__icontains=search_query) |
            Q(student__full_name__icontains=search_query) |
            Q(student__admission_number__icontains=search_query)
        )

    # Filter by certificate type
    type_filter = request.GET.get('type', '')
    if type_filter:
        certificates = certificates.filter(certificate_type=type_filter)

    # Filter by level
    level_filter = request.GET.get('level', '')
    if level_filter:
        certificates = certificates.filter(level_id=level_filter)

    # Filter by date range
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        certificates = certificates.filter(issue_date__gte=date_from)
    if date_to:
        certificates = certificates.filter(issue_date__lte=date_to)

    # Sorting
    sort_by = request.GET.get('sort', '-issue_date')
    if sort_by in ['issue_date', '-issue_date', 'certificate_number', 'student__full_name']:
        certificates = certificates.order_by(sort_by)

    # Pagination
    paginator = Paginator(certificates, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get filter options
    levels = YLELevel.objects.filter(is_active=True)

    context = {
        'page_obj': page_obj,
        'certificates': page_obj.object_list,
        'search_query': search_query,
        'type_filter': type_filter,
        'level_filter': level_filter,
        'date_from': date_from,
        'date_to': date_to,
        'sort_by': sort_by,
        'levels': levels,
        'certificate_types': Certificate.CERTIFICATE_TYPE_CHOICES,
        'total_count': certificates.count(),
        'is_student': is_student,
    }

    return render(request, 'certification/certificate_list.html', context)


@login_required
def certificate_detail_view(request, certificate_id):
    """
    View certificate details.
    Students can only view their own certificates.
    """
    certificate = get_object_or_404(
        Certificate.objects.select_related('student', 'level'),
        id=certificate_id
    )

    # Permission check: students can only view their own certificates
    is_student = hasattr(request.user, 'student')
    if is_student and certificate.student != request.user.student:
        messages.error(request, 'You do not have permission to view this certificate.')
        return redirect('certificate_list')

    # Calculate total shields
    total_shields = certificate.calculate_total_shields()
    max_shields = 20  # 5 shields per skill x 4 skills

    context = {
        'certificate': certificate,
        'total_shields': total_shields,
        'max_shields': max_shields,
        'is_student': is_student,
    }

    return render(request, 'certification/certificate_detail.html', context)


@login_required
def certificate_download_view(request, certificate_id):
    """
    Download certificate as PDF.
    Students can only download their own certificates.
    """
    certificate = get_object_or_404(
        Certificate.objects.select_related('student', 'level'),
        id=certificate_id
    )

    # Permission check
    is_student = hasattr(request.user, 'student')
    if is_student and certificate.student != request.user.student:
        messages.error(request, 'You do not have permission to download this certificate.')
        return redirect('certificate_list')

    # Check if PDF exists
    if certificate.certificate_pdf:
        # Serve existing PDF
        response = HttpResponse(
            certificate.certificate_pdf.read(),
            content_type='application/pdf'
        )
        response['Content-Disposition'] = (
            f'attachment; filename="certificate_{certificate.certificate_number}.pdf"'
        )
        return response

    # Generate PDF if not exists
    # TODO: Implement PDF generation using reportlab or weasyprint
    # For now, return a placeholder response

    # Placeholder: Generate simple PDF
    try:
        pdf_content = generate_certificate_pdf(certificate)
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'attachment; filename="certificate_{certificate.certificate_number}.pdf"'
        )
        return response
    except Exception as e:
        messages.error(request, f'Error generating certificate PDF: {str(e)}')
        return redirect('certificate_detail', certificate_id=certificate_id)


def generate_certificate_pdf(certificate):
    """
    Generate a PDF for the certificate.

    This is a placeholder implementation. In production, use a library like
    reportlab, weasyprint, or xhtml2pdf to generate proper PDFs.

    Args:
        certificate: Certificate model instance

    Returns:
        bytes: PDF content
    """
    # Placeholder implementation - returns a simple text-based PDF
    # Replace with actual PDF generation logic
    from io import BytesIO

    # Simple placeholder content
    content = f"""
    CERTIFICATE OF ACHIEVEMENT

    Certificate Number: {certificate.certificate_number}

    This is to certify that

    {certificate.student.full_name}

    has successfully completed

    {certificate.title}

    {certificate.description}

    Issue Date: {certificate.issue_date}

    Total Shields Earned: {certificate.calculate_total_shields()}

    Listening: {certificate.listening_shields}/5
    Reading: {certificate.reading_shields}/5
    Writing: {certificate.writing_shields}/5
    Speaking: {certificate.speaking_shields}/5
    """

    # For a proper implementation, use reportlab:
    # from reportlab.pdfgen import canvas
    # from reportlab.lib.pagesizes import A4, landscape
    #
    # buffer = BytesIO()
    # p = canvas.Canvas(buffer, pagesize=landscape(A4))
    # ... draw certificate content ...
    # p.save()
    # return buffer.getvalue()

    # Placeholder: return plain text as "PDF" (not a real PDF)
    # In production, this should be replaced with actual PDF generation
    return content.encode('utf-8')


def certificate_verify_view(request):
    """
    Public verification page for certificates.
    Anyone can verify a certificate using its certificate number.
    No login required.
    """
    certificate = None
    searched = False

    if request.method == 'POST' or request.GET.get('certificate_number'):
        certificate_number = (
            request.POST.get('certificate_number') or
            request.GET.get('certificate_number', '')
        )
        searched = True

        if certificate_number:
            try:
                certificate = Certificate.objects.select_related(
                    'student', 'level'
                ).get(
                    certificate_number=certificate_number.strip(),
                    is_verified=True
                )
            except Certificate.DoesNotExist:
                messages.warning(
                    request,
                    'Certificate not found or not verified. Please check the certificate number.'
                )

    context = {
        'certificate': certificate,
        'searched': searched,
    }

    return render(request, 'certification/certificate_verify.html', context)


@login_required
@permission_required('certification.add_certificate', raise_exception=True)
def certificate_issue_view(request):
    """
    Staff view to issue certificates to students.
    """
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        certificate_type = request.POST.get('certificate_type')
        level_id = request.POST.get('level_id')
        title = request.POST.get('title')
        description = request.POST.get('description')
        template_name = request.POST.get('template_name', 'default')

        # Skill shields (for level completion certificates)
        listening_shields = int(request.POST.get('listening_shields', 0))
        reading_shields = int(request.POST.get('reading_shields', 0))
        writing_shields = int(request.POST.get('writing_shields', 0))
        speaking_shields = int(request.POST.get('speaking_shields', 0))

        # Validate required fields
        if not all([student_id, certificate_type, title]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('certificate_issue')

        # Get student
        student = get_object_or_404(Student, id=student_id)

        # Get level if provided
        level = None
        if level_id:
            level = get_object_or_404(YLELevel, id=level_id)

        # Calculate total shields
        total_shields = listening_shields + reading_shields + writing_shields + speaking_shields

        # Create certificate
        certificate = Certificate.objects.create(
            student=student,
            certificate_type=certificate_type,
            level=level,
            title=title,
            description=description or f'{title} certificate for {student.full_name}',
            template_name=template_name,
            shields_earned=total_shields,
            listening_shields=listening_shields,
            reading_shields=reading_shields,
            writing_shields=writing_shields,
            speaking_shields=speaking_shields,
        )

        messages.success(
            request,
            f'Certificate issued successfully! Number: {certificate.certificate_number}'
        )
        return redirect('certificate_detail', certificate_id=certificate.id)

    # GET request - show form
    students = Student.objects.filter(is_active=True).order_by('full_name')
    levels = YLELevel.objects.filter(is_active=True)
    templates = CertificateTemplate.objects.filter(is_active=True)

    context = {
        'students': students,
        'levels': levels,
        'templates': templates,
        'certificate_types': Certificate.CERTIFICATE_TYPE_CHOICES,
    }

    return render(request, 'certification/certificate_issue.html', context)


# ============== ACHIEVEMENT VIEWS ==============

@login_required
def achievement_list_view(request):
    """
    List achievements.
    Staff sees all achievements, students see only their own.
    """
    is_student = hasattr(request.user, 'student')

    if is_student:
        achievements = Achievement.objects.filter(
            student=request.user.student
        ).select_related('student', 'related_unit', 'related_lesson')
    elif request.user.is_staff:
        achievements = Achievement.objects.select_related(
            'student', 'related_unit', 'related_lesson'
        ).all()
    else:
        messages.error(request, 'You do not have permission to view achievements.')
        return redirect('/')

    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        achievements = achievements.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(student__full_name__icontains=search_query)
        )

    # Filter by achievement type
    type_filter = request.GET.get('type', '')
    if type_filter:
        achievements = achievements.filter(achievement_type=type_filter)

    # Filter by date range
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        achievements = achievements.filter(earned_date__date__gte=date_from)
    if date_to:
        achievements = achievements.filter(earned_date__date__lte=date_to)

    # Sorting
    sort_by = request.GET.get('sort', '-earned_date')
    if sort_by in ['earned_date', '-earned_date', 'title', 'points_awarded']:
        achievements = achievements.order_by(sort_by)

    # Pagination
    paginator = Paginator(achievements, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Statistics for students
    total_points = 0
    achievement_count = 0
    if is_student:
        student_achievements = Achievement.objects.filter(student=request.user.student)
        total_points = sum(a.points_awarded for a in student_achievements)
        achievement_count = student_achievements.count()

    context = {
        'page_obj': page_obj,
        'achievements': page_obj.object_list,
        'search_query': search_query,
        'type_filter': type_filter,
        'date_from': date_from,
        'date_to': date_to,
        'sort_by': sort_by,
        'achievement_types': Achievement.ACHIEVEMENT_TYPE_CHOICES,
        'total_count': achievements.count(),
        'is_student': is_student,
        'total_points': total_points,
        'achievement_count': achievement_count,
    }

    return render(request, 'certification/achievement_list.html', context)


@login_required
def achievement_detail_view(request, achievement_id):
    """
    View achievement details.
    Students can only view their own achievements.
    """
    achievement = get_object_or_404(
        Achievement.objects.select_related(
            'student', 'related_unit', 'related_lesson'
        ),
        id=achievement_id
    )

    # Permission check
    is_student = hasattr(request.user, 'student')
    if is_student and achievement.student != request.user.student:
        messages.error(request, 'You do not have permission to view this achievement.')
        return redirect('achievement_list')

    # Get other achievements of the same type for comparison (staff only)
    similar_achievements = None
    if request.user.is_staff:
        similar_achievements = Achievement.objects.filter(
            achievement_type=achievement.achievement_type
        ).exclude(id=achievement.id).select_related('student')[:10]

    context = {
        'achievement': achievement,
        'is_student': is_student,
        'similar_achievements': similar_achievements,
    }

    return render(request, 'certification/achievement_detail.html', context)


@login_required
@permission_required('certification.add_achievement', raise_exception=True)
def award_achievement_view(request):
    """
    Staff view to award achievements to students.
    """
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        achievement_type = request.POST.get('achievement_type')
        title = request.POST.get('title')
        description = request.POST.get('description')
        icon = request.POST.get('icon', '')
        points_awarded = int(request.POST.get('points_awarded', 0))
        related_unit_id = request.POST.get('related_unit_id')
        related_lesson_id = request.POST.get('related_lesson_id')

        # Validate required fields
        if not all([student_id, achievement_type, title]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('award_achievement')

        # Get student
        student = get_object_or_404(Student, id=student_id)

        # Get related objects
        related_unit = None
        related_lesson = None
        if related_unit_id:
            related_unit = get_object_or_404(Unit, id=related_unit_id)
        if related_lesson_id:
            related_lesson = get_object_or_404(Lesson, id=related_lesson_id)

        # Check if student already has this achievement type
        existing = Achievement.objects.filter(
            student=student,
            achievement_type=achievement_type
        ).first()

        if existing:
            messages.warning(
                request,
                f'{student.full_name} already has the "{existing.title}" achievement.'
            )
            return redirect('award_achievement')

        # Create achievement
        achievement = Achievement.objects.create(
            student=student,
            achievement_type=achievement_type,
            title=title,
            description=description or f'{title} achieved by {student.full_name}',
            icon=icon,
            points_awarded=points_awarded,
            related_unit=related_unit,
            related_lesson=related_lesson,
        )

        messages.success(
            request,
            f'Achievement "{title}" awarded to {student.full_name}!'
        )
        return redirect('achievement_detail', achievement_id=achievement.id)

    # GET request - show form
    students = Student.objects.filter(is_active=True).order_by('full_name')
    units = Unit.objects.filter(is_active=True).select_related('level')
    lessons = Lesson.objects.filter(is_active=True).select_related('unit__level')

    context = {
        'students': students,
        'units': units,
        'lessons': lessons,
        'achievement_types': Achievement.ACHIEVEMENT_TYPE_CHOICES,
    }

    return render(request, 'certification/award_achievement.html', context)


# ============== TEMPLATE MANAGEMENT VIEWS ==============

@login_required
@staff_member_required
def template_list_view(request):
    """
    List certificate templates (admin only).
    """
    templates = CertificateTemplate.objects.all()

    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        templates = templates.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Filter by template type
    type_filter = request.GET.get('type', '')
    if type_filter:
        templates = templates.filter(template_type=type_filter)

    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        templates = templates.filter(is_active=True)
    elif status_filter == 'inactive':
        templates = templates.filter(is_active=False)

    # Sorting
    sort_by = request.GET.get('sort', 'name')
    if sort_by in ['name', 'template_type', '-created_at', '-updated_at']:
        templates = templates.order_by(sort_by)

    # Pagination
    paginator = Paginator(templates, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'templates': page_obj.object_list,
        'search_query': search_query,
        'type_filter': type_filter,
        'status_filter': status_filter,
        'sort_by': sort_by,
        'template_types': CertificateTemplate.TEMPLATE_TYPE_CHOICES,
        'total_count': templates.count(),
    }

    return render(request, 'certification/template_list.html', context)


@login_required
@staff_member_required
def template_preview_view(request, template_id):
    """
    Preview a certificate template with sample data.
    """
    template = get_object_or_404(CertificateTemplate, id=template_id)

    # Sample data for preview
    sample_data = {
        'student_name': 'Sample Student',
        'certificate_number': 'YLE-2024-SAMPLE-0001',
        'title': 'Sample Certificate Title',
        'description': 'This is a sample certificate description for preview purposes.',
        'issue_date': date.today().strftime('%B %d, %Y'),
        'level_name': 'A1 Movers',
        'listening_shields': 4,
        'reading_shields': 5,
        'writing_shields': 3,
        'speaking_shields': 4,
        'total_shields': 16,
    }

    # Render HTML template with sample data
    rendered_html = template.html_template
    for key, value in sample_data.items():
        rendered_html = rendered_html.replace(f'{{{{ {key} }}}}', str(value))

    context = {
        'template': template,
        'rendered_html': rendered_html,
        'sample_data': sample_data,
    }

    return render(request, 'certification/template_preview.html', context)


# ============== REPORT VIEWS ==============

@login_required
@permission_required('certification.view_certificate', raise_exception=True)
def certification_report_view(request):
    """
    Staff report on certifications issued.
    Provides statistics and trends on certificate issuance.
    """
    # Date range (default: last 12 months)
    date_to = date.today()
    date_from = date_to - timedelta(days=365)

    date_from_str = request.GET.get('date_from', '')
    date_to_str = request.GET.get('date_to', '')

    if date_from_str:
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date()
    if date_to_str:
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date()

    # Filter by level
    level_filter = request.GET.get('level', '')

    # Base querysets
    certificates_qs = Certificate.objects.filter(
        issue_date__gte=date_from,
        issue_date__lte=date_to
    )
    achievements_qs = Achievement.objects.filter(
        earned_date__date__gte=date_from,
        earned_date__date__lte=date_to
    )

    if level_filter:
        certificates_qs = certificates_qs.filter(level_id=level_filter)

    # Certificate statistics
    total_certificates = certificates_qs.count()
    certificates_by_type = certificates_qs.values('certificate_type').annotate(
        count=Count('id')
    ).order_by('-count')

    certificates_by_level = certificates_qs.filter(level__isnull=False).values(
        'level__name'
    ).annotate(count=Count('id')).order_by('-count')

    # Monthly trend
    monthly_certificates = []
    current_date = date_from
    while current_date <= date_to:
        month_start = current_date.replace(day=1)
        if current_date.month == 12:
            month_end = current_date.replace(year=current_date.year + 1, month=1, day=1)
        else:
            month_end = current_date.replace(month=current_date.month + 1, day=1)

        count = certificates_qs.filter(
            issue_date__gte=month_start,
            issue_date__lt=month_end
        ).count()

        monthly_certificates.append({
            'month': month_start.strftime('%B %Y'),
            'count': count,
        })

        # Move to next month
        current_date = month_end

    # Achievement statistics
    total_achievements = achievements_qs.count()
    achievements_by_type = achievements_qs.values('achievement_type').annotate(
        count=Count('id')
    ).order_by('-count')

    total_points_awarded = sum(a.points_awarded for a in achievements_qs)

    # Average shields per certificate (for level completion)
    level_certificates = certificates_qs.filter(certificate_type='LEVEL_COMPLETE')
    avg_shields = level_certificates.aggregate(
        avg_listening=Avg('listening_shields'),
        avg_reading=Avg('reading_shields'),
        avg_writing=Avg('writing_shields'),
        avg_speaking=Avg('speaking_shields'),
    )

    # Recent certificates
    recent_certificates = certificates_qs.select_related(
        'student', 'level'
    ).order_by('-issue_date')[:10]

    # Top students by certificates
    top_students = Student.objects.filter(
        certificates__issue_date__gte=date_from,
        certificates__issue_date__lte=date_to
    ).annotate(
        cert_count=Count('certificates')
    ).order_by('-cert_count')[:10]

    # Get levels for filter
    levels = YLELevel.objects.filter(is_active=True)

    context = {
        'date_from': date_from,
        'date_to': date_to,
        'level_filter': level_filter,
        'levels': levels,
        # Certificate stats
        'total_certificates': total_certificates,
        'certificates_by_type': certificates_by_type,
        'certificates_by_level': certificates_by_level,
        'monthly_certificates': monthly_certificates,
        'recent_certificates': recent_certificates,
        'top_students': top_students,
        'avg_shields': avg_shields,
        # Achievement stats
        'total_achievements': total_achievements,
        'achievements_by_type': achievements_by_type,
        'total_points_awarded': total_points_awarded,
        # Types for display
        'certificate_types': dict(Certificate.CERTIFICATE_TYPE_CHOICES),
        'achievement_types': dict(Achievement.ACHIEVEMENT_TYPE_CHOICES),
    }

    return render(request, 'certification/certification_report.html', context)


# ============== AJAX/API ENDPOINTS ==============

@login_required
def api_student_certificates(request, student_id):
    """
    API endpoint to get certificates for a specific student.
    """
    # Permission check
    is_student = hasattr(request.user, 'student')
    if is_student and request.user.student.id != student_id:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    if not is_student and not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    certificates = Certificate.objects.filter(student_id=student_id).values(
        'id', 'certificate_number', 'certificate_type', 'title',
        'issue_date', 'shields_earned'
    )

    return JsonResponse({'certificates': list(certificates)})


@login_required
def api_student_achievements(request, student_id):
    """
    API endpoint to get achievements for a specific student.
    """
    # Permission check
    is_student = hasattr(request.user, 'student')
    if is_student and request.user.student.id != student_id:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    if not is_student and not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    achievements = Achievement.objects.filter(student_id=student_id).values(
        'id', 'achievement_type', 'title', 'icon',
        'points_awarded', 'earned_date'
    )

    return JsonResponse({'achievements': list(achievements)})


@login_required
@staff_member_required
def api_certificate_stats(request):
    """
    API endpoint for certificate statistics (staff only).
    Returns summary statistics for dashboard widgets.
    """
    # Last 30 days
    thirty_days_ago = date.today() - timedelta(days=30)

    certificates_30d = Certificate.objects.filter(issue_date__gte=thirty_days_ago)
    achievements_30d = Achievement.objects.filter(earned_date__date__gte=thirty_days_ago)

    stats = {
        'certificates_last_30_days': certificates_30d.count(),
        'achievements_last_30_days': achievements_30d.count(),
        'total_certificates': Certificate.objects.count(),
        'total_achievements': Achievement.objects.count(),
        'certificates_by_type': list(
            certificates_30d.values('certificate_type').annotate(count=Count('id'))
        ),
    }

    return JsonResponse(stats)
