from django.db import models


class SkillProgress(models.Model):
    """
    Track overall skill progress for each student at each level
    """
    SKILL_CHOICES = [
        ('LISTENING', 'Listening'),
        ('READING', 'Reading'),
        ('WRITING', 'Writing'),
        ('SPEAKING', 'Speaking'),
    ]

    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='skill_progress')
    level = models.ForeignKey('courses.YLELevel', on_delete=models.CASCADE)
    skill = models.CharField(max_length=20, choices=SKILL_CHOICES)

    # Progress metrics
    mastery_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    total_activities_completed = models.IntegerField(default=0)
    total_activities_available = models.IntegerField(default=0)

    # Score tracking
    average_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    highest_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    # Time tracking
    total_time_spent_minutes = models.IntegerField(default=0)

    last_activity_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['student', 'level', 'skill']
        ordering = ['student', 'level', 'skill']

    def __str__(self):
        return f"{self.student.full_name} - {self.level.short_code} - {self.skill}: {self.mastery_percentage}%"

    def update_progress(self):
        """Recalculate progress based on completed activities"""
        if self.total_activities_available > 0:
            self.mastery_percentage = (
                self.total_activities_completed / self.total_activities_available
            ) * 100
        self.save()


class UnitProgress(models.Model):
    """
    Track student progress through individual units
    """
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='unit_progress')
    unit = models.ForeignKey('courses.Unit', on_delete=models.CASCADE)

    # Status
    STATUS_CHOICES = [
        ('NOT_STARTED', 'Not Started'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='NOT_STARTED'
    )

    # Progress tracking
    lessons_completed = models.IntegerField(default=0)
    total_lessons = models.IntegerField(default=0)
    completion_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    # Scores
    unit_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Dates
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['student', 'unit']
        ordering = ['student', 'unit']

    def __str__(self):
        return f"{self.student.full_name} - {self.unit.title}: {self.completion_percentage}%"


class LessonProgress(models.Model):
    """
    Track individual lesson completion and performance
    """
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='lesson_progress')
    lesson = models.ForeignKey('courses.Lesson', on_delete=models.CASCADE)

    # Completion status
    is_completed = models.BooleanField(default=False)
    completion_date = models.DateTimeField(null=True, blank=True)

    # Attempt tracking
    attempts_count = models.IntegerField(default=0)

    # Time spent
    time_spent_minutes = models.IntegerField(default=0)

    # Activities
    activities_completed = models.IntegerField(default=0)
    total_activities = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['student', 'lesson']
        ordering = ['student', 'lesson']
        verbose_name_plural = 'Lesson Progress Records'

    def __str__(self):
        status = "✓" if self.is_completed else "○"
        return f"{status} {self.student.full_name} - {self.lesson.title}"


class ActivityAttempt(models.Model):
    """
    Individual attempts at activities
    """
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='activity_attempts')
    activity = models.ForeignKey('courses.Activity', on_delete=models.CASCADE)

    # Attempt data
    attempt_number = models.IntegerField(default=1)
    student_answers = models.JSONField()  # Store student's answers/work

    # Scoring
    score = models.DecimalField(max_digits=5, decimal_places=2)
    max_score = models.DecimalField(max_digits=5, decimal_places=2)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)

    # Skills addressed
    SKILL_CHOICES = [
        ('LISTENING', 'Listening'),
        ('READING', 'Reading'),
        ('WRITING', 'Writing'),
        ('SPEAKING', 'Speaking'),
    ]
    skill_type = models.CharField(max_length=20, choices=SKILL_CHOICES, null=True, blank=True)

    # Timing
    time_taken_seconds = models.IntegerField(default=0)

    # Completion
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.full_name} - {self.activity.title} - Attempt {self.attempt_number}: {self.percentage}%"


class AssessmentResult(models.Model):
    """
    Store results from unit/level assessments (Internal Exam Marks)
    """
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='assessment_results')
    assessment = models.ForeignKey('courses.Assessment', on_delete=models.CASCADE)

    # Overall score
    total_score = models.DecimalField(max_digits=5, decimal_places=2)
    max_score = models.DecimalField(max_digits=5, decimal_places=2)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)

    # Skill breakdown (4 skills)
    listening_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    reading_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    writing_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    speaking_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Status
    passed = models.BooleanField(default=False)

    # Attempt tracking
    attempt_number = models.IntegerField(default=1)

    # Answers
    student_answers = models.JSONField()

    # Timing
    time_taken_minutes = models.IntegerField()

    # Completion
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-completed_at']

    def __str__(self):
        pass_fail = "PASS" if self.passed else "FAIL"
        return f"{self.student.full_name} - {self.assessment.title}: {self.percentage}% ({pass_fail})"
