from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Avg, Count, Q
from django.core.paginator import Paginator
from datetime import datetime, timedelta


@login_required
@permission_required('teachers.view_teacher', raise_exception=True)
def teacher_list_view(request):
    """
    List all teachers with filtering and search
    """
    from .models import Teacher

    # Get all teachers
    teachers = Teacher.objects.select_related('user').all()

    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        teachers = teachers.filter(
            Q(employee_id__icontains=search_query) |
            Q(full_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(contact_number__icontains=search_query)
        )

    # Filter by active status
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        teachers = teachers.filter(is_active=True)
    elif status_filter == 'inactive':
        teachers = teachers.filter(is_active=False)

    # Filter by employment type
    employment_filter = request.GET.get('employment_type', '')
    if employment_filter:
        teachers = teachers.filter(employment_type=employment_filter)

    # Filter by specialization
    specialization = request.GET.get('specialization', '')
    if specialization == 'STARTERS':
        teachers = teachers.filter(teaches_starters=True)
    elif specialization == 'MOVERS':
        teachers = teachers.filter(teaches_movers=True)
    elif specialization == 'FLYERS':
        teachers = teachers.filter(teaches_flyers=True)

    # Sorting
    sort_by = request.GET.get('sort', 'full_name')
    if sort_by in ['full_name', 'employee_id', 'date_joined', 'years_of_experience']:
        teachers = teachers.order_by(sort_by)

    # Pagination
    paginator = Paginator(teachers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'teachers': page_obj.object_list,
        'search_query': search_query,
        'status_filter': status_filter,
        'employment_filter': employment_filter,
        'specialization': specialization,
        'sort_by': sort_by,
        'total_count': teachers.count(),
    }

    return render(request, 'teachers/teacher_list.html', context)


@login_required
@permission_required('teachers.view_teacher', raise_exception=True)
def teacher_detail_view(request, teacher_id):
    """
    View detailed teacher information
    """
    from .models import Teacher, TeacherDocument
    from courses.models import Class

    teacher = get_object_or_404(
        Teacher.objects.select_related('user'),
        id=teacher_id
    )

    # Get documents
    documents = teacher.documents.all().order_by('-uploaded_at')

    # Get classes taught
    classes_taught = Class.objects.filter(teacher=teacher, is_active=True)

    # Get specializations
    specializations = teacher.get_specializations()

    context = {
        'teacher': teacher,
        'documents': documents,
        'classes_taught': classes_taught,
        'specializations': specializations,
    }

    return render(request, 'teachers/teacher_detail.html', context)


@login_required
@permission_required('teachers.add_teacher', raise_exception=True)
def teacher_add_view(request):
    """
    Add new teacher
    """
    from .models import Teacher, TeacherDocument
    from django.contrib.auth.models import User, Group
    from django.db import transaction, IntegrityError

    if request.method == 'POST':
        # Get form data
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password', 'teacher123')
        employee_id = request.POST.get('employee_id')
        full_name = request.POST.get('full_name')

        # Validate required fields
        if not all([username, email, employee_id, full_name]):
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'teachers/teacher_add.html')

        # Check if username exists
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists!')
            return render(request, 'teachers/teacher_add.html')

        # Check if employee_id exists
        if Teacher.objects.filter(employee_id=employee_id).exists():
            messages.error(request, 'Employee ID already exists!')
            return render(request, 'teachers/teacher_add.html')

        try:
            with transaction.atomic():
                # Create user account
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=full_name.split()[0] if full_name else '',
                )

                # Add to Teachers group (create if doesn't exist)
                teacher_group, _ = Group.objects.get_or_create(name='Teachers')
                user.groups.add(teacher_group)

                # Create teacher profile
                teacher = Teacher.objects.create(
                    user=user,
                    full_name=full_name,
                    employee_id=employee_id,
                    contact_number=request.POST.get('contact_number', ''),
                    email=email,
                    bio=request.POST.get('bio', ''),
                    qualifications=request.POST.get('qualifications', ''),
                    years_of_experience=int(request.POST.get('years_of_experience') or 0),
                    teaches_starters=request.POST.get('teaches_starters') == 'on',
                    teaches_movers=request.POST.get('teaches_movers') == 'on',
                    teaches_flyers=request.POST.get('teaches_flyers') == 'on',
                    date_joined=request.POST.get('date_joined'),
                    employment_type=request.POST.get('employment_type', 'FULL_TIME'),
                    is_active=True,
                )

                # Handle profile picture
                if 'profile_picture' in request.FILES:
                    teacher.profile_picture = request.FILES['profile_picture']
                    teacher.save()

                messages.success(request, f'Teacher {teacher.full_name} added successfully! Username: {username}')
                return redirect('teacher_detail', teacher_id=teacher.id)

        except IntegrityError as e:
            messages.error(request, 'A record with this information already exists.')
        except Exception as e:
            messages.error(request, f'Error creating teacher: {str(e)}')

    return render(request, 'teachers/teacher_add.html')


