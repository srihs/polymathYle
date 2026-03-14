# Section Detection Fix for Father's Fields

## Problem Summary

Father's contact number and occupation were being extracted from mother's fields instead of father's fields, even though section-aware extraction was implemented.

### Symptoms:
- `father_contact_number`: Getting mother's contact "0719888262" instead of "0771656172"
- `father_occupation`: Getting mother's occupation "Manager Human Resources" instead of "Merchant Navy (Seaman)"

## Root Cause Analysis

The issue was in the `_find_in_parent_section()` method in `/Users/sas/Repos/PolymathYLE/students/ocr_service.py`.

### Original Logic Flaw:

1. **Section Boundary Detection (Lines 776-794):**
   ```python
   # Original code
   section_start_y = parent_section_bounds['y']
   section_end_y = section_start_y + 500  # Default: 500px down

   other_parent = 'FATHER' if parent_prefix == 'MOTHER' else 'MOTHER'
   for word in words:
       if (word['bounds']['y'] > section_start_y and
           (other_parent in word['text'].upper() or ...)):
           section_end_y = min(section_end_y, word['bounds']['y'])
           break
   ```

2. **The Problem:**
   - For **MOTHER** section: Correctly finds "FATHER" keyword AFTER mother's section (higher y-coordinate) and sets section_end_y
   - For **FATHER** section: Looks for "MOTHER" keyword, but MOTHER appears BEFORE father in the document (lower y-coordinate)
   - The condition `word['bounds']['y'] > section_start_y` is FALSE for MOTHER words
   - Result: FATHER section extends the full 500px down, potentially including other sections

3. **Section Marker Ambiguity:**
   - The code searched for any word containing "FATHER" or "MOTHER"
   - Could match "FATHER'S NAME" label, section headers, or any other occurrence
   - Not specific enough to reliably detect section boundaries

## The Fix

### Changes Made:

1. **Improved Parent Section Detection (Lines 741-790):**
   ```python
   # NEW: Look for "FATHER'S NAME" or "MOTHER'S NAME" as section start
   # This is more reliable than just "FATHER" or "MOTHER"
   parent_name_found = False

   for i, word in enumerate(words):
       word_text = word['text'].upper()
       if parent_prefix in word_text:
           # Check if this is the NAME field for this parent
           is_name_field = False
           if 'NAME' in word_text:  # "FATHER'S" and "NAME" in same word
               is_name_field = True
           else:
               # Check next 2 words for "NAME"
               for j in range(i+1, min(i+3, len(words))):
                   if 'NAME' in words[j]['text'].upper():
                       is_name_field = True
                       break

           if is_name_field:
               parent_words.append(word)
               parent_name_found = True
               break
   ```

2. **Fixed Section Boundary Logic (Lines 787-823):**
   ```python
   if parent_prefix == 'MOTHER':
       # Mother section ends where Father section begins
       other_parent = 'FATHER'
       # Look for words with y > section_start_y (below mother)

   else:  # FATHER section
       # Father section ends at next major section (NOT mother)
       # Look for sections that come AFTER family information
       section_end_markers = [
           'CONTACT INFORMATION', 'HOME ADDRESS', 'STUDENT INFORMATION',
           'SIBLINGS', 'PAYMENT', 'OFFICE USE', 'REMARKS'
       ]
       # Search for these markers with y > section_start_y
   ```

3. **Added Extensive Debug Logging:**
   - Logs section detection process for father fields
   - Shows section boundaries (start_y, end_y)
   - Lists all words in the section
   - Shows which label was matched and why

## How It Works Now

### For MOTHER Fields:
1. Find "MOTHER'S NAME" or "MOTHER" keyword
2. Section starts at MOTHER keyword position
3. Section ends at FATHER keyword position (or next major section)
4. Extract CONTACT NUMBER and OCCUPATION within this section

### For FATHER Fields:
1. Find "FATHER'S NAME" or "FATHER" keyword
2. Section starts at FATHER keyword position
3. Section ends at next major section marker (CONTACT INFORMATION, HOME ADDRESS, etc.)
4. Extract CONTACT NUMBER and OCCUPATION within this section
5. **Critical:** Don't look backwards for MOTHER section

## Expected Behavior After Fix

