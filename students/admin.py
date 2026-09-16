from django.contrib import admin
from .models import (
    Application, Attendance, BaselineTest, ClassTransferRequest, Guardian, Student, StudentBadge,
    StudentClassHistory,
)


class BaselineTestInline(admin.StackedInline):
    model = BaselineTest
    extra = 0
    readonly_fields = ('total_score', 'percentage', 'recommended_level', 'created_at', 'updated_at')


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'full_name', 'admission_number', 'status', 'application_date', 'application_type', 'uploaded_by')
    list_filter = ('status', 'application_type', 'gender', 'application_date', 'uploaded_by')
    search_fields = ('full_name', 'name_with_initials', 'admission_number', 'reference_number', 'student_email')
    readonly_fields = ('age', 'uploaded_by', 'created_at', 'updated_at')
    inlines = [BaselineTestInline]
    fieldsets = (
        ('Application Info', {
            'fields': ('reference_number', 'admission_number', 'receipt_number', 'status', 'application_type',
                      'uploaded_by', 'created_at', 'processing_date', 'processed_by')
        }),
        ('Student Personal Information', {
            'fields': ('name_with_initials', 'full_name', 'nationality', 'date_of_birth',
                      'age', 'gender', 'student_email', 'student_nic', 'current_school', 'siblings_info')
        }),
        ('Family Information', {
            'fields': ('mother_name', 'mother_contact_number', 'mother_occupation',
                      'father_name', 'father_contact_number', 'father_occupation')
        }),
        ('Contact Information', {
            'fields': ('home_address', 'whatsapp_number', 'primary_contact_email')
        }),
        ('Class Preferences', {
            'fields': ('schedule_preferences', 'selected_class_day')
        }),
        ('Terms and Conditions', {
            'fields': ('terms_accepted', 'terms_accepted_date', 'guardian_signature_date', 'signature_image')
        }),
        ('Office Use', {
            'fields': ('special_comments', 'authorized_by', 'authorization_date', 'application_form_scan')
        }),
    )


@admin.register(BaselineTest)
class BaselineTestAdmin(admin.ModelAdmin):
    list_display = ('application', 'test_date', 'percentage', 'recommended_level', 'assigned_level')
    list_filter = ('recommended_level', 'assigned_level', 'test_date')
    search_fields = ('application__full_name', 'application__admission_number')
    readonly_fields = ('total_score', 'percentage', 'recommended_level', 'created_at', 'updated_at')
    fieldsets = (
        ('Test Info', {
            'fields': ('application', 'test_date', 'tested_by')
        }),
        ('Scores', {
            'fields': ('listening_score', 'reading_score', 'writing_score', 'speaking_score',
                      'total_score', 'percentage')
        }),
        ('Level Assignment', {
            'fields': ('recommended_level', 'assigned_level', 'notes')
        }),
    )


@admin.register(Guardian)
class GuardianAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'relationship', 'contact_number', 'email')
    list_filter = ('relationship',)
    search_fields = ('full_name', 'email', 'contact_number')


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('admission_number', 'full_name', 'current_level', 'is_active', 'enrollment_date')
    list_filter = ('current_level', 'is_active', 'gender')
    search_fields = ('full_name', 'admission_number', 'student_email')

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        # Once assigned, a class changes only through a transfer request or promotion
        if obj and obj.assigned_class_id:
            readonly.append('assigned_class')
        return readonly


@admin.register(ClassTransferRequest)
class ClassTransferRequestAdmin(admin.ModelAdmin):
    list_display = ('student', 'from_class', 'to_class', 'status', 'requested_by', 'requested_at', 'decided_by')
    list_filter = ('status',)
    search_fields = ('student__full_name', 'student__admission_number', 'reason')
    # Status changes must go through the app so the student is moved and history recorded
    readonly_fields = ('student', 'from_class', 'to_class', 'status', 'requested_by', 'requested_at',
                       'decided_by', 'decided_at')

    def has_add_permission(self, request):
        return False


@admin.register(StudentClassHistory)
class StudentClassHistoryAdmin(admin.ModelAdmin):
    list_display = ('student', 'change_type', 'from_class', 'to_class', 'from_level', 'to_level', 'changed_by', 'changed_at')
    list_filter = ('change_type',)
    search_fields = ('student__full_name', 'student__admission_number')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(StudentBadge)
class StudentBadgeAdmin(admin.ModelAdmin):
    list_display = ('student', 'badge_name', 'badge_type', 'earned_date')
    list_filter = ('badge_type', 'skill_type')
    search_fields = ('student__full_name', 'badge_name')


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'date', 'status', 'class_session')
    list_filter = ('status', 'date')
    search_fields = ('student__full_name',)
