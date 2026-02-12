# PolymathYLE - Django Apps Structure
## Cambridge English Young Learners LMS System

---

## Overview
This document outlines the four core Django apps for the YLE Learning Management System:
1. **Students** - Student management, applications, attendance, and profiles
2. **Courses** - Dynamic course structure with YLE levels, classes, units, lessons
3. **Progress** - Skill-based progress tracking and internal exam marks (4 skills)
4. **Certification** - Achievement certificates and awards

### Model Summary by App:

**Students App (5 models):**
- Application - Online/offline application forms
- Guardian - Parent/guardian information
- Student - Enrolled student profiles
- StudentBadge - Achievement badges (separate, students earn multiple)
- Attendance - Daily attendance tracking

**Courses App (6 models):**
- YLELevel - Three levels (Starters, Movers, Flyers)
- Class - Parallel class sections (for class allocation)
- Unit - Course units within levels
- Lesson - Individual lessons
- Activity - Interactive activities
- Assessment - Unit and level exams

**Progress App (5 models):**
- SkillProgress - Overall skill tracking (4 skills)
- UnitProgress - Unit completion tracking
- LessonProgress - Lesson completion
- ActivityAttempt - Individual activity attempts
- AssessmentResult - Internal exam marks (4 skills breakdown)

**Certification App (3 models):**
- Certificate - Achievement certificates
- CertificateTemplate - Certificate designs
- Achievement - Special milestones

---

## 1. STUDENTS APP

### Purpose
Manage student profiles, authentication, enrollment, admission applications, attendance tracking, and class allocation.
Supports both manual (paper-based) and online parent applications.

### Key Features:
- Online application submission by parents
- Application approval workflow
- Multiple guardians per student
- Class allocation and tracking
- Daily attendance recording
- Achievement badges (students earn multiple as they progress through levels)

### Models

#### Application
```python
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
    status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending Review'),
            ('APPROVED', 'Approved'),
            ('REJECTED', 'Rejected'),
            ('WAITLIST', 'Waitlist'),
        ],
        default='PENDING'
    )
    application_type = models.CharField(
        max_length=20,
        choices=[
            ('ONLINE', 'Online Application'),
            ('OFFLINE', 'Paper Application'),
        ],
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
        from datetime import date
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
        import datetime
        year = datetime.datetime.now().year
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
```

#### Guardian
```python
class Guardian(models.Model):
    """
    Parent/Guardian information - separate model for flexibility
    One guardian can have multiple students
    """
    # GUARDIAN DETAILS
    full_name = models.CharField(max_length=200)
    relationship = models.CharField(
        max_length=20,
        choices=[
            ('MOTHER', 'Mother'),
            ('FATHER', 'Father'),
            ('GUARDIAN', 'Legal Guardian'),
        ]
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
```

#### Student
```python
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
    gender = models.CharField(max_length=10)
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
    current_level = models.CharField(
        max_length=20,
        choices=[
            ('STARTERS', 'Pre A1 Starters'),
            ('MOVERS', 'A1 Movers'),
            ('FLYERS', 'A2 Flyers'),
        ],
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
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )

    def update_age(self):
        """Update age field"""
        self.age = self.calculate_age()
        self.save()
```

#### StudentBadge
```python
class StudentBadge(models.Model):
    """
    Badges/achievements earned by students
    SEPARATE MODEL - Students can earn multiple badges as they progress through
    different YLE levels (Starters, Movers, Flyers) and complete various exams
    """
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='badges')

    # Badge details
    badge_name = models.CharField(max_length=100)
    badge_type = models.CharField(
        max_length=50,
        choices=[
            ('SKILL_MASTERY', 'Skill Mastery'),
            ('LEVEL_COMPLETE', 'Level Completion'),
            ('EXAM_PASSED', 'Exam Passed'),
            ('PERFECT_SCORE', 'Perfect Score'),
            ('STREAK', 'Daily Streak'),
            ('PARTICIPATION', 'Participation'),
        ]
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
    skill_type = models.CharField(
        max_length=20,
        choices=[
            ('LISTENING', 'Listening'),
            ('READING', 'Reading'),
            ('WRITING', 'Writing'),
            ('SPEAKING', 'Speaking'),
        ],
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
        level_info = f" - {self.level.short_code}" if self.level else ""
        return f"{self.student.full_name} - {self.badge_name}{level_info}"
```

