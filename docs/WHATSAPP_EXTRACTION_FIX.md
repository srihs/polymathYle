# WhatsApp Number Extraction Fix

## Problem Summary

The WhatsApp number was not being extracted correctly from scanned application forms. The WhatsApp number appears in the "HOME ADDRESS" / "Contact Information" section of the form, separate from the student personal information fields.

## Root Cause

The OCR service had basic WhatsApp label patterns but lacked:
1. **Section-aware extraction** - WhatsApp appears in the Contact Information section, not at the top level
2. **Comprehensive label patterns** - Missing common variations like "WHATSAPP NO", "W/A NUMBER", etc.
3. **Spatial extraction logic** - No special handling for fields within the Contact/Address section
4. **Debugging visibility** - Limited logging for troubleshooting extraction issues

## Changes Made

### 1. Enhanced WhatsApp Label Patterns

**File:** `/Users/sas/Repos/PolymathYLE/students/ocr_service.py`

**Before:**
```python
'whatsapp_number': [
    'WHATSAPP NUMBER', 'WHATSAPP', 'WHATS APP', 'WA NUMBER'
],
```

**After:**
```python
'whatsapp_number': [
    'WHATSAPP NUMBER', 'WHATSAPP NO', 'WHATS APP NUMBER', 'WHATS APP NO',
    'WHATSAPP', 'WHATS APP', 'WA NUMBER', 'WA NO', 'W/A NUMBER'
],
```

Added patterns:
- "WHATSAPP NO" (common abbreviation)
- "WHATS APP NUMBER" (with space)
- "WHATS APP NO" (with space + abbreviation)
- "WA NO" (short abbreviation)
- "W/A NUMBER" (with slash notation)

### 2. Section-Aware Extraction Logic

Added two new methods to handle WhatsApp number extraction within the Contact Information section:

#### `_find_in_contact_section()`
- Locates the "HOME ADDRESS" or "CONTACT INFORMATION" section header
- Determines section boundaries (start to end of section)
- Searches for WhatsApp label within that section
- Extracts value using spatial extraction (right of label or below)
- Filters results to only phone-number-like values

#### `_find_whatsapp_anywhere()`
- Fallback method when section-based search fails
- Searches entire document for WhatsApp label
- Uses pattern matching to find nearby phone numbers
- Returns phone number words adjacent to WhatsApp label

### 3. Enhanced Extraction Strategy

**Updated:** `_extract_field_value_spatial()` method

Added **Strategy 6** for WhatsApp number:
```python
# Strategy 6: For WhatsApp number in Contact Information section
if field_name == 'whatsapp_number':
    if not value_words or len(value_words) == 0:
        value_words = self._find_in_contact_section(words, label_bounds, field_name)
```

This runs after the standard spatial extraction strategies and provides section-aware context.

### 4. Improved Debug Logging

Added comprehensive logging at INFO level for WhatsApp extraction:

- Logs when extraction starts with label patterns
- Logs section detection ("Found Contact Information section at y=...")
- Logs WhatsApp label detection
- Logs extraction attempts (right of label, below label)
- Logs phone number filtering
- Logs success/failure with extracted value
- Logs warnings when extraction fails

### 5. Dedicated Test Script

**New file:** `/Users/sas/Repos/PolymathYLE/test_whatsapp_extraction.py`

Features:
- Focused testing for WhatsApp number extraction
- Shows all label patterns being searched
- Displays detailed extraction logs
- Shows confidence scores and validation results
- Provides debugging tips if extraction fails
- Shows all other extracted fields for context

## Verification

### Already Confirmed Working:
- `application_date` - Already in FIELD_LABELS (line 52-54)
- `receipt_number` - Already in FIELD_LABELS (line 49-51)
- `age` - Already in FIELD_LABELS (line 69-71) with special handling to preserve short numeric values (line 495-497)

### Testing Instructions

