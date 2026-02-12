# Role-Based Authentication Guide - PolymathYLE LMS

## Overview

The PolymathYLE LMS now has complete role-based authentication with 5 user roles:

1. **Admin** - Full system access (Superusers)
2. **Teachers** - Mark attendance, update progress, view courses
3. **Students** - View own progress and courses
4. **Guardians** - View children's progress
5. **Staff** - Manage applications, students, certificates

## User Groups and Permissions

### 1. Admin Group
- **Access:** Full system access
- **Permissions:** All permissions (via Django's `is_superuser`)
- **Dashboard:** Django Admin Panel

**Capabilities:**
- Manage all users and groups
- Access all admin sections
- Configure system settings
- Manage teachers and staff

---

### 2. Teachers Group
- **Access:** Teaching and progress tracking
- **Permissions:** 23 permissions
- **Dashboard:** Teacher Dashboard (`/teacher/dashboard/`)

**Capabilities:**
✅ **Students:**
- View students
- View attendance records
- Add/change attendance

✅ **Courses:**
- View all YLE levels
- View assigned classes
- View units and lessons
- View activities and assessments

✅ **Progress:**
- View and update skill progress
- View and update unit/lesson progress
- Add activity attempts
- Add and update assessment results

✅ **Certificates:**
- View certificates and achievements

**Restrictions:**
❌ Cannot approve applications
❌ Cannot modify student records
❌ Cannot change class assignments
❌ Cannot delete records

---

### 3. Students Group
- **Access:** View own data and learning materials
- **Permissions:** 14 permissions
- **Dashboard:** Student Dashboard (`/students/dashboard/`)

**Capabilities:**
✅ **Own Data:**
- View own student profile
- View own badges
- View own attendance
- View own progress (4 skills)
- View own certificates

✅ **Courses:**
- View YLE levels
- View units and lessons
- View activities (read-only)

**Restrictions:**
❌ Cannot view other students' data
❌ Cannot modify any records
❌ Cannot access admin functions

---

### 4. Guardians Group
- **Access:** View children's data
- **Permissions:** 11 permissions
- **Dashboard:** Guardian Portal (`/students/guardian/portal/`)

**Capabilities:**
✅ **Children's Data:**
- View children's profiles
- View children's badges
- View children's attendance
- View children's progress
- View children's certificates
- View children's classes

✅ **Courses:**
- View YLE levels (read-only)
- View class information

**Restrictions:**
❌ Cannot view other students
❌ Cannot modify any records
❌ Cannot access teacher or staff functions

---

### 5. Staff Group
- **Access:** Administrative functions
- **Permissions:** 21 permissions
- **Dashboard:** Staff Dashboard (`/staff/dashboard/`)

**Capabilities:**
✅ **Applications:**
- View all applications
- Add/change/delete applications
- Process applications

✅ **Students & Guardians:**
- View/add/change students
- View/add/change guardians
- Assign students to classes

✅ **Attendance:**
- View/add/change attendance records

✅ **Classes:**
- View and update class assignments

✅ **Certificates:**
- View/add/change certificates
- Issue certificates to students

✅ **Teachers:**
- View teacher profiles (read-only)
- View teacher documents (read-only)
- View teacher rates (read-only)

**Restrictions:**
❌ Cannot modify teacher records
❌ Cannot approve teacher documents
❌ Cannot change teacher rates
❌ Cannot modify course content

---

## Authentication Flow

### Login Process

1. User visits `/` or `/login/`
2. Enters username and password
3. System authenticates user
4. System checks user's role (group membership)
5. User is redirected to appropriate dashboard:
   - **Superuser/Admin** → Django Admin Panel
   - **Teacher** → Teacher Dashboard
   - **Student** → Student Dashboard
   - **Guardian** → Guardian Portal
   - **Staff** → Staff Dashboard

### Dashboard Router

The `/dashboard/` URL automatically routes users based on their role:

```python
def dashboard_view(request):
    if user.is_superuser or user.is_staff:
        return redirect('/admin/')
    elif user.groups.filter(name='Teachers').exists():
        return redirect('teacher_dashboard')
    elif user.groups.filter(name='Students').exists():
        return redirect('student_dashboard')
    elif user.groups.filter(name='Guardians').exists():
        return redirect('guardian_portal')
    elif user.groups.filter(name='Staff').exists():
        return redirect('staff_dashboard')
```

---

## Setup Instructions

### 1. Run Setup Command

First time setup - creates all user groups and assigns permissions:

```bash
python manage.py setup_groups
```

This creates:
- ✅ Admin group
- ✅ Teachers group (23 permissions)
- ✅ Students group (14 permissions)
- ✅ Guardians group (11 permissions)
- ✅ Staff group (21 permissions)

### 2. Create Superuser (Admin)

```bash
python manage.py createsuperuser
```

Follow prompts to create admin account.

### 3. Create Users via Admin Panel

Login to `/admin/` with superuser account:

#### Creating a Teacher:
1. Go to **Authentication and Authorization** → **Users** → **Add User**
2. Set username and password
3. Click **Save**
4. In **Permissions** section:
   - Check "Staff status" (allows admin panel access)
   - Add to **Teachers** group
5. Click **Save**
6. Go to **Students** → **Teachers** → **Add Teacher**
7. Link to the user account created above
8. Fill in teacher details (employee ID, qualifications, etc.)
9. Upload CV and certificates
10. Set hourly rate

#### Creating a Student:
1. Create User account and add to **Students** group
2. First, process their Application (approve it)
3. Go to **Students** → **Students** → **Add Student**
4. Link to user and approved application
5. Assign to class

#### Creating a Guardian:
1. Create User account and add to **Guardians** group
2. Go to **Students** → **Guardians** → **Add Guardian**
3. Link to user account
4. Link to their children (students)

#### Creating Staff:
1. Create User account
2. Check "Staff status"
3. Add to **Staff** group

---

## URL Structure

### Public URLs
- `/` - Login page
- `/login/` - Login page
- `/students/apply/` - Student application form

### Authenticated URLs
- `/dashboard/` - Auto-router to role-based dashboard
- `/logout/` - Logout

### Role-Specific Dashboards
- `/admin/` - Admin panel (Superusers, Teachers, Staff)
- `/teacher/dashboard/` - Teacher dashboard
- `/students/dashboard/` - Student dashboard
- `/students/guardian/portal/` - Guardian portal
- `/staff/dashboard/` - Staff dashboard

---

## Testing Authentication

### Test Teacher Login:

1. Create a teacher user and teacher profile
2. Login at `/login/`
3. Should redirect to `/teacher/dashboard/`
4. Dashboard shows:
   - Teacher profile summary
   - Assigned classes
   - Student count
   - Quick actions (mark attendance, record assessments)

### Test Student Login:

1. Create a student user and student profile
2. Login at `/login/`
3. Should redirect to `/students/dashboard/`
4. Dashboard shows:
   - Student profile
   - Progress stats (4 skills)
   - Badges earned
   - Recent activity

### Test Guardian Login:

1. Create a guardian user and guardian profile
2. Link guardian to student(s)
3. Login at `/login/`
4. Should redirect to `/students/guardian/portal/`
5. Dashboard shows:
   - Children's profiles
   - Combined progress
   - Attendance records
   - Certificates

### Test Staff Login:

1. Create a staff user
2. Login at `/login/`
3. Should redirect to `/staff/dashboard/`
4. Dashboard shows:
   - Pending applications
   - Recent enrollments
   - Statistics
   - Quick actions

---

## Security Features

### Permission Checks
- All views use `@login_required` decorator
- Role-specific views check group membership
- Admin panel respects permission system

### Data Isolation
- Students can only see their own data
- Guardians can only see their children's data
- Teachers can only see their assigned classes
- Staff cannot modify teacher records

### Automatic Redirects
- Unauthenticated users → Login page
- Authenticated users → Role-based dashboard
- Wrong role access → Redirected to appropriate dashboard

---

## Common Tasks

### Change User Role

1. Login to admin panel
2. Go to **Users** → Select user
3. In **Groups** section:
   - Remove from old group
   - Add to new group
4. Click **Save**

### Grant Admin Access

1. Edit user in admin panel
2. Check **Superuser status**
3. Check **Staff status**
4. Click **Save**

### Reset Password

```bash
python manage.py changepassword <username>
```

Or via admin panel:
1. Go to **Users** → Select user
2. Click "Change password" link
3. Enter new password

---

## Dashboard Features

### Teacher Dashboard
- **Statistics:** Total classes, students, classes taught
- **Classes List:** All assigned classes with details
- **Quick Actions:**
  - Mark attendance
  - Record assessment
  - View students
  - View lessons

### Staff Dashboard
- **Statistics:** Total applications, pending, approved, active students
- **Pending Applications:** Recent applications awaiting review
- **Recent Enrollments:** Latest student enrollments
- **Quick Actions:**
  - View all applications
  - Add application
  - Manage students
  - Issue certificates

### Student Dashboard
- **Profile:** Student photo, name, level, class
- **Progress:** 4 skills with progress bars
- **Badges:** Earned badges display
- **Stats:** Points, streak, attendance rate

### Guardian Portal
- **Children List:** All linked children
- **Combined Progress:** Overall progress view
- **Attendance:** Each child's attendance
- **Certificates:** Earned certificates

---

## Troubleshooting

### User Can't Login
- ✓ Check username and password are correct
- ✓ Check user account is active
- ✓ Check user has appropriate role assigned

### Wrong Dashboard Displayed
- ✓ Check user is in correct group
- ✓ Check user has required profile (Teacher/Student/Guardian)
- ✓ Logout and login again

### Permission Denied
- ✓ Check user has correct group membership
- ✓ Re-run `python manage.py setup_groups`
- ✓ Check profile exists (Teacher/Student/Guardian)

### Profile Not Found Error
- ✓ Create matching profile (Teacher/Student/Guardian)
- ✓ Link profile to user account
- ✓ Ensure OneToOne relationship is correct

---

## Best Practices

### User Creation Workflow

**For Teachers:**
1. Create User → Add to Teachers group → Set staff status
2. Create Teacher profile → Link to user
3. Upload documents and set rate
4. Assign to classes

**For Students:**
1. Receive application (online or paper)
2. Create Application record
3. Approve application → Auto-generates admission number
4. Create User → Add to Students group
5. Create Student → Link to user and application
6. Assign to class

**For Guardians:**
1. Create User → Add to Guardians group
2. Create Guardian profile → Link to user
3. Link to children via ManyToMany relationship

**For Staff:**
1. Create User → Add to Staff group → Set staff status
2. No additional profile needed

---

**Last Updated:** 2026-02-11
**Version:** 1.0
**Status:** Production Ready ✅
