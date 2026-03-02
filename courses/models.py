from django.db import models
from django.contrib.auth.models import User


class YLELevel(models.Model):
    """
    Three main YLE levels: Starters, Movers, Flyers
    """
    name = models.CharField(max_length=50)  # e.g., "Pre A1 Starters"
    short_code = models.CharField(max_length=20, unique=True)  # e.g., "STARTERS"
    cefr_level = models.CharField(max_length=10, blank=True)  # e.g., "Pre A1", "A1", "A2" - Optional field
    description = models.TextField()
    age_range_min = models.IntegerField()  # Minimum age
    age_range_max = models.IntegerField()  # Maximum age
    duration_minutes = models.IntegerField()  # Total exam duration
    order = models.IntegerField(default=0)  # Display order

    # Visual elements
    icon = models.CharField(max_length=100)
    color_theme = models.CharField(max_length=20)  # Hex color for UI

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        if self.cefr_level:
            return f"{self.name} ({self.cefr_level})"
        return self.name


class Class(models.Model):
    """
    Parallel class sections for each YLE level
    One level can have multiple classes (e.g., Starters Class A, Starters Class B)
    IMPORTANT: This is for class allocation - students are assigned to specific classes
    """
    level = models.ForeignKey(YLELevel, on_delete=models.CASCADE, related_name='classes')

    # Class identification
    class_name = models.CharField(max_length=100)  # e.g., "Class A", "Morning Batch"
    class_code = models.CharField(max_length=20, unique=True)  # e.g., "START-A", "MOV-B"

    # Teacher assignment
    teacher = models.ForeignKey(
        'teachers.Teacher',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='classes_taught'
    )

    # Schedule
    # Format: [{day: 'Monday', time: '10:00', duration_minutes: 90}, ...]
    schedule = models.JSONField(
        default=list,
        help_text="Class schedule: day, time, duration"
    )

    # Capacity
    max_students = models.IntegerField(default=25)
    current_enrollment = models.IntegerField(default=0)

    # Room/Location
    room_number = models.CharField(max_length=50, blank=True)

    # Academic period
    start_date = models.DateField()
    end_date = models.DateField()

    # Status
    is_active = models.BooleanField(default=True)

    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['level', 'class_name']
        verbose_name_plural = 'Classes'

    def __str__(self):
        return f"{self.level.short_code} - {self.class_name}"

    def is_full(self):
        """Check if class has reached capacity"""
        return self.current_enrollment >= self.max_students

    def get_enrolled_students(self):
        """Get all students enrolled in this class"""
        return self.enrolled_students.filter(is_active=True)


class Unit(models.Model):
    """
    Units within each YLE level (dynamic - can add/remove)
    Example: Unit 1: Family, Unit 2: School, Unit 3: Animals
    """
    level = models.ForeignKey(YLELevel, on_delete=models.CASCADE, related_name='units')
    title = models.CharField(max_length=200)
    description = models.TextField()
    order = models.IntegerField(default=0)

    # Prerequisites
    requires_completion_of = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='unlocks'
    )

    # Visual
    thumbnail = models.ImageField(upload_to='unit_thumbnails/', blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['level', 'order']
        unique_together = ['level', 'order']

    def __str__(self):
        return f"{self.level.short_code} - {self.title}"


class Lesson(models.Model):
    """
    Individual lessons within units
    Each lesson focuses on one or more of the 4 skills
    """
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    description = models.TextField()
    order = models.IntegerField(default=0)

    # Skills covered in this lesson
    skill_listening = models.BooleanField(default=False)
    skill_reading = models.BooleanField(default=False)
    skill_writing = models.BooleanField(default=False)
    skill_speaking = models.BooleanField(default=False)

    # Content
    CONTENT_TYPE_CHOICES = [
        ('VIDEO', 'Video Lesson'),
        ('INTERACTIVE', 'Interactive Activity'),
        ('READ', 'Reading Material'),
        ('AUDIO', 'Audio Lesson'),
        ('GAME', 'Educational Game'),
    ]
    content_type = models.CharField(max_length=50, choices=CONTENT_TYPE_CHOICES)
    content_url = models.URLField(blank=True)  # External content
    content_file = models.FileField(upload_to='lesson_content/', blank=True)
    content_html = models.TextField(blank=True)  # Embedded HTML content

    # Estimated duration
    duration_minutes = models.IntegerField(default=15)

    # Points for completion
    completion_points = models.IntegerField(default=10)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['unit', 'order']
        unique_together = ['unit', 'order']

    def __str__(self):
        return f"{self.unit.title} - {self.title}"


class Activity(models.Model):
    """
    Interactive activities within lessons
    Examples: coloring, matching, find differences, drag-drop
    """
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='activities')
    title = models.CharField(max_length=200)
    description = models.TextField()

    ACTIVITY_TYPE_CHOICES = [
        ('COLORING', 'Coloring Activity'),
        ('MATCHING', 'Matching Pairs'),
        ('DIFFERENCES', 'Find Differences'),
        ('DRAG_DROP', 'Drag and Drop'),
        ('MULTIPLE_CHOICE', 'Multiple Choice'),
        ('FILL_BLANK', 'Fill in the Blanks'),
        ('WORD_PUZZLE', 'Word Puzzle'),
        ('LISTENING_COMPREHENSION', 'Listening Comprehension'),
    ]
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPE_CHOICES)

    # Activity data (JSON for flexibility)
    activity_data = models.JSONField()  # Store questions, answers, images, etc.

    # Points
    max_points = models.IntegerField(default=10)

    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['lesson', 'order']
        verbose_name_plural = 'Activities'

    def __str__(self):
        return f"{self.lesson.title} - {self.title}"


class Assessment(models.Model):
    """
    End-of-unit or end-of-level assessments
    """
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, null=True, blank=True, related_name='assessments')
    level = models.ForeignKey(YLELevel, on_delete=models.CASCADE, null=True, blank=True, related_name='assessments')

    title = models.CharField(max_length=200)
    description = models.TextField()

    ASSESSMENT_TYPE_CHOICES = [
        ('UNIT_TEST', 'Unit Test'),
        ('LEVEL_TEST', 'Level Final Exam'),
        ('PRACTICE_TEST', 'Practice Test'),
    ]
    assessment_type = models.CharField(max_length=50, choices=ASSESSMENT_TYPE_CHOICES)

    # Time limit
    time_limit_minutes = models.IntegerField(default=30)

    # Skills tested
    tests_listening = models.BooleanField(default=True)
    tests_reading = models.BooleanField(default=True)
    tests_writing = models.BooleanField(default=True)
    tests_speaking = models.BooleanField(default=False)  # Separate speaking assessment

    # Passing criteria
    passing_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=60.00)

    # Assessment data
    questions_data = models.JSONField()  # Store all questions and answers

    max_score = models.IntegerField(default=100)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.unit:
            return f"{self.unit.title} - {self.title}"
        return f"{self.level.name} - {self.title}"
