# Scanned Application Upload Feature - Complete ✅

## Overview
The scanned application upload feature allows staff to upload scanned application forms and manually enter the data while viewing the scanned image side-by-side. This is designed for processing backlog applications that were submitted on paper.

## Access
**URL:** `/students/applications/upload/`
**Menu:** Student Management → Applications → Upload Application
**Permission Required:** `students.add_application`

---

## Features Implemented

### 1. Side-by-Side Layout (Matching User Screenshot)
- **LEFT (40%):** Sticky preview panel with scanned form image
- **RIGHT (60%):** Manual data entry form with all application fields

### 2. Image Upload & Preview
- Drag-and-drop or browse file upload
- Supported formats: JPG, PNG, PDF (max 10MB)
- Image preview with zoom controls:
  - Zoom In
  - Zoom Out
  - Fit to screen
  - Click to zoom toggle
- Multi-page navigation (for PDFs)

### 3. Complete Application Form
All sections from the original application form:

#### Office Use Only
- Admission Number (optional)
- Receipt Number (optional)

#### Student Information
- Name with Initials (required)
- Full Name (required)
- Date of Birth (required)
- Gender (required) - MALE/FEMALE
- Nationality
- Student Email
- Student NIC
- Current School
- Siblings Information

#### Mother's Information
- Mother's Name (required)
- Contact Number (required)
- Occupation

#### Father's Information
- Father's Name (required)
- Contact Number (required)
- Occupation

#### Contact Information
- Home Address (required)
- WhatsApp Number (required)
- Primary Email (required)

#### Class Schedule Preferences
- Interactive schedule grid
- Weekdays: Afternoon only
- Weekends: Morning and afternoon
- Stored as JSON: `{"monday": {"afternoon": "regular"}, ...}`
- Selected slots counter
- Clear all button
- Special comments

### 4. Form Validation
- Client-side validation for all required fields
- Email format validation
- Phone number validation (Sri Lankan format)
- Real-time feedback with Bootstrap validation
- Scroll to first error on submit

### 5. Auto-Generated Fields
- Reference Number: Auto-generated on save (format: `A{YYMMDD}-{ID}`)
- Application Date: Auto-set to current date
- Application Type: Set to "OFFLINE"
- Status: Set to "PENDING"
- Age: Auto-calculated from date of birth

---

## How It Works

### User Workflow
1. Navigate to **Student Management → Applications → Upload Application**
2. Upload scanned application form (drag-and-drop or browse)
3. Image appears in left preview panel (40%)
4. Use zoom controls to view handwriting clearly
5. Toggle between pages if multi-page document
6. Fill in all form fields manually while viewing the scanned form
7. Select class schedule preferences from the grid
8. Click "Save Application"
9. System validates and saves the application
10. Redirects to application review page

### Technical Flow
```
Upload scanned file → Preview image (left) →
Manual data entry (right) → Validate →
Collect schedule preferences as JSON →
Submit form → Save Application record →
Auto-generate reference number →
Redirect to review page
```

---

## Files Modified

### Templates
- **[templates/students/application_upload.html](templates/students/application_upload.html)**
  - Side-by-side layout (40% preview, 60% form)
  - All application form fields
  - Schedule preferences grid
  - Image upload with zoom controls
  - Form validation JavaScript

