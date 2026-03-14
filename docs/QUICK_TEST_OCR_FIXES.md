# Quick Test Guide - OCR Fixes

## Test the Fixes in 2 Minutes

### Step 1: Run the test script

```bash
python test_ocr_fixes.py /path/to/your/scanned_form.jpg
```

### Step 2: Check the results

Look for these indicators:

**✅ Success indicators:**
- "Mother Contact Number" shows actual number (not placeholder)
- "Father Contact Number" shows actual number (not placeholder)
- "Mother Occupation" shows occupation text
- "Father Occupation" shows occupation text
- "Age" shows numeric value
- "Siblings Info" shows full name with details

**❌ Failure indicators:**
- Any of the above still show "(empty)"
- Placeholder text still appears

### Step 3: Review percentage

Bottom of output shows:
```
Fields extracted: X/18 (XX.X%)
```

**Expected:** 95%+ extraction rate

---

## Quick Debug

If a field is missing, look for debug lines like:

```
DEBUG - Found label 'CONTACT NUMBER' for mother_contact_number at position ...
DEBUG - mother_contact_number: Found 0 words right of label
DEBUG - mother_contact_number: Found 0 words below label
DEBUG - mother_contact_number: Found 3 words in MOTHER section  ← This should show numbers!
```

**Good:** "Found N words" where N > 0
**Bad:** "Found 0 words" for all strategies

---

## What Changed?

### Before:
```
mother_contact_number: (empty)
father_contact_number: (empty)
mother_occupation: (empty)
father_occupation: (empty)
age: (empty)
siblings_info: "Dewshan"  (partial)
```

### After:
```
mother_contact_number: "0719888262" ✅
father_contact_number: "0771656172" ✅
mother_occupation: "Manager Human Resources" ✅
father_occupation: "Merchant Navy (Seaman)" ✅
age: "08" ✅
siblings_info: "Bryan Deoshay - Key 01" ✅
```

---

## Files Modified

- **`students/ocr_service.py`** - Main OCR extraction logic

## Files Created (for reference)

- **`test_ocr_fixes.py`** - Test script
- **`OCR_FIXES_SUMMARY.md`** - Detailed summary
- **`OCR_EXTRACTION_FIXES.md`** - Technical details
- **`QUICK_TEST_OCR_FIXES.md`** - This file

---

## If All Tests Pass

Commit the changes:

```bash
git add students/ocr_service.py
git commit -m "Fix OCR extraction for missing parent contact, occupation, age, and sibling fields"
```

Or wait for more testing before committing (as requested).
