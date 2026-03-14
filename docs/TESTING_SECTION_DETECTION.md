# Testing Section Detection Fix

## Quick Start

To test the section detection fix for father's fields:

```bash
# Navigate to project directory
cd /Users/sas/Repos/PolymathYLE

# Run the test script with a scanned application form
python3 test_section_detection.py <path_to_scanned_form.jpg>
```

## What the Test Does

The test script will:

1. **Load the scanned application form image**
2. **Extract all parent fields** using the OCR service:
   - Mother's name, contact number, occupation
   - Father's name, contact number, occupation
3. **Display extraction logs** showing:
   - Section detection process
   - Section boundaries (start_y, end_y)
   - Words found in each section
   - Label matching process
   - Final extracted values
4. **Verify correctness:**
   - Check that father's contact ≠ mother's contact
   - Check that father's occupation ≠ mother's occupation
   - Validate against expected values (if known)
5. **Report results:**
   - Show extracted values for both parents
   - Flag any issues found
   - Return PASS ✅ or FAIL ❌

## Expected Output

### Successful Test (PASS):

```
================================================================================
Testing Section-Aware Extraction for Father's Fields
================================================================================

Loading test image: /path/to/scanned_form.jpg

Starting OCR extraction...
================================================================================

INFO: === EXTRACTING FATHER FIELD: father_contact_number ===
INFO: Labels to search: ["FATHER'S CONTACT NUMBER", "FATHER'S CONTACT", ...]
INFO: Found FATHER's NAME field at index 45: 'FATHER'S' at y=1400
INFO: Found FATHER section at y=1400
INFO: Initial section boundaries: start_y=1400, end_y=1900
INFO: Searching for FATHER section end markers: ['CONTACT INFORMATION', ...]
INFO: Section boundary found: 'CONTACT' at y=1600
INFO: FATHER section ends at y=1600
INFO: Final section boundaries: start_y=1400, end_y=1600
INFO: Total words in FATHER section: 15
INFO: First 30 words in FATHER section:
INFO:   [0] y=1400: 'FATHER'S'
INFO:   [1] y=1400: 'NAME'
INFO:   [5] y=1450: 'CONTACT'
INFO:   [6] y=1450: 'NUMBER'
INFO:   [7] y=1460: '0771656172'
INFO: Searching for 'CONTACT' label within section boundaries...
INFO: Found 'CONTACT' label in FATHER section: 'CONTACT' at y=1450
INFO: Words right of 'CONTACT' label: ['NUMBER', '0771656172']
INFO: After section filtering: 2 value words: ['NUMBER', '0771656172']
INFO: After label filtering: 1 words: ['0771656172']
INFO: FINAL EXTRACTED VALUE for father_contact_number: '0771656172'

... (similar logs for father_occupation) ...

================================================================================
EXTRACTION RESULTS
================================================================================

Mother's Information:
----------------------------------------
  Name:       Randika Chamali Samarajewa
  Contact:    0719888262
  Occupation: Manager Human Resources

Father's Information:
----------------------------------------
  Name:       K.G.A Daminda Nalaka
  Contact:    0771656172
  Occupation: Merchant Navy (Seaman)

================================================================================
VERIFICATION
================================================================================

✓ Father's contact number is CORRECT: 0771656172
✓ Father's occupation is CORRECT: Merchant Navy (Seaman)
✓ Mother's contact number is CORRECT: 0719888262
✓ Mother's occupation is CORRECT: Manager Human Resources

All checks passed! ✓

TEST PASSED ✅
```

### Failed Test (Issues Found):

```
================================================================================
EXTRACTION RESULTS
================================================================================

Mother's Information:
----------------------------------------
  Name:       Randika Chamali Samarajewa
  Contact:    0719888262
  Occupation: Manager Human Resources

Father's Information:
----------------------------------------
  Name:       K.G.A Daminda Nalaka
  Contact:    0719888262              ← WRONG (same as mother)
  Occupation: Manager Human Resources  ← WRONG (same as mother)

================================================================================
VERIFICATION
================================================================================

ISSUES FOUND:
----------------------------------------
  CRITICAL: Father's contact number matches mother's contact number!
  CRITICAL: Father's occupation matches mother's occupation!
  ✗ Father's contact number is WRONG: Got '0719888262', expected '0771656172'
  ✗ Father's occupation is WRONG: Got 'Manager Human Resources', expected 'Merchant Navy (Seaman)'

TEST FAILED ❌
```

