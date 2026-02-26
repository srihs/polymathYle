"""
URL configuration for the certification app.

Handles routes for Certificates, Achievements, Templates, and Reports.
"""
from django.urls import path
from . import views

urlpatterns = [
    # ============== CERTIFICATE URLs ==============

    # Certificate list - shows all (staff) or own (students) certificates
    path('certificates/', views.certificate_list_view, name='certificate_list'),

    # Certificate detail - view single certificate
    path('certificates/<int:certificate_id>/', views.certificate_detail_view, name='certificate_detail'),

    # Certificate download - download as PDF
    path('certificates/<int:certificate_id>/download/', views.certificate_download_view, name='certificate_download'),

    # Certificate verification - public page (no login required)
    path('verify/', views.certificate_verify_view, name='certificate_verify'),

    # Issue certificate - staff only
    path('certificates/issue/', views.certificate_issue_view, name='certificate_issue'),

    # ============== ACHIEVEMENT URLs ==============

    # Achievement list - shows all (staff) or own (students) achievements
    path('achievements/', views.achievement_list_view, name='achievement_list'),

    # Achievement detail - view single achievement
    path('achievements/<int:achievement_id>/', views.achievement_detail_view, name='achievement_detail'),

    # Award achievement - staff only
    path('achievements/award/', views.award_achievement_view, name='award_achievement'),

    # ============== TEMPLATE MANAGEMENT URLs (Admin) ==============

    # Template list - admin only
    path('templates/', views.template_list_view, name='template_list'),

    # Template preview - admin only
    path('templates/<int:template_id>/preview/', views.template_preview_view, name='template_preview'),

    # ============== REPORT URLs ==============

    # Certification report - staff only
    path('reports/', views.certification_report_view, name='certification_report'),

    # ============== API ENDPOINTS ==============

    # Get certificates for a specific student (AJAX)
    path('api/students/<int:student_id>/certificates/', views.api_student_certificates, name='api_student_certificates'),

    # Get achievements for a specific student (AJAX)
    path('api/students/<int:student_id>/achievements/', views.api_student_achievements, name='api_student_achievements'),

    # Certificate statistics for dashboard widgets (AJAX)
    path('api/stats/', views.api_certificate_stats, name='api_certificate_stats'),
]
