from django.contrib import admin
from .models import PaymentTier


@admin.register(PaymentTier)
class PaymentTierAdmin(admin.ModelAdmin):
    """
    Admin interface for PaymentTier model.
    """
    list_display = [
        'name', 'payment_type', 'display_rate_amount',
        'is_active', 'created_at', 'updated_at'
    ]
    list_filter = ['payment_type', 'is_active', 'created_at']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['name']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'is_active')
        }),
        ('Payment Configuration', {
            'fields': ('payment_type', 'hourly_rate', 'fixed_amount')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['activate_tiers', 'deactivate_tiers']

    def display_rate_amount(self, obj):
        """Display the appropriate rate or amount based on payment type."""
        if obj.payment_type == 'HOURLY':
            return f"LKR {obj.hourly_rate}/hour" if obj.hourly_rate else "-"
        return f"LKR {obj.fixed_amount} (fixed)" if obj.fixed_amount else "-"
    display_rate_amount.short_description = "Rate / Amount"

    def activate_tiers(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} payment tier(s) activated.')
    activate_tiers.short_description = "Activate selected payment tiers"

    def deactivate_tiers(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} payment tier(s) deactivated.')
    deactivate_tiers.short_description = "Deactivate selected payment tiers"
