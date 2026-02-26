from django.db import models
from django.contrib.auth.models import User
from datetime import date


class Teacher(models.Model):
    """
    Teacher profile for instructors who teach YLE classes
    """
    # Link to Django User for authentication
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')

    # BASIC INFO
    full_name = models.CharField(max_length=200)
    employee_id = models.CharField(max_length=50, unique=True)

    # CONTACT
    contact_number = models.CharField(max_length=20)
    email = models.EmailField()

    # PROFILE
    profile_picture = models.ImageField(upload_to='teacher_profiles/', blank=True)
    bio = models.TextField(blank=True, help_text="Short biography or introduction")

    # QUALIFICATIONS
    qualifications = models.TextField(
        blank=True,
        help_text="Educational qualifications and certifications (e.g., CELTA, TESOL)"
    )
    years_of_experience = models.IntegerField(default=0)

    # SPECIALIZATIONS - YLE Levels
    teaches_starters = models.BooleanField(default=False)
    teaches_movers = models.BooleanField(default=False)
    teaches_flyers = models.BooleanField(default=False)

    # EMPLOYMENT
    date_joined = models.DateField()
    is_active = models.BooleanField(default=True)

    EMPLOYMENT_TYPE_CHOICES = [
        ('FULL_TIME', 'Full Time'),
        ('PART_TIME', 'Part Time'),
        ('CONTRACT', 'Contract'),
    ]
    employment_type = models.CharField(
        max_length=20,
        choices=EMPLOYMENT_TYPE_CHOICES,
        default='FULL_TIME'
    )

    # AVAILABILITY
    availability_schedule = models.JSONField(
        default=dict,
        blank=True,
        help_text="Weekly availability schedule"
    )

    # PERFORMANCE METRICS (optional)
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        help_text="Average student rating out of 5.00"
    )
    total_classes_taught = models.IntegerField(default=0)

    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['full_name']

    def __str__(self):
        return f"{self.full_name} ({self.employee_id})"

    def get_specializations(self):
        """Return list of levels teacher can teach"""
        levels = []
        if self.teaches_starters:
            levels.append('Starters')
        if self.teaches_movers:
            levels.append('Movers')
        if self.teaches_flyers:
            levels.append('Flyers')
        return levels

    def get_current_hourly_rate(self):
        """Get the most recent active hourly rate"""
        current_rate = self.hourly_rates.filter(is_current=True).first()
        return current_rate.hourly_rate if current_rate else None


class TeacherDocument(models.Model):
    """
    Store teacher's CV, certificates, and other documents
    """
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='documents')

    DOCUMENT_TYPE_CHOICES = [
        ('CV', 'Curriculum Vitae / Resume'),
        ('DEGREE', 'Degree Certificate'),
        ('DIPLOMA', 'Diploma / Certificate'),
        ('TEACHING_CERT', 'Teaching Certification (CELTA, TESOL, etc.)'),
        ('ID_PROOF', 'ID Proof / Passport'),
        ('EXPERIENCE_LETTER', 'Experience Letter'),
        ('POLICE_CLEARANCE', 'Police Clearance'),
        ('OTHER', 'Other Document'),
    ]
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPE_CHOICES)

    # Document details
    title = models.CharField(max_length=200, help_text="E.g., 'Bachelor of Arts in English', 'CELTA Certificate'")
    description = models.TextField(blank=True, help_text="Additional details about the document")

    # File upload
    document = models.FileField(
        upload_to='teacher_documents/',
        help_text="Upload PDF, DOC, DOCX, or image files"
    )

    # Issue details (for certificates)
    issuing_authority = models.CharField(max_length=200, blank=True, help_text="E.g., 'Cambridge Assessment', 'University of Colombo'")
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True, help_text="If applicable (e.g., police clearance)")

    # Verification
    is_verified = models.BooleanField(default=False, help_text="Mark as verified after review")
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_teacher_documents'
    )
    verified_date = models.DateTimeField(null=True, blank=True)
    verification_notes = models.TextField(blank=True)

    # Meta
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.teacher.full_name} - {self.get_document_type_display()}: {self.title}"

    def is_expired(self):
        """Check if document has expired"""
        if self.expiry_date:
            return date.today() > self.expiry_date
        return False


class TeacherHourlyRate(models.Model):
    """
    Track teacher hourly rate history
    Maintains all historical rates for audit and payment calculation
    """
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='hourly_rates')

    # Rate details
    hourly_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Hourly rate in LKR or currency"
    )

    CURRENCY_CHOICES = [
        ('LKR', 'Sri Lankan Rupee'),
        ('USD', 'US Dollar'),
        ('GBP', 'British Pound'),
        ('EUR', 'Euro'),
    ]
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='LKR')

    # Effective period
    effective_from = models.DateField(help_text="Date from which this rate is applicable")
    effective_until = models.DateField(null=True, blank=True, help_text="Leave blank if current rate")

    # Status
    is_current = models.BooleanField(
        default=False,
        help_text="Only one rate should be marked as current"
    )

    # Reason for change
    reason = models.TextField(
        blank=True,
        help_text="Reason for rate change (e.g., 'Annual increment', 'Performance bonus', 'Promotion')"
    )

    # Approval
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_teacher_rates'
    )
    approval_date = models.DateField(null=True, blank=True)

    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-effective_from']
        unique_together = ['teacher', 'effective_from']

    def __str__(self):
        status = " (Current)" if self.is_current else ""
        return f"{self.teacher.full_name} - {self.currency} {self.hourly_rate}/hour from {self.effective_from}{status}"

    def save(self, *args, **kwargs):
        # If this rate is marked as current, unmark all other rates for this teacher
        if self.is_current:
            TeacherHourlyRate.objects.filter(
                teacher=self.teacher,
                is_current=True
            ).exclude(pk=self.pk).update(is_current=False)

        # If effective_until is not set and this is not marked as current, set is_current to True
        if not self.effective_until and not self.is_current:
            self.is_current = True

        super().save(*args, **kwargs)
