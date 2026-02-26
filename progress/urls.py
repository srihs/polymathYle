"""
Progress App URL Configuration

URL patterns for student progress tracking including:
- Dashboard views
- Skill progress tracking
- Unit and lesson progress
- Activity attempts
- Staff reports
"""

from django.urls import path
from . import views


urlpatterns = [
    # Progress Dashboard
    path(
        '',
        views.progress_dashboard_view,
        name='progress_dashboard'
    ),

    # Skill Progress URLs
    path(
        'skills/',
        views.skill_progress_list_view,
        name='skill_progress_list'
    ),
    path(
        'skills/<str:skill>/',
        views.skill_progress_detail_view,
        name='skill_progress_detail'
    ),

    # Unit Progress URLs
    path(
        'units/',
        views.unit_progress_list_view,
        name='unit_progress_list'
    ),
    path(
        'units/<int:unit_id>/',
        views.unit_progress_detail_view,
        name='unit_progress_detail'
    ),

    # Lesson Progress URLs
    path(
        'lessons/<int:lesson_id>/',
        views.lesson_progress_view,
        name='lesson_progress'
    ),
    path(
        'lessons/<int:lesson_id>/complete/',
        views.mark_lesson_complete_view,
        name='mark_lesson_complete'
    ),

    # Activity URLs
    path(
        'activities/<int:activity_id>/',
        views.activity_attempt_view,
        name='activity_attempt'
    ),
    path(
        'activities/<int:activity_id>/history/',
        views.activity_history_view,
        name='activity_history'
    ),

    # Staff Report URLs
    path(
        'reports/student/<int:student_id>/',
        views.student_progress_report_view,
        name='student_progress_report'
    ),
    path(
        'reports/class/<int:class_id>/',
        views.class_progress_report_view,
        name='class_progress_report'
    ),
]
