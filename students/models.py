from django.db import models
from django.contrib.auth.models import User
from datetime import date




class Application(models.Model):
    """
    Student application form - supports both online and offline submissions
    Based on Polymath College application form structure
    """
    # APPLICATION DETAILS
    admission_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    application_date = models.DateField(auto_now_add=True)
    receipt_number = models.CharField(max_length=50, blank=True)

    # APPLICATION STATUS
    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('WAITLIST', 'Waitlist'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    APPLICATION_TYPE_CHOICES = [
        ('ONLINE', 'Online Application'),
        ('OFFLINE', 'Paper Application'),
    ]
    application_type = models.CharField(
        max_length=20,
        choices=APPLICATION_TYPE_CHOICES,
        default='ONLINE'
    )

    # STUDENT PERSONAL INFORMATION
    name_with_initials = models.CharField(max_length=200)
    full_name = models.CharField(max_length=200)
    nationality = models.CharField(max_length=100, default='Sinhalese')
    date_of_birth = models.DateField()
    age = models.IntegerField(blank=True, null=True)  # Auto-calculated

    GENDER_CHOICES = [
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
    ]
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)

    student_email = models.EmailField(blank=True)
    student_nic = models.CharField(max_length=20, blank=True, verbose_name="NIC")
    current_school = models.CharField(max_length=200, blank=True)

    # Siblings information
    siblings_info = models.TextField(blank=True, help_text="Names and levels of siblings currently attending")

    # FAMILY INFORMATION - MOTHER
    mother_name = models.CharField(max_length=200)
    mother_contact_number = models.CharField(max_length=20)
    mother_occupation = models.CharField(max_length=100, blank=True)

    # FAMILY INFORMATION - FATHER
    father_name = models.CharField(max_length=200)
    father_contact_number = models.CharField(max_length=20)
    father_occupation = models.CharField(max_length=100, blank=True)

    # CONTACT INFORMATION
    home_address = models.TextField()
    whatsapp_number = models.CharField(max_length=20)
    primary_contact_email = models.EmailField()  # Usually parent email

    # CLASS SCHEDULE PREFERENCES
    # Stored as JSON: {day: {time_slot: class_type}}
    schedule_preferences = models.JSONField(
        default=dict,
        blank=True,
        help_text="Preferred class days and times"
    )

    # SELECTED CLASS AND DAY (After approval)
    selected_class_day = models.CharField(max_length=100, blank=True)

    # TERMS AND CONDITIONS
    terms_accepted = models.BooleanField(default=False)
    terms_accepted_date = models.DateTimeField(blank=True, null=True)
    signature_image = models.ImageField(upload_to='signatures/', blank=True)  # For online applications

    # SPECIAL COMMENTS
    special_comments = models.TextField(blank=True)

    # OFFICE USE
    authorized_by = models.CharField(max_length=100, blank=True)
    authorization_date = models.DateField(blank=True, null=True)

    # DOCUMENTS
    application_form_scan = models.FileField(upload_to='applications/scans/', blank=True)

    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-application_date']

    def __str__(self):
        return f"{self.full_name} - {self.admission_number or 'Pending'} ({self.status})"

    def calculate_age(self):
        """Auto-calculate age from date of birth"""
        today = date.today()
        age = today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
        return age

    def save(self, *args, **kwargs):
        # Auto-calculate age
        if self.date_of_birth:
            self.age = self.calculate_age()

        # Generate admission number if approved and not set
        if self.status == 'APPROVED' and not self.admission_number:
            self.admission_number = self.generate_admission_number()

        super().save(*args, **kwargs)

    def generate_admission_number(self):
        """Generate unique admission number"""
        from datetime import datetime
        year = datetime.now().year
        # Format: FCE-YEAR-XXXX
        last_app = Application.objects.filter(
            admission_number__startswith=f'FCE-{year}'
        ).order_by('-admission_number').first()

        if last_app and last_app.admission_number:
            last_num = int(last_app.admission_number.split('-')[-1])
            new_num = last_num + 1
        else:
            new_num = 1

        return f'FCE-{year}-{new_num:04d}'


class Guardian(models.Model):
    """
    Parent/Guardian information - separate model for flexibility
    One guardian can have multiple students
    """
    # GUARDIAN DETAILS
    full_name = models.CharField(max_length=200)

    RELATIONSHIP_CHOICES = [
        ('MOTHER', 'Mother'),
        ('FATHER', 'Father'),
        ('GUARDIAN', 'Legal Guardian'),
    ]
    relationship = models.CharField(
        max_length=20,
        choices=RELATIONSHIP_CHOICES
    )

    # CONTACT
    contact_number = models.CharField(max_length=20)
    whatsapp_number = models.CharField(max_length=20, blank=True)
    email = models.EmailField()

    # ADDITIONAL INFO
    occupation = models.CharField(max_length=100, blank=True)

    # LOGIN (For parent portal access)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='guardian_profile'
    )

    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.full_name} ({self.relationship})"