## Troubleshooting

### Issue: "OCR service not available"

**Solution:** Configure Google Cloud Vision credentials:

1. Enable Cloud Vision API in Google Cloud Console
2. Create a service account with Cloud Vision API access
3. Download the JSON credentials file
4. Set environment variable:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
   ```
   OR
   ```bash
   export GOOGLE_CLOUD_CREDENTIALS='{"type": "service_account", ...}'
   ```

### Issue: "Test image not found"

**Solution:** Provide a valid path to a scanned application form:

```bash
python3 test_section_detection.py /path/to/your/scanned_form.jpg
```

### Issue: Father's fields still extracting mother's data

**Possible Causes:**

1. **Section boundaries not being detected correctly:**
   - Check the logs for "Section boundary found" messages
   - Verify that FATHER section ends at a reasonable y-coordinate
   - Ensure section_end_y for FATHER is > section_start_y + 100

2. **Parent NAME field not being found:**
   - Check logs for "Found FATHER's NAME field" message
   - If not found, the fallback logic might be using wrong section markers
   - Manually verify that the form has "FATHER'S NAME" or "FATHER NAME" label

3. **Generic labels matching in wrong section:**
   - Check logs for which "CONTACT NUMBER" label is matched
   - Verify the y-coordinate of the matched label is within father's section
   - If wrong label is matched, section boundaries need adjustment

### Issue: No debug logs appearing

**Solution:** Ensure logging is configured:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

The test script already does this, but if running OCR extraction manually, add this.

## Manual Testing

If you need to test manually without the test script:

```python
import os
import django
import logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ylehub.settings')
django.setup()

from students.ocr_service import get_ocr_service

# Enable debug logging
logging.basicConfig(level=logging.INFO)

# Extract fields
service = get_ocr_service()
result = service.extract_form_fields('/path/to/scanned_form.jpg')

# Check father's fields
print(f"Father Contact: {result.get('father_contact_number')}")
print(f"Father Occupation: {result.get('father_occupation')}")
print(f"Mother Contact: {result.get('mother_contact_number')}")
print(f"Mother Occupation: {result.get('mother_occupation')}")

# Verify they're different
assert result.get('father_contact_number') != result.get('mother_contact_number')
assert result.get('father_occupation') != result.get('mother_occupation')
```

## Analyzing Debug Logs

Look for these key indicators in the logs:

### ✓ Good Signs:

```
INFO: Found FATHER's NAME field at index 45: 'FATHER'S' at y=1400
INFO: Section boundary found: 'CONTACT' at y=1600
INFO: Final section boundaries: start_y=1400, end_y=1600
INFO: Found 'CONTACT' label in FATHER section: 'CONTACT' at y=1450
INFO: FINAL EXTRACTED VALUE for father_contact_number: '0771656172'
```

### ✗ Warning Signs:

```
WARNING: No FATHER section header found!
# → Section detection failed completely

INFO: Final section boundaries: start_y=1400, end_y=1900
# → Section extends too far (500px default), no boundary found

INFO: Found 'CONTACT' label in FATHER section: 'CONTACT' at y=1050
# → Label y-coordinate is BELOW section_start_y (wrong!)

INFO: After section filtering: 0 value words
# → Nothing found in the section (boundaries might be wrong)
```

## Next Steps

If the test passes:
- ✅ The fix is working correctly
- ✅ Father's fields are extracting from father's section
- ✅ No cross-contamination with mother's fields

If the test fails:
1. Review the debug logs carefully
2. Check section boundary detection
3. Verify the form structure matches expectations
4. Consider adjusting section end markers in the code
5. Report the issue with logs and sample image

## Related Files

- **Fix Implementation:** `/Users/sas/Repos/PolymathYLE/students/ocr_service.py`
- **Test Script:** `/Users/sas/Repos/PolymathYLE/test_section_detection.py`
- **Detailed Explanation:** `/Users/sas/Repos/PolymathYLE/SECTION_DETECTION_FIX.md`
- **Visual Diagram:** `/Users/sas/Repos/PolymathYLE/SECTION_BOUNDARIES_DIAGRAM.md`
