# Admission Number Extraction Fix

## Problem
The OCR service was extracting unwanted text along with the admission number. For example:
- **Input (OCR extracted)**: "YLE - 2021-1660 POLYMATH COLLEGE"
- **Expected output**: "YLE-2021-1660"

The issue occurred because the OCR spatial extraction captured text from the school logo/header area near the admission number field.

## Solution
Added a post-processing step to clean admission numbers by:

1. **Filtering school-related words** - Removes common school name words:
   - POLYMATH, COLLEGE, SCHOOL, ENGLISH, ACADEMY
   - UNIVERSITY, INSTITUTE, EDUCATION, LEARNING
   - CENTER, CENTRE, INTERNATIONAL, CAMBRIDGE

2. **Normalizing format** - Standardizes the admission number format:
   - Removes extra spaces around dashes: "YLE - 2021 - 1660" → "YLE-2021-1660"
   - Converts spaces to dashes: "YLE 2021 1660" → "YLE-2021-1660"

3. **Pattern validation** - Extracts and standardizes using pattern matching:
   - Pattern: `PREFIX-YEAR-NUMBER` (e.g., "YLE-2021-1660")
   - Regex: `([A-Z]+)-?(\d{4})-?(\d+)`
   - Reconstructs in standard format

## Changes Made

### File: `/Users/sas/Repos/PolymathYLE/students/ocr_service.py`

#### 1. Added `_clean_admission_number()` method (lines 1108-1176)
```python
def _clean_admission_number(self, value):
    """
    Clean admission number by removing school names and other non-admission text.
    """
    # Filters out school-related words
    # Normalizes spacing and dashes
    # Validates and standardizes format
```

#### 2. Updated `_post_process_fields()` method (lines 1059-1065)
```python
# Clean admission number - remove school names and unwanted text
if 'admission_number' in processed:
    original_value = processed['admission_number']
    cleaned = self._clean_admission_number(processed['admission_number'])
    if cleaned != original_value:
        logger.info(f"Admission number cleaned: '{original_value}' -> '{cleaned}'")
    processed['admission_number'] = cleaned
```

#### 3. Updated validation patterns
- **Confidence scoring** (lines 1348-1356): More flexible pattern matching
- **Field validation** (lines 1402-1405): Accepts variable-length admission numbers

## Test Results

Created comprehensive test suite (`/Users/sas/Repos/PolymathYLE/test_admission_cleaning.py`):

```
Test Cases (All Passed ✓):
1. "YLE - 2021-1660 POLYMATH COLLEGE" → "YLE-2021-1660" ✓
2. "YLE-2021-1660" → "YLE-2021-1660" ✓
3. "YLE - 2021 - 1660" → "YLE-2021-1660" ✓
4. "YLE 2021 1660" → "YLE-2021-1660" ✓
5. "FCE-2022-0001 ENGLISH ACADEMY" → "FCE-2022-0001" ✓
6. "YLE-2021-1660 INTERNATIONAL SCHOOL" → "YLE-2021-1660" ✓
7. "YLE-2020-0042" → "YLE-2020-0042" ✓
8. "IELTS - 2023 - 123 CAMBRIDGE CENTRE" → "IELTS-2023-123" ✓

Results: 8/8 tests passed
```

## Debug Logging

The fix includes debug logging to help track the cleaning process:

```python
logger.info(f"Admission number cleaned: '{original_value}' -> '{cleaned}'")
logger.debug(f"Cleaning admission number: '{value}'")
logger.debug(f"  Removing school-related word: '{word}'")
logger.debug(f"  After filtering: '{cleaned}'")
logger.debug(f"  After dash normalization: '{cleaned}'")
logger.debug(f"  Standardized format: '{standardized}'")
```

You can monitor the cleaning process in Django logs when processing forms.

## How It Works

### Example: User's Reported Issue
```
Input:  "YLE - 2021-1660 POLYMATH COLLEGE"

Step 1: Split into words
  → ["YLE", "-", "2021-1660", "POLYMATH", "COLLEGE"]

Step 2: Filter school words
  → ["YLE", "-", "2021-1660"]
  (Removed: "POLYMATH", "COLLEGE")

Step 3: Join and normalize
  → "YLE - 2021-1660"

Step 4: Fix spacing around dashes
  → "YLE-2021-1660"

Step 5: Validate and standardize with regex
  → Match: prefix="YLE", year="2021", number="1660"
  → Output: "YLE-2021-1660"
```

## Benefits

1. **Removes unwanted text** - Filters out school names from header/logo area
2. **Normalizes format** - Ensures consistent "PREFIX-YEAR-NUMBER" format
3. **Preserves data** - Keeps all relevant admission number parts
4. **Flexible pattern matching** - Works with various prefixes and number lengths
5. **Debug visibility** - Logs show before/after values for verification

## Testing Instructions

### 1. Run the standalone test:
```bash
python3 /Users/sas/Repos/PolymathYLE/test_admission_cleaning.py
```

### 2. Test with actual OCR service:
```python
from students.ocr_service import get_ocr_service

ocr = get_ocr_service()
result = ocr._clean_admission_number('YLE - 2021-1660 POLYMATH COLLEGE')
print(result)  # Output: YLE-2021-1660
```

### 3. Test end-to-end with form upload:
- Upload a scanned application form through the web interface
- Check the admission number field in the extracted data
- Review Django logs for cleaning messages

## Notes

- **Not committed** - As requested, changes are ready for testing but not committed to git
- **Backward compatible** - Already clean admission numbers pass through unchanged
- **Non-destructive** - Original data is logged before cleaning
- **Only affects admission_number** - Other fields remain unchanged

## File Locations

- **OCR Service**: `/Users/sas/Repos/PolymathYLE/students/ocr_service.py`
- **Test Script**: `/Users/sas/Repos/PolymathYLE/test_admission_cleaning.py`
- **This Document**: `/Users/sas/Repos/PolymathYLE/ADMISSION_NUMBER_FIX.md`

## Next Steps

1. Test with the actual form that had the issue
2. Verify the cleaning works in the web interface
3. Check Django logs for cleaning messages
4. If successful, commit the changes
5. Consider adding more school name patterns if needed
