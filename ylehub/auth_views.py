"""
Authentication views for role-based access
"""
from django import forms
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth import views as django_auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q
from django.urls import reverse, reverse_lazy


def login_view(request):
    """
    Custom login view that redirects to role-based dashboards
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')

            # Redirect to appropriate dashboard based on role
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'auth/login.html')


def logout_view(request):
    """
    Logout view
    """
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('login')


class UsernameOrEmailPasswordResetForm(PasswordResetForm):
    """
    Password reset form that accepts either a username or an email address,
    since users sign in with usernames (e.g. student_yle_2025_001).
    """
    email = forms.CharField(label='Username or email', max_length=254)

    def get_users(self, email):
        identifier = email.strip()
        users = get_user_model()._default_manager.filter(
            Q(username__iexact=identifier) | Q(email__iexact=identifier),
            is_active=True,
        ).exclude(email='')
        # Only accounts with a usable password can reset it
        return (user for user in users if user.has_usable_password())


class PasswordResetRequestView(django_auth_views.PasswordResetView):
    """Step 1: user enters username or email; a reset link is emailed if an account matches."""
    form_class = UsernameOrEmailPasswordResetForm
    template_name = 'auth/password_reset_form.html'
    email_template_name = 'auth/emails/password_reset_email.txt'
    html_email_template_name = 'auth/emails/password_reset_email.html'
    subject_template_name = 'auth/emails/password_reset_subject.txt'
    success_url = reverse_lazy('password_reset_done')


class PasswordResetSentView(django_auth_views.PasswordResetDoneView):
    """Step 2: confirmation page (same message whether or not an account matched)."""
    template_name = 'auth/password_reset_done.html'


class PasswordResetSetView(django_auth_views.PasswordResetConfirmView):
    """Step 3: user follows the emailed link and chooses a new password."""
    template_name = 'auth/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')


class PasswordResetCompleteView(django_auth_views.PasswordResetCompleteView):
    """Step 4: password changed; prompt to sign in."""
    template_name = 'auth/password_reset_complete.html'


class PasswordChangeView(LoginRequiredMixin, django_auth_views.PasswordChangeView):
    """Logged-in users change their own password (keeps them signed in)."""
    template_name = 'auth/password_change.html'
    # Dashboards don't render flash messages, so return here to show the confirmation
    success_url = reverse_lazy('password_change')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Your password has been changed successfully.')
        return response


@login_required
def dashboard_view(request):
    """
    Role-based dashboard router
    Redirects users to their appropriate dashboard based on their role
    """
    user = request.user

    # Check for specific roles first (Teachers, Students, Guardians, Staff)
    # Teacher - redirect to teacher dashboard
    if user.groups.filter(name='Teachers').exists():
        try:
            teacher = user.teacher_profile
            return redirect('teacher_dashboard')
        except:
            messages.error(request, 'Teacher profile not found. Please contact admin.')
            return redirect('login')

    # Student - redirect to student dashboard
    if user.groups.filter(name='Students').exists():
        try:
            student = user.student_set.first()
            return redirect('student_dashboard')
        except:
            messages.error(request, 'Student profile not found. Please contact admin.')
            return redirect('login')

    # Guardian - redirect to guardian portal
    if user.groups.filter(name='Guardians').exists():
        try:
            guardian = user.guardian_profile
            return redirect('guardian_portal')
        except:
            messages.error(request, 'Guardian profile not found. Please contact admin.')
            return redirect('login')

    # Staff - redirect to staff dashboard
    if user.groups.filter(name='Staff').exists():
        return redirect('staff_dashboard')

    # Superuser/Admin (no specific group) - redirect to admin dashboard
    if user.is_superuser:
        return redirect('admin_dashboard')

    # No role assigned
    messages.warning(request, 'No role assigned to your account. Please contact admin.')
    logout(request)
    return redirect('login')


@login_required
def teacher_dashboard_view(request):
    """
    Teacher dashboard - shows their classes, students, and schedule
    """
    try:
        teacher = request.user.teacher_profile
    except:
        messages.error(request, 'Teacher profile not found.')
        return redirect('dashboard')

    # Get teacher's classes
    classes = teacher.classes_taught.filter(is_active=True)

    # Get students in those classes
    students_count = 0
    for cls in classes:
        students_count += cls.enrolled_students.filter(is_active=True).count()

    context = {
        'teacher': teacher,
        'classes': classes,
        'students_count': students_count,
        'specializations': teacher.get_specializations(),
    }

    return render(request, 'auth/teacher_dashboard.html', context)


@login_required
def staff_dashboard_view(request):
    """
    Staff dashboard - shows pending applications, recent students, etc.
    """
    from students.models import Application, Student

    # Get pending applications
    pending_applications = Application.objects.filter(status='PENDING').order_by('-application_date')[:10]

    # Get recent students
    recent_students = Student.objects.filter(is_active=True).order_by('-enrollment_date')[:10]

    # Get statistics
    total_applications = Application.objects.count()
    total_students = Student.objects.filter(is_active=True).count()
    pending_count = Application.objects.filter(status='PENDING').count()
    approved_count = Application.objects.filter(status='APPROVED').count()

    context = {
        'pending_applications': pending_applications,
        'recent_students': recent_students,
        'total_applications': total_applications,
        'total_students': total_students,
        'pending_count': pending_count,
        'approved_count': approved_count,
    }

    return render(request, 'auth/staff_dashboard.html', context)


@login_required
def admin_dashboard_view(request):
    """
    Admin dashboard - system overview and management
    """
    from django.contrib.auth.models import User
    from teachers.models import Teacher
    from students.models import Student, Application
    from courses.models import Class

    # Get statistics
    total_users = User.objects.count()
    total_teachers = Teacher.objects.filter(is_active=True).count()
    total_students = Student.objects.filter(is_active=True).count()
    total_classes = Class.objects.filter(is_active=True).count()

    # Get recent applications
    recent_applications = Application.objects.all().order_by('-application_date')[:10]

    context = {
        'total_users': total_users,
        'total_teachers': total_teachers,
        'total_students': total_students,
        'total_classes': total_classes,
        'recent_applications': recent_applications,
    }

    return render(request, 'auth/admin_dashboard.html', context)
