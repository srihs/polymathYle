from django.contrib import admin
from .models import Certificate, CertificateTemplate, Achievement


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = [
        'certificate_number', 'student', 'certificate_type', 'level',
        'shields_earned', 'issue_date', 'is_verified'
    ]
    list_filter = ['certificate_type', 'level', 'is_verified', 'issue_date']
    search_fields = ['certificate_number', 'student__full_name', 'student__admission_number', 'title']
    readonly_fields = ['certificate_number', 'issue_date', 'created_at']
    date_hierarchy = 'issue_date'

    fieldsets = (
        ('Student & Type', {
            'fields': ('student', 'certificate_type', 'level')
        }),
        ('Certificate Details', {
            'fields': ('title', 'description', 'certificate_number', 'template_name')
        }),
        ('Shields (4 Skills)', {
            'fields': (
                'shields_earned',
                'listening_shields', 'reading_shields',
                'writing_shields', 'speaking_shields'
            )
        }),
        ('Files', {
            'fields': ('certificate_pdf',)
        }),
        ('Verification', {
            'fields': ('is_verified', 'issue_date', 'created_at')
        }),
    )


@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'template_type', 'is_active', 'created_at']
    list_filter = ['template_type', 'is_active']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Template Info', {
            'fields': ('name', 'description', 'template_type', 'is_active')
        }),
        ('Design', {
            'fields': ('html_template', 'css_styles', 'layout_settings')
        }),
        ('Visual Elements', {
            'fields': ('background_image', 'logo_image')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ['student', 'title', 'achievement_type', 'points_awarded', 'earned_date']
    list_filter = ['achievement_type', 'earned_date']
    search_fields = ['student__full_name', 'title', 'description']
    readonly_fields = ['earned_date']
    date_hierarchy = 'earned_date'

    fieldsets = (
        ('Student', {
            'fields': ('student',)
        }),
        ('Achievement Details', {
            'fields': ('achievement_type', 'title', 'description', 'icon')
        }),
        ('Points & Date', {
            'fields': ('points_awarded', 'earned_date')
        }),
        ('Related Items', {
            'fields': ('related_unit', 'related_lesson'),
            'classes': ('collapse',)
        }),
    )
