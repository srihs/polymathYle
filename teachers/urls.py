from django.urls import path
from . import views

urlpatterns = [
    # Teacher Management
    path('', views.teacher_list_view, name='teacher_list'),
    path('add/', views.teacher_add_view, name='teacher_add'),
    path('<int:teacher_id>/', views.teacher_detail_view, name='teacher_detail'),
    path('<int:teacher_id>/edit/', views.teacher_edit_view, name='teacher_edit'),

    # Teacher Documents
    path('documents/', views.teacher_documents_view, name='teacher_documents'),

    # Teacher Rates
    path('rates/', views.teacher_rates_view, name='teacher_rates'),
    path('<int:teacher_id>/rate/add/', views.teacher_rate_add_view, name='teacher_rate_add'),
    path('rate/<int:rate_id>/edit/', views.teacher_rate_edit_view, name='teacher_rate_edit'),
    path('rate/<int:rate_id>/delete/', views.teacher_rate_delete_view, name='teacher_rate_delete'),
]
