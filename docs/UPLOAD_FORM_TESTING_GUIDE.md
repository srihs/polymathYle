# Application Upload Form - Testing Guide

## Quick Test Checklist

### Prerequisites
- [ ] Django development server is running (`python manage.py runserver`)
- [ ] Browser Developer Tools are open (F12)
- [ ] Console tab is visible in Developer Tools

### Test Case 1: Complete Successful Submission

**Steps:**

1. **Navigate to Upload Page**
   - URL: `http://localhost:8000/applications/upload/`
   - Expected: Upload form loads with preview panel on left, form on right

2. **Upload a File**
   - Click "Browse Files" or drag-and-drop an image/PDF
   - Expected:
     - Preview appears on left
     - Extract Data button appears
     - Console shows file upload confirmation

3. **Fill Required Fields**

   **Student Information:**
   - Name with Initials: `K.D.S. Perera`
   - Full Name: `Kamal Dilshan Sampath Perera`
   - Date of Birth: `2015-05-15` (will auto-calculate age)
   - Gender: `Male`

   **Mother's Information:**
   - Mother's Name: `Nimalika Perera`
   - Contact Number: `0771234567`

   **Father's Information:**
   - Father's Name: `Sunil Perera`
   - Contact Number: `0779876543`

   **Contact Information:**
   - Home Address: `123 Galle Road, Colombo 03`
   - WhatsApp Number: `0771234567`

4. **Optional: Select Schedule Preferences**
   - Click on any time slots in the schedule table
   - Counter should update (e.g., "3 time slots selected")

5. **Submit Form**
   - Click "Save Application" button
   - Expected Console Output:
   ```
   === Form Submit Handler Triggered ===
   Checking uploaded file: File {...}
   File check passed: filename.jpg
   Hidden file input files: FileList {0: File, length: 1}
   Validating required fields...
   All required fields valid
   Validating email fields...
   Validating phone fields...
   All validations passed
   Collecting schedule preferences...
   Schedule preferences: {...}
   Setting loading state...
   === Form Data Summary ===
   Form action: /applications/upload/
   Form method: post
   Form enctype: multipart/form-data
   ...
   Submitting form now...
   Form submit() called - page should reload/redirect
   ```

   - Expected Visual Behavior:
     - Button shows spinner
     - Text changes to "Saving..."
     - Button becomes disabled
     - Page redirects to application review page
     - Success message appears: "Application [REF-XXX] saved successfully!"

### Test Case 2: Missing File Upload

**Steps:**
1. Navigate to upload page
2. Fill all required fields
3. **Do NOT upload a file**
4. Click "Save Application"

**Expected:**
- Alert appears: "Please upload a scanned application form first."
- Console shows: `ERROR: No file uploaded`
- Form does NOT submit
- No redirect

### Test Case 3: Missing Required Fields

