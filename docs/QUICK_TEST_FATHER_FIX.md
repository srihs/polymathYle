# Quick Test Guide - Father's Details Extraction Fix

## What Was Fixed?

Father's details (name, contact, occupation) were being extracted incorrectly. The fix adds:
1. **Section-aware extraction** for father's name (previously missing)
2. **Context validation** to prevent picking up mother's data
3. **Enhanced debugging** to see exactly what's happening

## Quick Test (Command Line)

```bash
cd /Users/sas/Repos/PolymathYLE
python test_father_extraction.py /path/to/your/scanned_form.jpg
```

**What to look for:**
- ✓ Father's Name should be correct (not mother's name)
- ✓ Father's Contact should be correct (not mother's contact)
- ✓ Father's Occupation should be correct (not mother's occupation)
- ✓ No "cross-contamination" warnings

## Quick Test (Web Interface)

1. Start Django server:
   ```bash
   python manage.py runserver
   ```

2. Go to application upload page:
   ```
   http://localhost:8000/students/application/upload/
   ```

3. Upload the scanned form

4. Check the extracted data preview:
   - Father's Name should show: "K.G.A Daminda Nalaka" (or similar from your form)
   - Father's Contact should show: "0771656172" (or similar from your form)
   - Father's Occupation should show: "Merchant Navy (Seaman)" (or similar from your form)

## Viewing Debug Logs

When testing, you'll see detailed logs like:

```
=== EXTRACTING FATHER FIELD: father_name ===
Labels to search: ["FATHER'S FULL NAME", "FATHER'S NAME", ...]
Found label match: 'FATHER NAME' at position {...}
Strategy 1 - Right of label: Found 3 words: ['K.G.A', 'Daminda', 'Nalaka']
FINAL EXTRACTED VALUE for father_name: 'K.G.A Daminda Nalaka'
=== END EXTRACTION FOR father_name ===
```

**Good signs:**
- "FINAL EXTRACTED VALUE" shows correct data
- No "NO VALUE EXTRACTED" warnings
- Section boundaries detected correctly
- No cross-contamination warnings

**Bad signs:**
- "NO VALUE EXTRACTED" appears
- "No FATHER section header found"
- Values match mother's details
- Cross-contamination warnings

## Expected Results

### Before Fix
- Father's Name: [Wrong - might show mother's name or empty]
- Father's Contact: [Wrong - might show mother's contact or empty]
- Father's Occupation: [Wrong - might show mother's occupation or empty]

### After Fix
- Father's Name: "K.G.A Daminda Nalaka" ✓
- Father's Contact: "0771656172" ✓
- Father's Occupation: "Merchant Navy (Seaman)" ✓

## If It's Still Wrong

### Check 1: Is FATHER section detected?
Look for this in logs:
```
Found FATHER section at y=1250
Section boundaries: start_y=1250, end_y=1500
```

If missing → Form might not have clear "FATHER" section header

### Check 2: Are labels found in section?
Look for this in logs:
```
Found 'NAME' label in FATHER section: 'FATHER NAME' at y=1260
Found 'CONTACT' label in FATHER section: 'CONTACT' at y=1280
```

If missing → Labels might be spelled differently on form

### Check 3: Are values extracted from section?
Look for this in logs:
```
Words right of 'NAME' label: ['K.G.A', 'Daminda', 'Nalaka']
After section filtering: 3 value words: ['K.G.A', 'Daminda', 'Nalaka']
```

If empty → Values might be positioned differently on form

## Troubleshooting

### Problem: All father fields are empty

**Try:**
1. Check if form has "FATHER" text visible
2. Look at debug logs for "No FATHER section header found"
3. Verify OCR is recognizing text from that area

### Problem: Father fields show mother's data

**Try:**
1. Check section boundaries in logs
2. Verify section_start_y and section_end_y don't overlap
3. Look for "Section boundary found" messages

### Problem: Some fields correct, others wrong

**Try:**
1. Check which strategy succeeded for correct fields
2. Look at debug logs for failing fields
3. Verify labels appear correctly on form

## Files Changed

Only one file modified:
- `/Users/sas/Repos/PolymathYLE/students/ocr_service.py`

New test files created (safe to delete after testing):
- `/Users/sas/Repos/PolymathYLE/test_father_extraction.py`
- `/Users/sas/Repos/PolymathYLE/FATHER_EXTRACTION_DEBUG.md`
- `/Users/sas/Repos/PolymathYLE/FATHER_EXTRACTION_FIX_SUMMARY.md`
- `/Users/sas/Repos/PolymathYLE/QUICK_TEST_FATHER_FIX.md` (this file)

## Status

**NOT COMMITTED YET**

Test first, then commit when confirmed working.

## Need More Help?

Read the detailed docs:
- `FATHER_EXTRACTION_FIX_SUMMARY.md` - Complete fix explanation
- `FATHER_EXTRACTION_DEBUG.md` - Debugging guide

Or check the code:
- `students/ocr_service.py` - Look for "is_father_field" debug blocks