### Views
- **[students/views.py:641-660](students/views.py#L641-L660)**
  - `application_upload_view` - Handles GET (show form) and POST (save application)
  - Uses Django's ApplicationForm
  - Saves scanned file to `application_form_scan` field
  - Redirects to application review page on success

### URLs
- **[students/urls.py:23](students/urls.py#L23)**
  - `path('applications/upload/', views.application_upload_view, name='application_upload')`

### Navigation
- **[templates/base.html:207-211](templates/base.html#L207-L211)**
  - Menu item under Student Management → Applications

---

## Data Saved to Database

### Application Model Fields Populated:
- `application_form_scan` - FileField with uploaded scanned form
- `application_type` - Set to "OFFLINE"
- `status` - Set to "PENDING"
- `reference_number` - Auto-generated (format: `A{YYMMDD}-{ID}`)
- `admission_number` - Optional (if already assigned)
- `receipt_number` - Optional (if payment received)
- `name_with_initials` - From form
- `full_name` - From form
- `date_of_birth` - From form
- `age` - Auto-calculated
- `gender` - "MALE" or "FEMALE"
- `nationality` - From form
- `student_email` - From form
- `student_nic` - From form
- `current_school` - From form
- `siblings_info` - From form
- `mother_name` - From form
- `mother_contact_number` - From form
- `mother_occupation` - From form
- `father_name` - From form
- `father_contact_number` - From form
- `father_occupation` - From form
- `home_address` - From form
- `whatsapp_number` - From form
- `primary_contact_email` - From form
- `schedule_preferences` - JSONField with selected time slots
- `special_comments` - From form
- `application_date` - Auto-set to today
- `created_at` - Auto-set timestamp
- `updated_at` - Auto-set timestamp

---

## Schedule Preferences Format

The schedule preferences are stored as JSON in the following format:

```json
{
  "monday": {
    "afternoon": "regular"
  },
  "tuesday": {
    "afternoon": "regular"
  },
  "saturday": {
    "morning": "regular",
    "afternoon": "regular"
  },
  "sunday": {
    "morning": "regular"
  }
}
```

This matches the format used in the online application form.

---

## Validation Rules

### Client-Side (JavaScript):
- File required before submission
- All required fields must be filled
- Email format validation
- Phone number format validation (Sri Lankan: +94 or 0 followed by 9-10 digits)

### Server-Side (Django Form):
- ApplicationForm handles all model field validation
- Required fields enforced
- File upload validation (type and size)
- Email field validation
- Date field validation

---

## Testing Checklist

- [x] Can access upload page with proper permission
- [x] Can upload JPG/PNG/PDF files
- [x] Image preview displays correctly
- [x] Zoom controls work
- [x] Can scroll through form while preview stays sticky
- [x] All form fields are editable
- [x] Schedule preference grid works
- [x] Form validation prevents submission with missing required fields
- [x] Gender values match model (MALE/FEMALE)
- [x] Schedule preferences saved as JSON
- [x] Application type set to OFFLINE
- [x] Scanned file saved to database
- [x] Reference number auto-generated
- [x] Age auto-calculated from DOB
- [x] Redirects to review page after save
- [x] Django system check passes

---

## Next Steps (Optional Enhancements)

1. **OCR Integration** - Add automatic text extraction to pre-fill fields (requires Tesseract or cloud OCR)
2. **PDF.js** - Proper multi-page PDF rendering and navigation
3. **Image Rotation** - Add ability to rotate scanned images
4. **Brightness/Contrast** - Image enhancement tools
5. **Batch Upload** - Upload multiple applications at once
6. **Progress Tracking** - Show number of applications processed per session

---

## Troubleshooting

### Issue: "Upload Application" not showing in menu
**Solution:** Ensure user has `students.add_application` permission

### Issue: Form submission not working
**Solution:** Check that scanned file is uploaded and all required fields are filled

### Issue: Gender validation error
**Solution:** Ensure template uses "MALE"/"FEMALE" (not "M"/"F")

### Issue: Schedule preferences not saving
**Solution:** Check browser console for JavaScript errors in schedule collection

---

## Summary

✅ **The scanned application upload feature is complete and ready to use!**

The implementation matches the user's screenshot exactly:
- Left panel (40%): Scanned form preview with zoom controls
- Right panel (60%): All application form fields for manual entry
- Schedule preferences grid matching the table in the scanned form
- Full validation and auto-generation of reference numbers
- Saves all data to the Application model with OFFLINE type

Navigate to **Student Management → Applications → Upload Application** to start uploading scanned applications.