@login_required
@permission_required('teachers.change_teacher', raise_exception=True)
def teacher_edit_view(request, teacher_id):
    """
    Edit teacher profile
    """
    from .models import Teacher, TeacherDocument

    teacher = get_object_or_404(Teacher, id=teacher_id)

    if request.method == 'POST':
        # Update teacher info
        teacher.full_name = request.POST.get('full_name', teacher.full_name)
        teacher.contact_number = request.POST.get('contact_number', teacher.contact_number)
        teacher.email = request.POST.get('email', teacher.email)
        teacher.bio = request.POST.get('bio', teacher.bio)
        teacher.qualifications = request.POST.get('qualifications', teacher.qualifications)
        teacher.years_of_experience = int(request.POST.get('years_of_experience', teacher.years_of_experience))

        # Update specializations (YLE levels only - teachers teach all skills)
        teacher.teaches_starters = request.POST.get('teaches_starters') == 'on'
        teacher.teaches_movers = request.POST.get('teaches_movers') == 'on'
        teacher.teaches_flyers = request.POST.get('teaches_flyers') == 'on'

        # Update employment details
        teacher.employment_type = request.POST.get('employment_type', teacher.employment_type)
        teacher.is_active = request.POST.get('is_active') == 'on'

        # Handle profile picture
        if 'profile_picture' in request.FILES:
            teacher.profile_picture = request.FILES['profile_picture']

        teacher.save()
        messages.success(request, 'Teacher profile updated successfully!')
        return redirect('teacher_detail', teacher_id=teacher.id)

    context = {
        'teacher': teacher,
    }

    return render(request, 'teachers/teacher_edit.html', context)


# Teacher Documents Management
@login_required
@permission_required('teachers.view_teacherdocument', raise_exception=True)
def teacher_documents_view(request):
    """List all teacher documents with filtering"""
    from .models import Teacher, TeacherDocument

    documents = TeacherDocument.objects.select_related('teacher').all()

    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        documents = documents.filter(
            Q(teacher__full_name__icontains=search_query) |
            Q(teacher__employee_id__icontains=search_query) |
            Q(document_type__icontains=search_query)
        )

    # Filter by teacher
    teacher_id = request.GET.get('teacher', '')
    if teacher_id:
        documents = documents.filter(teacher_id=teacher_id)

    # Filter by document type
    doc_type = request.GET.get('type', '')
    if doc_type:
        documents = documents.filter(document_type=doc_type)

    # Sorting
    sort_by = request.GET.get('sort', '-uploaded_at')
    documents = documents.order_by(sort_by)

    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(documents, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Get all teachers for filter dropdown
    teachers = Teacher.objects.filter(is_active=True).order_by('full_name')

    # Get document types
    doc_types = TeacherDocument.DOCUMENT_TYPE_CHOICES

    context = {
        'page_obj': page_obj,
        'documents': page_obj.object_list,
        'teachers': teachers,
        'doc_types': doc_types,
        'search_query': search_query,
        'selected_teacher': teacher_id,
        'selected_type': doc_type,
        'sort_by': sort_by,
    }

    return render(request, 'teachers/teacher_documents.html', context)