1. **Test with your scanned form:**
   ```bash
   python test_whatsapp_extraction.py /path/to/your/scanned_form.jpg
   ```

2. **Watch for these log messages:**
   - "Starting extraction for whatsapp_number with labels: [...]"
   - "Found Contact Information section at y=..."
   - "Found WHATSAPP label in Contact section at y=..."
   - "WhatsApp - right of label: [...]"
   - "WhatsApp - after phone filtering: [...]"
   - "Successfully extracted whatsapp_number: 0123456789"

3. **Expected output:**
   ```
   ✓ WhatsApp Number FOUND: 0712345678
     Confidence: HIGH
     Valid: True
     ✓ Looks good!
   ```

## How It Works

### Extraction Flow for WhatsApp Number

1. **Label Search:** Looks for WhatsApp label patterns in FIELD_LABELS
2. **Section Detection:** Finds "HOME ADDRESS" or "CONTACT INFORMATION" section
3. **Section Boundaries:** Determines where the section starts and ends
4. **Label in Section:** Searches for WhatsApp label within that section only
5. **Spatial Extraction:**
   - First tries: words to the right of label (same line)
   - Then tries: words below the label (next line)
6. **Phone Filtering:** Keeps only words that look like phone numbers (digits, spaces, dashes)
7. **Fallback:** If section-based fails, searches entire document
8. **Post-processing:** Cleans phone number format (removes spaces, ensures 0-prefix)

### Section-Aware Detection

The Contact Information section is identified by:
- Section headers: "CONTACT INFORMATION", "HOME ADDRESS", "CONTACT DETAILS", "ADDRESS"
- Section boundaries: From header to next major section (MOTHER, FATHER, PARENT, etc.)
- Default section height: 600px (larger than parent sections due to address field)

### Phone Number Pattern Matching

WhatsApp values are validated as phone numbers:
```python
# Matches digits with optional spaces/dashes
re.match(r'^[\d\s\-\+]+$', word_text)

# Or starts with Sri Lankan prefixes
word_text.startswith('0') or word_text.startswith('+94')
```

## Debugging Tips

If WhatsApp number still not extracted:

1. **Check the raw OCR text** - Is "WHATSAPP" visible in the text?
2. **Check section detection** - Look for "Found Contact Information section" log
3. **Check label detection** - Look for "Found WHATSAPP label in Contact section" log
4. **Check spatial extraction** - Look for "WhatsApp - right of label:" or "below label:" logs
5. **Check image quality** - Is the WhatsApp label clearly legible? Is the number clearly written?
6. **Try the test script** - Use `test_whatsapp_extraction.py` for detailed debugging

## Files Modified

1. `/Users/sas/Repos/PolymathYLE/students/ocr_service.py`
   - Enhanced WhatsApp label patterns (line 119-122)
   - Added Strategy 6 for WhatsApp in Contact section (line 489-494)
   - Added `_find_in_contact_section()` method (line 762-865)
   - Added `_find_whatsapp_anywhere()` fallback method (line 867-922)
   - Enhanced logging for critical fields (line 329-350)

## Files Created

1. `/Users/sas/Repos/PolymathYLE/test_whatsapp_extraction.py`
   - Dedicated test script for WhatsApp extraction
   - Shows label patterns, extraction logs, and results
   - Provides debugging tips

## Next Steps

1. **Test with actual scanned form** - Run the test script with your form image
2. **Review extraction logs** - Check if section and label are detected
3. **Verify extracted value** - Confirm the number is correct
4. **If still failing** - Check image quality and handwriting clarity
5. **After successful test** - Commit changes if approved

## Related Fields Also Fixed/Verified

- ✅ `application_date` - Already working (Office Use section)
- ✅ `receipt_number` - Already working (Office Use section)
- ✅ `age` - Already working (Student Information, with short value preservation)

These fields use the standard spatial extraction and are already configured correctly in FIELD_LABELS.
