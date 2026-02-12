from django.contrib import admin
from .models import Teacher, TeacherDocument, TeacherHourlyRate


class TeacherDocumentInline(admin.TabularInline):
    """Inline admin for teacher documents"""
    model = TeacherDocument
    extra = 1
    fields = ['document_type', 'title', 'document', 'issue_date', 'expiry_date', 'is_verified']
    readonly_fields = ['uploaded_at']


class TeacherHourlyRateInline(admin.TabularInline):
    """Inline admin for teacher hourly rates"""
    model = TeacherHourlyRate
    extra = 1
    fields = ['hourly_rate', 'currency', 'effective_from', 'effective_until', 'is_current', 'reason']
    readonly_fields = ['created_at']


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = [
        'employee_id', 'full_name', 'employment_type',
        'years_of_experience', 'is_active', 'date_joined'
    ]
    list_filter = ['employment_type', 'is_active', 'teaches_starters', 'teaches_movers', 'teaches_flyers']
    search_fields = ['full_name', 'employee_id', 'email', 'contact_number']
    readonly_fields = ['created_at', 'updated_at', 'total_classes_taught']

    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'full_name', 'employee_id')
        }),
        ('Contact Information', {
            'fields': ('contact_number', 'email')
        }),
        ('Profile', {
            'fields': ('profile_picture', 'bio')
        }),
        ('Qualifications', {
            'fields': ('qualifications', 'years_of_experience')
        }),
        ('YLE Level Specializations', {
            'fields': ('teaches_starters', 'teaches_movers', 'teaches_flyers')
        }),
        ('Skill Specializations', {
            'fields': ('specializes_listening', 'specializes_reading', 'specializes_writing', 'specializes_speaking')
        }),
        ('Employment', {
            'fields': ('employment_type', 'date_joined', 'is_active')
        }),
        ('Availability', {
            'fields': ('availability_schedule',)
        }),
        ('Performance Metrics', {
            'fields': ('average_rating', 'total_classes_taught'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    inlines = [TeacherDocumentInline, TeacherHourlyRateInline]
    actions = ['activate_teachers', 'deactivate_teachers']

    def activate_teachers(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} teachers activated.')
    activate_teachers.short_description = "Activate selected teachers"

    def deactivate_teachers(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} teachers deactivated.')
    deactivate_teachers.short_description = "Deactivate selected teachers"


@admin.register(TeacherDocument)
class TeacherDocumentAdmin(admin.ModelAdmin):
    list_display = [
        'teacher', 'document_type', 'title', 'issue_date',
        'expiry_date', 'is_verified', 'uploaded_at'
    ]
    list_filter = ['document_type', 'is_verified', 'uploaded_at', 'issue_date']
    search_fields = ['teacher__full_name', 'teacher__employee_id', 'title', 'description', 'issuing_authority']
    readonly_fields = ['uploaded_at', 'updated_at']
    date_hierarchy = 'uploaded_at'

    fieldsets = (
        ('Teacher', {
            'fields': ('teacher',)
        }),
        ('Document Details', {
            'fields': ('document_type', 'title', 'description', 'document')
        }),
        ('Issue Information', {
            'fields': ('issuing_authority', 'issue_date', 'expiry_date')
        }),
        ('Verification', {
            'fields': ('is_verified', 'verified_by', 'verified_date', 'verification_notes')
        }),
        ('Metadata', {
            'fields': ('uploaded_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TeacherHourlyRate)
class TeacherHourlyRateAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'hourly_rate', 'currency', 'effective_from', 'effective_until', 'is_current', 'approval_date']
    list_filter = ['is_current', 'currency', 'effective_from']
    search_fields = ['teacher__full_name', 'teacher__employee_id', 'reason']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'effective_from'
    
    fieldsets = (
        ('Teacher', {
            'fields': ('teacher',)
        }),
        ('Rate Details', {
            'fields': ('hourly_rate', 'currency', 'effective_from', 'effective_until', 'is_current')
        }),
        ('Additional Information', {
            'fields': ('reason', 'approved_by', 'approval_date')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
