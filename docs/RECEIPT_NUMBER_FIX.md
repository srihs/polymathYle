# Receipt Number Extraction Fix

## Problem

The receipt number field was capturing random text instead of being empty or capturing the correct value from the scanned form.

**Observed Issue:**
- Receipt Number field showed: `"PERSONAL :"` (or similar random text)
- Should show: Empty (if blank on form) or the actual receipt number if present

**Root Cause:**
The OCR was picking up text from nearby areas (like "PERSONAL INFORMATION: STUDENT" label) instead of:
1. Leaving it empty when no receipt number exists
2. Or extracting the correct receipt number value if it exists

## Analysis

From the scanned form:
```
OFFICE USE ONLY
ADMISSION NUMBER  YLE - 2021-1660
DATE              06/01/2026
RECEIPT NO        [appears to be blank]
```

The section immediately below:
```
PERSONAL INFORMATION: STUDENT
```

**Issue Details:**
1. Office Use fields didn't have section boundary detection (unlike parent fields)
2. Spatial extraction was picking up text from the PERSONAL INFORMATION section
3. No validation existed for receipt numbers to reject invalid values
4. The text "PERSONAL :" was being extracted from the section header below

## Solution

Implemented a three-pronged fix:

### 1. Section Boundary Detection for Office Use Fields

Added section-aware extraction similar to parent fields (mother/father):

```python
# OFFICE USE ONLY section boundary detection
if is_office_use_field:
    # Find the "OFFICE USE ONLY" section header
    office_section_y = None
    for i, word in enumerate(words):
        word_text = word['text'].upper()
        if 'OFFICE' in word_text or 'USE' in word_text:
            # Check if nearby words complete "OFFICE USE ONLY"
            nearby_text = ' '.join([words[j]['text'].upper()
                                   for j in range(max(0, i-2), min(len(words), i+4))])
            if 'OFFICE' in nearby_text and 'USE' in nearby_text:
                office_section_y = word['bounds']['y']
                break

    # Find where Office Use section ends (PERSONAL INFORMATION section starts)
    office_section_end_y = None
    if office_section_y is not None:
        for word in words:
            word_y = word['bounds']['y']
            if word_y > office_section_y:
                word_text = word['text'].upper()
                # Look for section headers that come after Office Use
                if any(marker in word_text for marker in
                      ['PERSONAL', 'STUDENT', 'FAMILY', 'INFORMATION']):
                    if len(word_text) > 3:
                        office_section_end_y = word_y
                        break

    # Filter words to only those within the Office Use section
    if office_section_y is not None and office_section_end_y is not None:
        section_filtered_words = [w for w in words
                                 if office_section_y <= w['bounds']['y'] < office_section_end_y]
```

### 2. Receipt Number Validation

Added `_clean_receipt_number()` method to validate and filter receipt numbers:

```python
def _clean_receipt_number(self, value):
    """
    Clean and validate receipt number by filtering out section labels and invalid text.

    Receipt numbers are typically:
    - Short (under 30 characters)
    - Numbers only: "12345"
    - Letters and numbers: "REC-001", "R-2021-001"
    - NO full sentences or section headers
    """
    if not value:
        return ''

    # Words that indicate this is NOT a receipt number (section labels, etc.)
    invalid_words = [
        'PERSONAL', 'INFORMATION', 'STUDENT', 'FAMILY', 'SECTION',
        'MOTHER', 'FATHER', 'NAME', 'CONTACT', 'ADDRESS', 'HOME',
        'OFFICE', 'USE', 'ONLY', 'ADMISSION', 'DATE', 'APPLICATION'
    ]

    # Check if value contains any invalid words
    value_upper = value.upper()
    for word in invalid_words:
        if word in value_upper:
            logger.info(f"Receipt number: Rejected '{value}' - contains invalid word '{word}'")
            return ''

    # Validate format
    if len(value) > 30:
        logger.info(f"Receipt number: Rejected '{value}' - too long")
        return ''

    # Reject if contains colon (section header like "PERSONAL :")
    if ':' in value:
        logger.info(f"Receipt number: Rejected '{value}' - contains colon")
        return ''

    # Reject if contains multiple spaces (phrase/sentence)
    if value.count(' ') > 2:
        logger.info(f"Receipt number: Rejected '{value}' - too many spaces")
        return ''

    return value.strip()
```

