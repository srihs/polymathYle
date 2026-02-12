from django.db import models
import random
from datetime import datetime


class Certificate(models.Model):
    """
    Certificates awarded to students
    """
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='certificates')

    CERTIFICATE_TYPE_CHOICES = [
        ('LEVEL_COMPLETE', 'Level Completion'),
        ('SKILL_MASTERY', 'Skill Mastery'),
        ('PERFECT_SCORE', 'Perfect Score Achievement'),
        ('PARTICIPATION', 'Participation Award'),
    ]
    certificate_type = models.CharField(max_length=50, choices=CERTIFICATE_TYPE_CHOICES)

    # Associated level (if level completion certificate)
    level = models.ForeignKey('courses.YLELevel', on_delete=models.CASCADE, null=True, blank=True)

    # Certificate details
    title = models.CharField(max_length=200)
    description = models.TextField()

    # Visual elements
    template_name = models.CharField(max_length=100)  # Template to use
    shields_earned = models.IntegerField(default=0)  # YLE uses shields instead of grades

    # Skill breakdown (for level completion certificates)
    listening_shields = models.IntegerField(default=0)  # Out of 5
    reading_shields = models.IntegerField(default=0)   # Out of 5
    writing_shields = models.IntegerField(default=0)   # Out of 5
    speaking_shields = models.IntegerField(default=0)  # Out of 5

    # Certificate number (unique identifier)
    certificate_number = models.CharField(max_length=50, unique=True)

    # File storage
    certificate_pdf = models.FileField(upload_to='certificates/', blank=True)

    # Dates
    issue_date = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Verification
    is_verified = models.BooleanField(default=True)

    class Meta:
        ordering = ['-issue_date']

    def __str__(self):
        return f"{self.student.full_name} - {self.title} ({self.certificate_number})"

    def save(self, *args, **kwargs):
        if not self.certificate_number:
            self.certificate_number = self.generate_certificate_number()
        super().save(*args, **kwargs)

    def generate_certificate_number(self):
        """Generate unique certificate number"""
        year = datetime.now().year
        random_num = random.randint(1000, 9999)
        return f"YLE-{year}-{self.student.id}-{random_num}"

    def calculate_total_shields(self):
        """Calculate total shields from 4 skills"""
        return (
            self.listening_shields +
            self.reading_shields +
            self.writing_shields +
            self.speaking_shields
        )


class CertificateTemplate(models.Model):
    """
    Certificate templates for different achievement types
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()

    TEMPLATE_TYPE_CHOICES = [
        ('STARTERS', 'Pre A1 Starters'),
        ('MOVERS', 'A1 Movers'),
        ('FLYERS', 'A2 Flyers'),
        ('SKILL', 'Skill Mastery'),
        ('ACHIEVEMENT', 'Special Achievement'),
    ]
    template_type = models.CharField(max_length=50, choices=TEMPLATE_TYPE_CHOICES)

    # Template files
    html_template = models.TextField()  # HTML template with placeholders
    css_styles = models.TextField(blank=True)

    # Visual elements
    background_image = models.ImageField(upload_to='certificate_templates/', blank=True)
    logo_image = models.ImageField(upload_to='certificate_templates/', blank=True)

    # Layout settings (JSON for flexibility)
    layout_settings = models.JSONField(default=dict)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.template_type})"


class Achievement(models.Model):
    """
    Special achievements/milestones (beyond regular certificates)
    """
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='achievements')

    ACHIEVEMENT_TYPE_CHOICES = [
        ('FIRST_LESSON', 'First Lesson Complete'),
        ('PERFECT_UNIT', 'Perfect Unit Score'),
        ('SPEED_LEARNER', 'Speed Learner'),
        ('CONSISTENT_LEARNER', '7-Day Streak'),
        ('HELPER', 'Helped Others'),
        ('ALL_SKILLS', 'All Skills Mastered'),
    ]
    achievement_type = models.CharField(max_length=50, choices=ACHIEVEMENT_TYPE_CHOICES)

    title = models.CharField(max_length=200)
    description = models.TextField()
    icon = models.CharField(max_length=100)  # Emoji or icon reference

    points_awarded = models.IntegerField(default=0)

    earned_date = models.DateTimeField(auto_now_add=True)

    # Related data
    related_unit = models.ForeignKey('courses.Unit', on_delete=models.SET_NULL, null=True, blank=True)
    related_lesson = models.ForeignKey('courses.Lesson', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.student.full_name} - {self.title}"
