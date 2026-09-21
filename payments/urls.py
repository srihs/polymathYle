from django.urls import path
from . import views

urlpatterns = [
    # Payment Tier Management
    path('tiers/', views.payment_tier_list_view, name='payment_tier_list'),
    path('tiers/add/', views.payment_tier_add_view, name='payment_tier_add'),
    path('tiers/<int:pk>/edit/', views.payment_tier_edit_view, name='payment_tier_edit'),

    # Paying uploaders per scanned application
    path('applications/', views.application_payment_report_view, name='application_payment_report'),
    path('applications/process/', views.application_payment_process_view, name='application_payment_process'),
    path('applications/<int:run_id>/', views.application_payment_detail_view, name='application_payment_detail'),
]
