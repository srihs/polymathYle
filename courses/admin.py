from django.contrib import admin
from .models import YLELevel, Class, Unit, Lesson, Activity, Assessment


@admin.register(YLELevel)
class YLELevelAdmin(admin.ModelAdmin):
    list_display = ['name', 'short_code', 'cefr_level', 'age_range_min', 'age_range_max', 'duration_minutes', 'is_active']
    list_filter = ['is_active', 'cefr_level']
    search_fields = ['name', 'short_code']
    ordering = ['order']


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ['class_code', 'level', 'class_name', 'teacher', 'current_enrollment', 'max_students', 'is_active']
    list_filter = ['level', 'is_active', 'start_date', 'teacher']
    search_fields = ['class_name', 'class_code', 'teacher__full_name']
    readonly_fields = ['current_enrollment', 'created_at', 'updated_at']

    fieldsets = (
        ('Class Information', {
            'fields': ('level', 'class_name', 'class_code')
        }),
        ('Teacher Assignment', {
            'fields': ('teacher',)
        }),
        ('Schedule', {
            'fields': ('schedule', 'room_number')
        }),
        ('Capacity', {
            'fields': ('max_students', 'current_enrollment')
        }),
        ('Academic Period', {
            'fields': ('start_date', 'end_date', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ['title', 'level', 'order', 'is_active']
    list_filter = ['level', 'is_active']
    search_fields = ['title', 'description']
    ordering = ['level', 'order']


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'unit', 'content_type', 'duration_minutes', 'completion_points', 'is_active']
    list_filter = ['content_type', 'is_active', 'skill_listening', 'skill_reading', 'skill_writing', 'skill_speaking']
    search_fields = ['title', 'description']
    ordering = ['unit', 'order']


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ['title', 'lesson', 'activity_type', 'max_points', 'is_active']
    list_filter = ['activity_type', 'is_active']
    search_fields = ['title', 'description']
    ordering = ['lesson', 'order']


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'assessment_type', 'unit', 'level', 'time_limit_minutes', 'max_score', 'is_active']
    list_filter = ['assessment_type', 'is_active']
    search_fields = ['title', 'description']
