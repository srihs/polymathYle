"""
Management command to set up user groups and permissions for the YLE LMS
Run: python manage.py setup_groups
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


class Command(BaseCommand):
    help = 'Set up user groups and permissions for Teachers, Students, Guardians, and Staff'

    def handle(self, *args, **kwargs):
        self.stdout.write('Setting up user groups and permissions...\n')

        # Clear existing groups (optional - comment out if you want to preserve)
        # Group.objects.all().delete()

        # 1. ADMIN GROUP (Full access - Django staff)
        admin_group, created = Group.objects.get_or_create(name='Admin')
        if created:
            self.stdout.write(self.style.SUCCESS('✓ Created Admin group'))

        # Admins have all permissions (set via Django's is_staff and is_superuser)

        # 2. TEACHER GROUP
        teacher_group, created = Group.objects.get_or_create(name='Teachers')
        if created:
            self.stdout.write(self.style.SUCCESS('✓ Created Teachers group'))

        teacher_permissions = [
            # Students - View and mark attendance
            'view_student',
            'view_attendance',
            'add_attendance',
            'change_attendance',

            # Courses - View all course materials
            'view_ylelevel',
            'view_class',
            'view_unit',
            'view_lesson',
            'view_activity',
            'view_assessment',

            # Progress - View and update student progress
            'view_skillprogress',
            'change_skillprogress',
            'view_unitprogress',
            'change_unitprogress',
            'view_lessonprogress',
            'change_lessonprogress',
            'view_activityattempt',
            'add_activityattempt',
            'view_assessmentresult',
            'add_assessmentresult',
            'change_assessmentresult',

            # Certification - View only
            'view_certificate',
            'view_achievement',
        ]

        self._assign_permissions(teacher_group, teacher_permissions)

        # 3. STUDENT GROUP
        student_group, created = Group.objects.get_or_create(name='Students')
        if created:
            self.stdout.write(self.style.SUCCESS('✓ Created Students group'))

        student_permissions = [
            # View their own data
            'view_student',
            'view_studentbadge',
            'view_attendance',

            # Courses - View only
            'view_ylelevel',
            'view_unit',
            'view_lesson',
            'view_activity',

            # Progress - View their own progress
            'view_skillprogress',
            'view_unitprogress',
            'view_lessonprogress',
            'view_activityattempt',
            'view_assessmentresult',

            # Certification - View their own certificates
            'view_certificate',
            'view_achievement',
        ]

        self._assign_permissions(student_group, student_permissions)

        # 4. GUARDIAN GROUP (Parents)
        guardian_group, created = Group.objects.get_or_create(name='Guardians')
        if created:
            self.stdout.write(self.style.SUCCESS('✓ Created Guardians group'))

        guardian_permissions = [
            # View their children's data
            'view_student',
            'view_guardian',
            'view_studentbadge',
            'view_attendance',

            # Courses - View only
            'view_ylelevel',
            'view_class',

            # Progress - View children's progress
            'view_skillprogress',
            'view_unitprogress',
            'view_assessmentresult',

            # Certification - View children's certificates
            'view_certificate',
            'view_achievement',
        ]

        self._assign_permissions(guardian_group, guardian_permissions)

        # 5. STAFF GROUP (Office/Administrative staff)
        staff_group, created = Group.objects.get_or_create(name='Staff')
        if created:
            self.stdout.write(self.style.SUCCESS('✓ Created Staff group'))

        staff_permissions = [
            # Applications - Full access
            'view_application',
            'add_application',
            'change_application',
            'delete_application',

            # Guardians - Full access
            'view_guardian',
            'add_guardian',
            'change_guardian',

            # Students - Full access
            'view_student',
            'add_student',
            'change_student',

            # Teachers - View only
            'view_teacher',
            'view_teacherdocument',
            'view_teacherhourlyrate',

            # Attendance - Full access
            'view_attendance',
            'add_attendance',
            'change_attendance',

            # Classes - View and assign
            'view_class',
            'change_class',

            # Certificates - Issue certificates
            'view_certificate',
            'add_certificate',
            'change_certificate',
        ]

        self._assign_permissions(staff_group, staff_permissions)

        self.stdout.write(self.style.SUCCESS('\n✓ All groups and permissions set up successfully!'))
        self.stdout.write('\nGroups created:')
        self.stdout.write('  - Admin (superuser access)')
        self.stdout.write('  - Teachers (mark attendance, update progress, view courses)')
        self.stdout.write('  - Students (view own progress and courses)')
        self.stdout.write('  - Guardians (view children\'s progress)')
        self.stdout.write('  - Staff (manage applications, students, certificates)')

    def _assign_permissions(self, group, permission_codenames):
        """Helper method to assign permissions to a group"""
        permissions = []
        for codename in permission_codenames:
            try:
                perm = Permission.objects.get(codename=codename)
                permissions.append(perm)
            except Permission.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'  Warning: Permission "{codename}" not found')
                )

        group.permissions.set(permissions)
        self.stdout.write(f'  → Assigned {len(permissions)} permissions to {group.name}')