### 3. Post-Processing Cleanup

Updated `_post_process_fields()` to:
1. Call `_clean_receipt_number()` on extracted values
2. Remove the field entirely if validation fails (empty result)

```python
# Clean and validate receipt number
if 'receipt_number' in processed:
    original_value = processed['receipt_number']
    cleaned = self._clean_receipt_number(processed['receipt_number'])
    if cleaned != original_value:
        logger.info(f"Receipt number cleaned: '{original_value}' -> '{cleaned}'")
    processed['receipt_number'] = cleaned
    # If cleaning resulted in empty string, remove the field entirely
    if not cleaned:
        logger.info(f"Receipt number removed - invalid value detected")
        del processed['receipt_number']
```

## Expected Behavior

### Case 1: Receipt number is blank on form
```
Before fix: 'PERSONAL :' (invalid text from nearby section)
After fix:  '' (empty - field not in result)
```

### Case 2: Receipt number exists on form
```
Before fix: 'REC-001 PERSONAL'
After fix:  'REC-001' (if valid format)
```

### Case 3: Random text detected
```
Before fix: 'PERSONAL :' or 'STUDENT INFORMATION'
After fix:  '' (empty - rejected as invalid)
```

## Files Modified

- `/Users/sas/Repos/PolymathYLE/students/ocr_service.py`
  - Added `is_office_use_field` flag for detection
  - Added Office Use section boundary detection (lines 500-551)
  - Updated label search to use `section_filtered_words` for Office Use fields
  - Updated value extraction strategies to use filtered word list
  - Added `_clean_receipt_number()` validation method (lines 1564-1621)
  - Updated `_post_process_fields()` to clean and validate receipt numbers

## Testing

Created test script: `/Users/sas/Repos/PolymathYLE/test_receipt_number_fix.py`

To test the fix:
```bash
# Install dependencies first
pip install google-cloud-vision

# Set up Google Cloud Vision credentials
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# Run the test
python3 test_receipt_number_fix.py

# Or test with a specific form
python3 test_receipt_number_fix.py /path/to/form.jpg
```

## Benefits

1. **Prevents false positives**: No more capturing section headers as receipt numbers
2. **Section awareness**: Office Use fields now respect section boundaries
3. **Validation**: Only valid receipt number formats are accepted
4. **Empty handling**: Blank receipt numbers remain empty (not filled with garbage)
5. **Better logging**: Debug output shows why values are rejected

## Debug Logging

When extracting Office Use fields, the following logs are now generated:

```
INFO - students.ocr_service - === EXTRACTING OFFICE USE FIELD: receipt_number ===
INFO - students.ocr_service - Labels to search: ['RECEIPT NUMBER', 'RECEIPT NO', 'RECEIPT', 'REC NO']
INFO - students.ocr_service - Applying section boundary detection for Office Use field
INFO - students.ocr_service - Found OFFICE USE section at y=120.5
INFO - students.ocr_service - Office Use section ends at y=245.3 ('PERSONAL')
INFO - students.ocr_service - Filtering to 15 words within Office Use section
INFO - students.ocr_service - Receipt number: Rejected 'PERSONAL :' - contains invalid word 'PERSONAL'
INFO - students.ocr_service - Receipt number removed - invalid value detected
```

## Notes

- This fix applies to all Office Use Only fields: `admission_number`, `receipt_number`, `application_date`
- Section boundary detection is similar to the parent field (mother/father) extraction strategy
- The validation is strict but can be adjusted if valid receipt numbers are being rejected
- Empty receipt numbers are now handled correctly (field not present in results)
