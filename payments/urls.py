from django.urls import path
from . import views

urlpatterns = [
    # Payment Tier Management
    path('tiers/', views.payment_tier_list_view, name='payment_tier_list'),
    path('tiers/add/', views.payment_tier_add_view, name='payment_tier_add'),
    path('tiers/<int:pk>/edit/', views.payment_tier_edit_view, name='payment_tier_edit'),
]
