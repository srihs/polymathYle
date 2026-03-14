# Father's Details Extraction - Debug Analysis

## Problem
Father's details (name, contact, occupation) are being extracted incorrectly from the scanned application form.

**Expected values:**
- Father's Name: "K.G.A Daminda Nalaka"
- Father's Contact Number: "0771656172"
- Father's Occupation: "Merchant Navy (Seaman)"

## Root Cause Analysis

### Issue 1: Father's Name Not Using Section-Aware Extraction
**Problem:** The `father_name` field was NOT included in the section-aware extraction strategy (Strategy 5), which meant it could pick up the mother's name or student's name instead of the father's name.

**Original Code (Line 512):**
```python
if field_name in ['mother_occupation', 'father_occupation', 'mother_contact_number', 'father_contact_number']:
```

Notice `father_name` and `mother_name` were missing from this list!

**Fix:** Added name fields to section-aware extraction:
```python
if field_name in ['mother_name', 'father_name', 'mother_occupation', 'father_occupation',
                  'mother_contact_number', 'father_contact_number']:
```

### Issue 2: Section-Aware Method Didn't Handle Name Fields
**Problem:** The `_find_in_parent_section` method only looked for 'CONTACT' or 'OCCUPATION' keywords, not 'NAME'.

**Fix:** Enhanced the method to:
1. Detect 'NAME' field type
2. Search for 'NAME' keyword within the parent section
3. Verify that the NAME label has FATHER/MOTHER context nearby to avoid confusion
4. Use larger gap multiplier for names (they often have multiple words)
5. Allow multiline extraction for names (they can wrap)

## Changes Made

### 1. Enhanced Debugging for Father Fields
Added extensive logging throughout `_extract_field_value_spatial`:
- Logs when father field extraction starts
- Shows which labels are being searched
- Reports results from each extraction strategy
- Shows final extracted value or failure reason

### 2. Enhanced `_find_in_parent_section` Method
**Added name field support:**
- Detects NAME field type
- Searches for NAME keyword with parent context validation
- Uses appropriate gap multiplier for multi-word names
- Allows multiline extraction for wrapped names

**Improved section boundary detection:**
- Logs section start and end positions
- Shows all words within the section boundary
- Validates that field labels are within correct section

**Better label matching for names:**
- Requires FATHER/MOTHER context near NAME label
- Checks previous 2 words for parent prefix
- Prevents cross-contamination between mother and father sections

### 3. Added Detailed Debug Logging

The following logs will now appear for father field extraction:

```
=== EXTRACTING FATHER FIELD: father_name ===
Labels to search: ["FATHER'S FULL NAME", "FATHER'S NAME", ...]
Found label match: 'FATHER NAME' at position {...}
Strategy 1 - Right of label: Found 3 words: ['K.G.A', 'Daminda', 'Nalaka']
After label filtering: 3 words: ['K.G.A', 'Daminda', 'Nalaka']
FINAL EXTRACTED VALUE for father_name: 'K.G.A Daminda Nalaka'
=== END EXTRACTION FOR father_name ===
```

If section-aware extraction is triggered:
```
Strategy 5 - Attempting section-aware extraction for FATHER section
=== PARENT SECTION EXTRACTION for FATHER ===
Field name: father_contact_number
Found FATHER word at index 145: 'FATHER' at y=1250
Found FATHER section at y=1250
Section boundaries: start_y=1250, end_y=1750
Searching for 'CONTACT' label within section boundaries...
Words in FATHER section (12 total):
  0: 'FATHER' at y=1250
  1: 'NAME' at y=1260
  2: 'K.G.A' at y=1260
  ...
Found 'CONTACT' label in FATHER section: 'CONTACT' at y=1300
Words right of 'CONTACT' label: ['0771656172']
After section filtering: 1 value words: ['0771656172']
=== END PARENT SECTION EXTRACTION ===
```

## How to Test

1. **Upload the scanned form** through the application upload page
2. **Check the console logs** or Django debug logs for:
   - Father field extraction messages
   - Section boundary detection
   - Strategy results for each father field
   - Final extracted values

3. **Look for specific issues:**
   - Is the FATHER section being detected?
   - Are the correct labels (NAME, CONTACT, OCCUPATION) being found within the section?
   - Are the section boundaries correct (not overlapping with mother's section)?
   - Are the extracted values correct?

## Expected Behavior After Fix

### Father's Name
- Should detect "FATHER'S NAME" or "FATHER NAME" label
- Should verify it's within the FATHER section
- Should extract "K.G.A Daminda Nalaka" or similar
- Should NOT extract mother's name or student's name

### Father's Contact
- Should detect FATHER section first
- Should find "CONTACT NUMBER" within that section
- Should extract "0771656172"
- Should NOT extract mother's contact number

### Father's Occupation
- Should detect FATHER section first
- Should find "OCCUPATION" within that section
- Should extract "Merchant Navy (Seaman)" or similar
- Should NOT extract mother's occupation

## Common Issues to Watch For

1. **Section not detected:**
   - Check if "FATHER" word appears on the form
   - Check if OCR correctly recognized the section header
   - Look at the debug logs for "No FATHER section header found"

2. **Wrong section boundaries:**
   - Check section_start_y and section_end_y values
   - Verify they don't overlap with mother's section
   - Look for the section boundary detection logs

3. **Label not found in section:**
   - Check if "NAME", "CONTACT", or "OCCUPATION" appears in the section
   - Look at the "Words in FATHER section" debug output
   - Verify labels are correctly spelled on the form

4. **Cross-contamination:**
   - If father fields show mother's data, section boundaries are wrong
   - Check if section end detection is working properly
   - Verify other_parent detection is triggering correctly

## Testing Checklist

- [ ] Father's name extracts correctly (not mother's or student's name)
- [ ] Father's contact extracts correctly (not mother's contact)
- [ ] Father's occupation extracts correctly (not mother's occupation)
- [ ] Debug logs show FATHER section is detected
- [ ] Debug logs show correct section boundaries
- [ ] Debug logs show labels found within correct section
- [ ] No cross-contamination from mother's section
- [ ] Multiline values (occupation) are handled correctly

## Files Modified

- `/Users/sas/Repos/PolymathYLE/students/ocr_service.py`
  - Enhanced `_extract_field_value_spatial` with father field debugging
  - Updated Strategy 5 to include name fields
  - Enhanced `_find_in_parent_section` to handle NAME fields
  - Added extensive debug logging throughout

## Next Steps

1. **Test with the actual form** - Upload and check extraction results
2. **Review debug logs** - Verify section detection is working
3. **Verify all three father fields** - Name, Contact, Occupation
4. **Check for edge cases** - Forms with missing fields, handwritten vs printed, etc.

## DO NOT COMMIT YET

User wants to test first before committing. Keep this as a working change for testing.