class Student(models.Model):
    """
    Enrolled student profile - created after application approval
    """
    # Link to approved application
    application = models.OneToOneField(
        Application,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='enrolled_student'
    )

    # STUDENT LOGIN
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # GUARDIANS (Multiple guardians possible)
    guardians = models.ManyToManyField(Guardian, related_name='students')

    # BASIC INFO (copied from application)
    admission_number = models.CharField(max_length=50, unique=True)
    full_name = models.CharField(max_length=200)
    name_with_initials = models.CharField(max_length=200)
    date_of_birth = models.DateField()
    age = models.IntegerField()

    GENDER_CHOICES = [
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
    ]
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    nationality = models.CharField(max_length=100)

    # CONTACT
    student_email = models.EmailField(blank=True)
    home_address = models.TextField()
    primary_contact_number = models.CharField(max_length=20)
    whatsapp_number = models.CharField(max_length=20, blank=True)

    # PROFILE
    profile_picture = models.ImageField(upload_to='student_profiles/', blank=True)

    # CURRENT SCHOOL
    current_school = models.CharField(max_length=200, blank=True)

    # YLE LEVEL ASSIGNMENT
    LEVEL_CHOICES = [
        ('STARTERS', 'Pre A1 Starters'),
        ('MOVERS', 'A1 Movers'),
        ('FLYERS', 'A2 Flyers'),
    ]
    current_level = models.CharField(
        max_length=20,
        choices=LEVEL_CHOICES,
        default='STARTERS'
    )

    # ENROLLMENT INFO
    enrollment_date = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    # CLASS ALLOCATION
    assigned_class = models.ForeignKey(
        'courses.Class',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='enrolled_students'
    )

    # GAMIFICATION
    avatar = models.CharField(max_length=50, blank=True)
    total_points = models.IntegerField(default=0)
    streak_days = models.IntegerField(default=0)
    last_activity = models.DateTimeField(auto_now=True)

    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-enrollment_date']

    def __str__(self):
        return f"{self.admission_number} - {self.full_name} ({self.current_level})"

    def calculate_age(self):
        """Calculate current age from date of birth"""
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )

    def update_age(self):
        """Update age field"""
        self.age = self.calculate_age()
        self.save()


class StudentBadge(models.Model):
    """
    Badges/achievements earned by students
    SEPARATE MODEL - Students can earn multiple badges as they progress through
    different YLE levels (Starters, Movers, Flyers) and complete various exams
    """
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='badges')

    # Badge details
    badge_name = models.CharField(max_length=100)

    BADGE_TYPE_CHOICES = [
        ('SKILL_MASTERY', 'Skill Mastery'),
        ('LEVEL_COMPLETE', 'Level Completion'),
        ('EXAM_PASSED', 'Exam Passed'),
        ('PERFECT_SCORE', 'Perfect Score'),
        ('STREAK', 'Daily Streak'),
        ('PARTICIPATION', 'Participation'),
    ]
    badge_type = models.CharField(
        max_length=50,
        choices=BADGE_TYPE_CHOICES
    )
    badge_icon = models.CharField(max_length=100)
    description = models.TextField()

    # Linked to specific level/exam (optional - for level completion badges)
    level = models.ForeignKey(
        'courses.YLELevel',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='badges'
    )

    # Skill-specific badges (optional)
    SKILL_CHOICES = [
        ('LISTENING', 'Listening'),
        ('READING', 'Reading'),
        ('WRITING', 'Writing'),
        ('SPEAKING', 'Speaking'),
    ]
    skill_type = models.CharField(
        max_length=20,
        choices=SKILL_CHOICES,
        blank=True,
        null=True
    )

    # Award info
    earned_date = models.DateTimeField(auto_now_add=True)
    points_awarded = models.IntegerField(default=0)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-earned_date']

    def __str__(self):
        return f"{self.student.full_name} - {self.badge_name}"


class Attendance(models.Model):
    """
    Track student attendance for each class session
    SEPARATE MODEL - Essential for monitoring student participation
    """
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance_records')
    class_session = models.ForeignKey(
        'courses.Class',
        on_delete=models.CASCADE,
        related_name='attendance_records',
        null=True,
        blank=True
    )

    # Attendance details
    date = models.DateField()

    STATUS_CHOICES = [
        ('PRESENT', 'Present'),
        ('ABSENT', 'Absent'),
        ('LATE', 'Late'),
        ('EXCUSED', 'Excused Absence'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES
    )

    # Additional info
    arrival_time = models.TimeField(null=True, blank=True)
    notes = models.TextField(blank=True, help_text="Reason for absence/lateness")

    # Marked by
    marked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='attendance_marked'
    )
    marked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        unique_together = ['student', 'class_session', 'date']

    def __str__(self):
        return f"{self.student.full_name} - {self.date} - {self.status}"