#### Attendance
```python
class Attendance(models.Model):
    """
    Track student attendance for each class session
    SEPARATE MODEL - Essential for monitoring student participation
    """
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance_records')
    class_session = models.ForeignKey('courses.Class', on_delete=models.CASCADE, related_name='attendance_records')

    # Attendance details
    date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=[
            ('PRESENT', 'Present'),
            ('ABSENT', 'Absent'),
            ('LATE', 'Late'),
            ('EXCUSED', 'Excused Absence'),
        ]
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
```

### Forms Needed
- Online Application Form (for parents)
- Student Profile Edit Form
- Guardian Information Form

### Views Needed
- Online application submission (public)
- Application status check (for parents)
- Application review/approval (admin)
- Student registration (after approval)
- Student profile view/edit
- Student dashboard (showing current level, progress, badges)
- Guardian portal (view children's progress)
- Leaderboard view
- Avatar selection

### URLs
- `/apply/` - Online application form
- `/application/status/<str:reference>/` - Check application status
- `/students/register/` - Create student account (after approval)
- `/students/profile/<int:student_id>/`
- `/students/dashboard/`
- `/students/leaderboard/`
- `/students/avatar/select/`
- `/guardian/portal/` - Guardian dashboard
- `/admin/applications/review/` - Admin application review

---

## 2. COURSES APP (Dynamic)

### Purpose
Dynamic course structure for YLE levels with units, lessons, and activities.

### Models

#### YLELevel
```python
class YLELevel(models.Model):
    """
    Three main YLE levels: Starters, Movers, Flyers
    """
    name = models.CharField(max_length=50)  # e.g., "Pre A1 Starters"
    short_code = models.CharField(max_length=20, unique=True)  # e.g., "STARTERS"
    cefr_level = models.CharField(max_length=10)  # e.g., "Pre A1", "A1", "A2"
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
        return f"{self.name} ({self.cefr_level})"
```

#### Class
```python
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
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='classes_taught',
        limit_choices_to={'groups__name': 'Teachers'}
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
```

#### Unit
```python
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
```

#### Lesson
```python
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
    content_type = models.CharField(
        max_length=50,
        choices=[
            ('VIDEO', 'Video Lesson'),
            ('INTERACTIVE', 'Interactive Activity'),
            ('READ', 'Reading Material'),
            ('AUDIO', 'Audio Lesson'),
            ('GAME', 'Educational Game'),
        ]
    )
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
```

#### Activity
```python
class Activity(models.Model):
    """
    Interactive activities within lessons
    Examples: coloring, matching, find differences, drag-drop
    """
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='activities')
    title = models.CharField(max_length=200)
    description = models.TextField()

    activity_type = models.CharField(
        max_length=50,
        choices=[
            ('COLORING', 'Coloring Activity'),
            ('MATCHING', 'Matching Pairs'),
            ('DIFFERENCES', 'Find Differences'),
            ('DRAG_DROP', 'Drag and Drop'),
            ('MULTIPLE_CHOICE', 'Multiple Choice'),
            ('FILL_BLANK', 'Fill in the Blanks'),
            ('WORD_PUZZLE', 'Word Puzzle'),
            ('LISTENING_COMPREHENSION', 'Listening Comprehension'),
        ]
    )

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
```

#### Assessment
```python
class Assessment(models.Model):
    """
    End-of-unit or end-of-level assessments
    """
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, null=True, blank=True, related_name='assessments')
    level = models.ForeignKey(YLELevel, on_delete=models.CASCADE, null=True, blank=True, related_name='assessments')

    title = models.CharField(max_length=200)
    description = models.TextField()

    assessment_type = models.CharField(
        max_length=50,
        choices=[
            ('UNIT_TEST', 'Unit Test'),
            ('LEVEL_TEST', 'Level Final Exam'),
            ('PRACTICE_TEST', 'Practice Test'),
        ]
    )

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
```

### Views Needed
- Browse YLE levels
- Unit listing by level
- Lesson detail view with activities
- Activity completion handler
- Assessment taking interface
- Dynamic course content management (admin)

### URLs
- `/courses/levels/`
- `/courses/level/<str:level_code>/`
- `/courses/unit/<int:unit_id>/`
- `/courses/lesson/<int:lesson_id>/`
- `/courses/activity/<int:activity_id>/complete/`
- `/courses/assessment/<int:assessment_id>/`

---

## 3. PROGRESS APP

### Purpose
Track student progress across the 4 skills (Listening, Reading, Writing, Speaking) for each level and unit.

### Models

#### SkillProgress
```python
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
        return f"{self.student.user.get_full_name()} - {self.level.short_code} - {self.skill}: {self.mastery_percentage}%"

    def update_progress(self):
        """Recalculate progress based on completed activities"""
        # Logic to recalculate mastery_percentage
        if self.total_activities_available > 0:
            self.mastery_percentage = (
                self.total_activities_completed / self.total_activities_available
            ) * 100
        self.save()
```

#### UnitProgress
```python
class UnitProgress(models.Model):
    """
    Track student progress through individual units
    """
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='unit_progress')
    unit = models.ForeignKey('courses.Unit', on_delete=models.CASCADE)

    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('NOT_STARTED', 'Not Started'),
            ('IN_PROGRESS', 'In Progress'),
            ('COMPLETED', 'Completed'),
        ],
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
        return f"{self.student.user.get_full_name()} - {self.unit.title}: {self.completion_percentage}%"
```

#### LessonProgress
```python
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
        return f"{status} {self.student.user.get_full_name()} - {self.lesson.title}"
```

#### ActivityAttempt
```python
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
    skill_type = models.CharField(max_length=20, null=True, blank=True)

    # Timing
    time_taken_seconds = models.IntegerField(default=0)

    # Completion
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.activity.title} - Attempt {self.attempt_number}: {self.percentage}%"
```

#### AssessmentResult
```python
class AssessmentResult(models.Model):
    """
    Store results from unit/level assessments
    """
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='assessment_results')
    assessment = models.ForeignKey('courses.Assessment', on_delete=models.CASCADE)

    # Overall score
    total_score = models.DecimalField(max_digits=5, decimal_places=2)
    max_score = models.DecimalField(max_digits=5, decimal_places=2)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)

    # Skill breakdown
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
        return f"{self.student.user.get_full_name()} - {self.assessment.title}: {self.percentage}% ({pass_fail})"
```

### Views Needed
- Student progress dashboard (all skills)
- Skill-specific progress view
- Unit progress view
- Detailed activity history
- Assessment results view
- Progress reports (printable/downloadable)

### URLs
- `/progress/dashboard/`
- `/progress/skill/<str:skill_name>/`
- `/progress/unit/<int:unit_id>/`
- `/progress/activity-history/`
- `/progress/assessments/`
- `/progress/report/download/`

---

## 4. CERTIFICATION APP

### Purpose
Generate, manage, and display achievement certificates for YLE levels and milestones.

### Models

#### Certificate
```python
class Certificate(models.Model):
    """
    Certificates awarded to students
    """
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='certificates')

    certificate_type = models.CharField(
        max_length=50,
        choices=[
            ('LEVEL_COMPLETE', 'Level Completion'),
            ('SKILL_MASTERY', 'Skill Mastery'),
            ('PERFECT_SCORE', 'Perfect Score Achievement'),
            ('PARTICIPATION', 'Participation Award'),
        ]
    )

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
        return f"{self.student.user.get_full_name()} - {self.title} ({self.certificate_number})"

    def generate_certificate_number(self):
        """Generate unique certificate number"""
        import datetime
        import random
        year = datetime.datetime.now().year
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
```

#### CertificateTemplate
```python
class CertificateTemplate(models.Model):
    """
    Certificate templates for different achievement types
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()

    template_type = models.CharField(
        max_length=50,
        choices=[
            ('STARTERS', 'Pre A1 Starters'),
            ('MOVERS', 'A1 Movers'),
            ('FLYERS', 'A2 Flyers'),
            ('SKILL', 'Skill Mastery'),
            ('ACHIEVEMENT', 'Special Achievement'),
        ]
    )

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
```

#### Achievement
```python
class Achievement(models.Model):
    """
    Special achievements/milestones (beyond regular certificates)
    """
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='achievements')

    achievement_type = models.CharField(
        max_length=50,
        choices=[
            ('FIRST_LESSON', 'First Lesson Complete'),
            ('PERFECT_UNIT', 'Perfect Unit Score'),
            ('SPEED_LEARNER', 'Speed Learner'),
            ('CONSISTENT_LEARNER', '7-Day Streak'),
            ('HELPER', 'Helped Others'),
            ('ALL_SKILLS', 'All Skills Mastered'),
        ]
    )

    title = models.CharField(max_length=200)
    description = models.TextField()
    icon = models.CharField(max_length=100)  # Emoji or icon reference

    points_awarded = models.IntegerField(default=0)

    earned_date = models.DateTimeField(auto_now_add=True)

    # Related data
    related_unit = models.ForeignKey('courses.Unit', on_delete=models.SET_NULL, null=True, blank=True)
    related_lesson = models.ForeignKey('courses.Lesson', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.title}"
```

### Views Needed
- Certificate gallery (student's earned certificates)
- Certificate detail view
- Certificate download (PDF)
- Certificate verification (public)
- Achievement showcase
- Certificate generation (admin/automated)

### URLs
- `/certificates/`
- `/certificates/<int:certificate_id>/`
- `/certificates/<int:certificate_id>/download/`
- `/certificates/verify/<str:certificate_number>/`
- `/achievements/`

---

## INTER-APP RELATIONSHIPS

### Student → Courses
- Students enroll in YLE levels
- Students progress through units and lessons
- Students complete activities and assessments

### Student → Progress
- Each student has skill progress tracked per level
- Each student has unit progress records
- Each student has lesson completion records
- Each activity attempt is logged

### Progress → Courses
- Progress tracks completion of units, lessons, activities
- Assessment results linked to specific assessments
- Skill progress calculated based on course activities

### Certification → Students + Progress + Courses
- Certificates awarded based on progress milestones
- Level completion triggers certificate generation
- Achievements earned based on activity completion
- Shields calculated from assessment results

---

## DATABASE RELATIONSHIPS DIAGRAM

```
┌─────────────┐
│   Student   │
└──────┬──────┘
       │
       ├─────────────┐
       │             │
       ▼             ▼
┌─────────────┐  ┌──────────────┐
│ SkillProgress│  │StudentBadge │
└─────────────┘  └──────────────┘
       │
       │
       ▼
┌─────────────┐
│ YLELevel    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    Unit     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Lesson    │
└──────┬──────┘
       │
       ├─────────────┐
       │             │
       ▼             ▼
┌─────────────┐  ┌──────────────┐
│  Activity   │  │ Assessment   │
└─────────────┘  └──────────────┘
       │             │
       │             │
       ▼             ▼
┌─────────────┐  ┌──────────────────┐
│ActivityAttempt│ │AssessmentResult │
└─────────────┘  └──────────────────┘
       │             │
       └──────┬──────┘
              │
              ▼
       ┌─────────────┐
       │Certificate  │
       └─────────────┘
```

---

## NEXT STEPS

### Order of Implementation:
1. ✓ **Students App** - Create base student models and authentication
2. **Courses App** - Build the dynamic course structure
3. **Progress App** - Implement progress tracking system
4. **Certification App** - Create certificate generation and awards

### For Each App:
1. Create Django app: `python manage.py startapp <app_name>`
2. Define models in `models.py`
3. Create and run migrations
4. Register models in admin
5. Create views and templates
6. Configure URLs
7. Test functionality

---

## ADDITIONAL CONSIDERATIONS

### Security
- Ensure students can only view their own progress
- Parent access controls
- Teacher/admin access levels
- Secure certificate verification

### Performance
- Cache progress calculations
- Optimize queries with `select_related` and `prefetch_related`
- Index frequently queried fields

### Scalability
- Use JSONField for flexible activity data
- Allow dynamic course content addition
- Modular certificate templates

### User Experience
- Colorful, age-appropriate UI
- Visual progress indicators
- Instant feedback on activities
- Celebratory animations for achievements

---

**Document Version:** 1.0
**Last Updated:** 2026-02-10
**Author:** PolymathYLE Development Team
