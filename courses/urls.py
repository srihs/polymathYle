"""
URL configuration for the courses app.

Handles routing for YLE Levels, Classes, Units, Lessons, and Assessments.
"""
from django.urls import path
from . import views

urlpatterns = [
    # ============== YLE LEVEL URLs ==============
    path('levels/', views.level_list_view, name='level_list'),
    path('levels/add/', views.yle_level_add_view, name='yle_level_add'),
    path('levels/<int:level_id>/', views.level_detail_view, name='level_detail'),

    # ============== CLASS URLs ==============
    path('classes/', views.class_list_view, name='class_list'),
    path('classes/add/', views.class_add_view, name='class_add'),
    path('classes/<int:class_id>/', views.class_detail_view, name='class_detail'),
    path('classes/<int:class_id>/edit/', views.class_edit_view, name='class_edit'),

    # ============== UNIT URLs ==============
    path('levels/<int:level_id>/units/', views.unit_list_view, name='unit_list'),
    path('units/<int:unit_id>/', views.unit_detail_view, name='unit_detail'),

    # ============== LESSON URLs ==============
    path('units/<int:unit_id>/lessons/', views.lesson_list_view, name='lesson_list'),
    path('lessons/<int:lesson_id>/', views.lesson_detail_view, name='lesson_detail'),

    # ============== ASSESSMENT URLs ==============
    path('assessments/', views.assessment_list_view, name='assessment_list'),
    path('assessments/add/', views.assessment_add_view, name='assessment_add'),
    path('assessments/<int:assessment_id>/', views.assessment_detail_view, name='assessment_detail'),
    path('assessments/<int:assessment_id>/take/', views.assessment_take_view, name='assessment_take'),
    path('assessments/results/<int:result_id>/', views.assessment_result_view, name='assessment_result'),

    # ============== API ENDPOINTS ==============
    path('api/classes/<int:class_id>/students/', views.api_class_students, name='api_class_students'),
    path('api/levels/<int:level_id>/units/', views.api_level_units, name='api_level_units'),
]
