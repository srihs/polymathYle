from django.contrib import admin
from .models import SkillProgress, UnitProgress, LessonProgress, ActivityAttempt, AssessmentResult


@admin.register(SkillProgress)
class SkillProgressAdmin(admin.ModelAdmin):
    list_display = ['student', 'level', 'skill', 'mastery_percentage', 'average_score', 'last_activity_date']
    list_filter = ['skill', 'level']
    search_fields = ['student__full_name', 'student__admission_number']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(UnitProgress)
class UnitProgressAdmin(admin.ModelAdmin):
    list_display = ['student', 'unit', 'status', 'completion_percentage', 'lessons_completed', 'total_lessons']
    list_filter = ['status', 'unit__level']
    search_fields = ['student__full_name', 'unit__title']
    readonly_fields = ['updated_at']


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ['student', 'lesson', 'is_completed', 'activities_completed', 'total_activities', 'time_spent_minutes']
    list_filter = ['is_completed', 'lesson__unit__level']
    search_fields = ['student__full_name', 'lesson__title']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ActivityAttempt)
class ActivityAttemptAdmin(admin.ModelAdmin):
    list_display = ['student', 'activity', 'attempt_number', 'percentage', 'skill_type', 'is_completed', 'completed_at']
    list_filter = ['skill_type', 'is_completed', 'completed_at']
    search_fields = ['student__full_name', 'activity__title']
    readonly_fields = ['created_at']
    date_hierarchy = 'completed_at'


@admin.register(AssessmentResult)
class AssessmentResultAdmin(admin.ModelAdmin):
    list_display = [
        'student', 'assessment', 'percentage', 'passed',
        'listening_score', 'reading_score', 'writing_score', 'speaking_score',
        'completed_at'
    ]
    list_filter = ['passed', 'assessment__assessment_type', 'completed_at']
    search_fields = ['student__full_name', 'assessment__title']
    readonly_fields = ['completed_at']
    date_hierarchy = 'completed_at'

    fieldsets = (
        ('Student & Assessment', {
            'fields': ('student', 'assessment', 'attempt_number')
        }),
        ('Overall Score', {
            'fields': ('total_score', 'max_score', 'percentage', 'passed')
        }),
        ('Skill Breakdown (4 Skills)', {
            'fields': ('listening_score', 'reading_score', 'writing_score', 'speaking_score')
        }),
        ('Details', {
            'fields': ('student_answers', 'time_taken_minutes', 'completed_at')
        }),
    )