### Extraction Log (Father's Contact Number):
```
INFO: === EXTRACTING FATHER FIELD: father_contact_number ===
INFO: Found FATHER's NAME field at index 45: 'FATHER'S' at y=1400
INFO: Found FATHER section at y=1400
INFO: Initial section boundaries: start_y=1400, end_y=1900
INFO: Searching for FATHER section end markers: ['CONTACT INFORMATION', 'HOME ADDRESS', ...]
INFO: Section boundary found: 'CONTACT' at y=1600
INFO: FATHER section ends at y=1600
INFO: Final section boundaries: start_y=1400, end_y=1600
INFO: Total words in FATHER section: 15
INFO: First 30 words in FATHER section:
INFO:   [0] y=1400: 'FATHER'S'
INFO:   [1] y=1400: 'NAME'
INFO:   [2] y=1410: 'K.G.A'
INFO:   [3] y=1410: 'Daminda'
INFO:   [4] y=1410: 'Nalaka'
INFO:   [5] y=1450: 'CONTACT'
INFO:   [6] y=1450: 'NUMBER'
INFO:   [7] y=1460: '0771656172'
INFO:   [8] y=1500: 'OCCUPATION'
INFO:   [9] y=1510: 'Merchant'
INFO:   [10] y=1510: 'Navy'
INFO:   [11] y=1510: '(Seaman)'
INFO: Searching for 'CONTACT' label within section boundaries...
INFO: Found 'CONTACT' label in FATHER section: 'CONTACT' at y=1450
INFO: Words right of 'CONTACT' label: ['NUMBER', '0771656172']
INFO: After section filtering: 2 value words: ['NUMBER', '0771656172']
INFO: After label filtering: 1 words: ['0771656172']
INFO: FINAL EXTRACTED VALUE for father_contact_number: '0771656172'
```

### Expected Extraction Results:
```
Mother's Information:
  Name:       Randika Chamali Samarajewa
  Contact:    0719888262
  Occupation: Manager Human Resources

Father's Information:
  Name:       K.G.A Daminda Nalaka
  Contact:    0771656172           ← CORRECT (not mother's)
  Occupation: Merchant Navy (Seaman) ← CORRECT (not mother's)
```

## Testing

Run the test script to verify the fix:

```bash
python3 test_section_detection.py <path_to_scanned_form.jpg>
```

The test will:
1. Extract all parent fields (mother and father)
2. Verify father's fields don't match mother's fields
3. Verify extracted values match expected values
4. Report SUCCESS or FAILURE with detailed diagnostics

## Files Modified

1. **`/Users/sas/Repos/PolymathYLE/students/ocr_service.py`:**
   - Fixed `_find_in_parent_section()` method (lines 720-902)
   - Improved parent section detection to look for "PARENT'S NAME" field
   - Fixed section boundary logic for FATHER section
   - Added extensive debug logging for father fields

2. **`/Users/sas/Repos/PolymathYLE/test_section_detection.py`:** (NEW)
   - Test script to verify section-aware extraction
   - Checks for father/mother field cross-contamination
   - Validates extracted values against expected values

## Key Improvements

1. **More Specific Section Detection:**
   - Now looks for "FATHER'S NAME" / "MOTHER'S NAME" instead of just "FATHER" / "MOTHER"
   - Reduces ambiguity and false matches

2. **Context-Aware Boundary Detection:**
   - MOTHER section ends at FATHER section
   - FATHER section ends at next major section (not MOTHER, which comes before)

3. **Comprehensive Logging:**
   - Debug logs show exactly what's happening during extraction
   - Makes it easy to diagnose issues in the future

4. **Spatial Awareness:**
   - Sections are defined by y-coordinate ranges
   - Labels are matched only within the correct section
   - Prevents cross-contamination between similar fields

## Future Enhancements

Consider these improvements for even better accuracy:

1. **Multi-level Section Hierarchy:**
   - Detect "FAMILY INFORMATION" parent section
   - Then detect MOTHER and FATHER sub-sections within it

2. **X-Coordinate Awareness:**
   - Use horizontal alignment to distinguish between label and value columns
   - Reduce false label matches

3. **Machine Learning:**
   - Train a model to recognize form structure
   - Learn typical section layouts and field positions

4. **Confidence Scoring:**
   - Add confidence scores to section detection
   - Flag low-confidence extractions for manual review