**Steps:**
1. Upload a file
2. Fill only some fields (leave Mother's Name empty)
3. Click "Save Application"

**Expected:**
- Console shows: `Invalid required fields: [mother_name, ...]`
- Empty required fields get red border (Bootstrap `is-invalid` class)
- Page scrolls to first invalid field
- No form submission
- No redirect

### Test Case 4: Invalid Email Format

**Steps:**
1. Upload file
2. Fill all required fields
3. Enter invalid email in "Primary Email": `notanemail`
4. Click "Save Application"

**Expected:**
- Console shows: `Invalid email: primary_contact_email, notanemail`
- Email field gets red border
- Form validation message appears
- No submission

### Test Case 5: Invalid Phone Number

**Steps:**
1. Upload file
2. Fill all required fields
3. Enter invalid phone in Mother's Contact: `12345`
4. Click "Save Application"

**Expected:**
- Console shows: `Invalid phone: mother_contact_number, 12345`
- Phone field gets red border
- No submission

### Test Case 6: Extract Data (OCR) - If Available

**Steps:**
1. Upload a clear image of filled application form
2. Click "Extract Data" button

**Expected:**
- Button shows "Extracting..." with spinner
- AJAX call to `/api/ocr/extract/`
- If successful: Fields auto-populate with green border highlight
- If OCR not configured: Warning message appears
- Console shows field population log

## Console Log Reference

### Successful Submission Flow

```javascript
=== Form Submit Handler Triggered ===
Checking uploaded file: File {name: "application.jpg", ...}
File check passed: application.jpg
Hidden file input files: FileList {0: File, length: 1}
Validating required fields...
All required fields valid
Validating email fields...
Validating phone fields...
All validations passed
Collecting schedule preferences...
Schedule preferences: {monday: {afternoon: "regular"}, saturday: {morning: "regular", afternoon: "regular"}}
Schedule preferences JSON: {"monday":{"afternoon":"regular"},"saturday":{"morning":"regular","afternoon":"regular"}}
Setting loading state...
=== Form Data Summary ===
Form action: http://localhost:8000/applications/upload/
Form method: post
Form enctype: multipart/form-data
File input name: application_form_scan
File input files: FileList {0: File, length: 1}
Key fields:
- name_with_initials: K.D.S. Perera
- full_name: Kamal Dilshan Sampath Perera
- date_of_birth: 2015-05-15
- gender: MALE
- mother_name: Nimalika Perera
- father_name: Sunil Perera
- home_address: 123 Galle Road, Colombo 03
- whatsapp_number: 0771234567
Submitting form now...
Form submit() called - page should reload/redirect
```

### Failed Validation Flow

```javascript
=== Form Submit Handler Triggered ===
Checking uploaded file: File {...}
File check passed: application.jpg
Hidden file input files: FileList {0: File, length: 1}
Validating required fields...
Invalid required fields: [mother_name, father_name, home_address]
Validation failed, scrolling to first error
```

## Backend Verification

After successful submission, verify in Django admin or database:

1. **Application Record Created**
   - Navigate to `/admin/students/application/`
   - Find the newly created application
   - Verify all fields are populated

2. **File Upload Saved**
   - Check that `application_form_scan` field has a file path
   - File should be in `media/applications/scans/` directory

3. **Reference Number Generated**
   - Format: `REF-YYYYMMDD-NNNN` (e.g., `REF-20260314-0001`)

4. **Application Type Set**
   - `application_type` should be `OFFLINE`

5. **Schedule Preferences JSON**
   - Should be valid JSON object
   - Example: `{"monday": {"afternoon": "regular"}}`

## Common Issues & Debugging

### Issue: Form submits but no file saved

**Debug Steps:**
1. Check console log - look for "File input files: FileList {length: 0}"
2. This indicates hidden input is empty
3. Code should auto-detect and re-transfer file
4. Look for: "ERROR: Hidden file input is empty, attempting to set file again"

**Solution:**
- Already handled in code (lines 1088-1097 of template)
- If still failing, check browser compatibility with DataTransfer API

### Issue: Page doesn't redirect

**Debug Steps:**
1. Check browser Network tab in Developer Tools
2. Look for POST request to `/applications/upload/`
3. Check response status:
   - **200 OK**: Form validation failed on server, errors should be shown
   - **302 Redirect**: Success! Check redirect target
   - **500 Error**: Server error, check Django logs

**Check Django Console:**
```bash
# Look for form validation errors
ApplicationForm is not valid
Field 'terms_accepted' failed validation
```

### Issue: "Terms must be accepted" error

**Cause:** Form validation is incorrectly requiring terms for upload form

**Debug Steps:**
1. Check if `terms_accepted` checkbox is in the upload template (it shouldn't be)
2. Verify form validation in `students/forms.py` line 141
3. Should only validate terms if checkbox was in POST data

**Fix Applied:**
```python
if 'terms_accepted' in self.data:
    # Only validate if checkbox was in form
    if not terms:
        raise forms.ValidationError('...')
```

## Performance Testing

### Upload Large Files
- Test with 10MB PDF
- Should upload successfully
- Check server memory usage
- Verify file size validation (max 10MB)

### Multiple Rapid Submissions
1. Fill form
2. Click Submit multiple times quickly
3. Expected: Button disables after first click
4. Only one application should be created

## Accessibility Testing

### Keyboard Navigation
- [ ] Tab through all form fields
- [ ] Space bar toggles schedule checkboxes
- [ ] Enter key submits form
- [ ] Form validation errors are announced by screen readers

### Screen Reader Testing
- [ ] All form labels are read correctly
- [ ] Error messages are associated with fields (aria-describedby)
- [ ] Loading state is announced

## Mobile Testing

Test on mobile viewport (320px width):
- [ ] Form layout is responsive (stacks vertically)
- [ ] File upload works on mobile
- [ ] Touch targets are at least 44x44px
- [ ] Virtual keyboard doesn't obscure submit button

## Clean Up After Testing

After testing is complete and working:

### Remove Debug Console Logs (Production)
Edit `/Users/sas/Repos/PolymathYLE/templates/students/application_upload.html` and remove/comment out console.log statements:

- Line 1072: `console.log('=== Form Submit Handler Triggered ===')`
- Lines 1080-1086: File upload logging
- Lines 1088-1096: Hidden file input logging
- Lines 1100-1115: Validation logging
- Line 1118: Email validation log
- Line 1130: Phone validation log
- Line 1145: Validation failed log
- Line 1152: Validation passed log
- Lines 1155-1169: Schedule preferences logging
- Line 1172: Loading state log
- Lines 1179-1200: Form data summary and submission logs

### Or Use Conditional Logging
Wrap all console logs in a debug flag:

```javascript
const DEBUG_MODE = false; // Set to true for debugging

if (DEBUG_MODE) console.log('...');
```

## Success Criteria

The form submission is working correctly when:

- [ ] File uploads and previews correctly
- [ ] All validation rules work as expected
- [ ] Form submits successfully with valid data
- [ ] User is redirected to application review page
- [ ] Success message appears after redirect
- [ ] Application is saved in database with correct data
- [ ] File is saved to media directory
- [ ] Reference number is generated
- [ ] No JavaScript errors in console
- [ ] Works on desktop and mobile browsers
