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
]
