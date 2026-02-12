from django.urls import path
from . import views

urlpatterns = [
    # Public URLs
    path('apply/', views.apply_view, name='apply'),
    path('application/success/<int:application_id>/', views.application_success_view, name='application_success'),
    path('application/status/', views.application_status_view, name='application_status'),

    # Student URLs (require login)
    path('dashboard/', views.student_dashboard_view, name='student_dashboard'),

    # Guardian URLs (require login)
    path('guardian/portal/', views.guardian_portal_view, name='guardian_portal'),

    # Student Management (Staff/Admin)
    path('students/', views.student_list_view, name='student_list'),
    path('students/<int:student_id>/', views.student_detail_view, name='student_detail'),
    path('students/<int:student_id>/edit/', views.student_edit_view, name='student_edit'),

    # Application Management (Staff/Admin)
    path('applications/', views.application_list_view, name='application_list'),
    path('applications/<int:application_id>/review/', views.application_review_view, name='application_review'),
    path('applications/<int:application_id>/enroll/', views.student_enroll_view, name='student_enroll'),

    # Attendance Management (Teachers/Staff)
    path('attendance/mark/', views.attendance_mark_view, name='attendance_mark'),
    path('attendance/report/', views.attendance_report_view, name='attendance_report'),
]
