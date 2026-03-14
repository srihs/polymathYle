# Gender Checkbox Detection Fix

## Problem Summary

The gender checkbox detection was returning the **wrong gender** even after previous fixes. The form uses:
- **Tick mark (✓)** for SELECTED checkbox
- **Cross mark (✗)** for UNSELECTED checkbox

**Example of the issue:**
- Form shows: MALE ✓ (tick), FEMALE ✗ (cross)
- OCR extracted: "Female" (WRONG)
- Should extract: "MALE" (correct)

## Root Cause

The previous implementation in `_has_checkmark_nearby()` method (lines 1439-1478) looked for ANY checkmark symbols including:
```python
checkmark_symbols = [
    '✓', '✗', '☑', '☐', '✔', '√', 'V', 'v',
    'X', 'x', '/', '\\', '|', '*', '•', '◆', '■', '□'
]
```

**Critical Issue:** The method treated BOTH tick marks (✓) AND cross marks (✗, X) as indicators of selection, when in reality:
- ✓ = SELECTED (positive indicator)
- ✗ = NOT SELECTED (negative indicator)

The code would find symbols near both labels and couldn't distinguish between "checked" and "unchecked" symbols.

## Solution Implemented

### 1. New Tick-Only Detection Strategy

Completely rewrote `_extract_checkbox_value()` method to:

**A. Focus ONLY on tick symbols (positive indicators):**
```python
tick_symbols = ['✓', '√', '✔', 'V', 'v']
```

**B. Ignore cross symbols completely:**
- Cross marks (✗, X, /, \) are NO LONGER considered
- They indicate "not selected" so we ignore them entirely

**C. Use distance-based assignment:**
```python
# For each tick symbol found:
male_distance = abs(word_x - male_bounds['x']) + abs(word_y - male_bounds['y'])
female_distance = abs(word_x - female_bounds['x']) + abs(word_y - female_bounds['y'])

# Assign to closest label (within 150px)
if male_distance < female_distance and male_distance < 150:
    male_tick_count += 1
elif female_distance < 150:
    female_tick_count += 1
```

**D. Make decision based on tick count:**
```python
if male_tick_count > female_tick_count:
    return 'MALE'
elif female_tick_count > male_tick_count:
    return 'FEMALE'
else:
    # Use fallback method
```

### 2. Enhanced Logging

Added comprehensive debug logging to show:
- All words detected near GENDER label
- MALE and FEMALE label positions
- Every tick symbol found and its distance to each label
- Tick count summary
- Final decision reasoning

**Example log output:**
```
================================================================================
GENDER DETECTION - DETAILED DEBUG
================================================================================
Gender label bounds: {'x': 200, 'y': 280, ...}

All words near GENDER label:
  Word: 'GENDER' at x=200, y=280
  Word: 'MALE' at x=450, y=280
    -> Identified as MALE label
  Word: 'FEMALE' at x=520, y=280
    -> Identified as FEMALE label

MALE label at: x=450, y=280
FEMALE label at: x=520, y=280

Searching for tick symbols: ['✓', '√', '✔', 'V', 'v']
Note: Cross marks (✗, X, /) are IGNORED - they indicate 'not selected'

Found tick symbol: '✓' at x=440, y=280
  Distance to MALE: 10px
  Distance to FEMALE: 80px
  -> Assigned to MALE

TICK COUNT SUMMARY:
MALE tick count: 1
FEMALE tick count: 0

DECISION: MALE (more ticks)

Final gender detection result: ['MALE']
================================================================================
```

### 3. Improved Fallback Detection

Enhanced `_detect_gender_fallback()` with:
- Symbol density analysis (count ALL symbols as last resort)
- Spatial ordering (which appears first/leftmost)
- Better decision logic with detailed logging

**Fallback strategies in order:**
1. **Single label found**: If only MALE or FEMALE label detected, return that one
2. **Symbol density**: Count all symbols near each label, prefer the one with more symbols
3. **Spatial ordering**: If symbol density is equal, prefer the leftmost label

## Files Modified

### `/Users/sas/Repos/PolymathYLE/students/ocr_service.py`

**Changed methods:**
1. `_extract_checkbox_value()` (lines 1301-1437)
   - Completely rewritten to focus on tick marks only
   - Added extensive debug logging
   - Uses distance-based tick assignment

2. `_has_checkmark_nearby()` (REMOVED)
   - Old method that treated all symbols equally
   - No longer needed with new approach

3. `_detect_gender_fallback()` (lines 1440-1534)
   - Enhanced with symbol density analysis
   - Better logging
   - Improved decision logic

## Testing Instructions

### Using the Test Script

Run the existing test script with your scanned form:

```bash
python test_gender_checkbox.py /path/to/application_form.jpg
```

**Expected output for MALE ✓, FEMALE ✗:**
```
================================================================================
EXTRACTION RESULTS
================================================================================

GENDER FIELD:
  Value: MALE
  Confidence: HIGH
  Valid: True
  ✓ Extracted as MALE
```

### Manual Testing Steps

1. **Test with MALE ticked:**
   - Form has: MALE ✓, FEMALE ✗
   - Expected result: "MALE"

2. **Test with FEMALE ticked:**
   - Form has: MALE ✗, FEMALE ✓
   - Expected result: "FEMALE"

3. **Check the logs:**
   - Look for "GENDER DETECTION - DETAILED DEBUG" section
   - Verify tick symbols are being detected
   - Verify distances are calculated correctly
   - Verify final decision matches the ticked checkbox

### Debugging Failed Cases

If gender detection still fails:

1. **Check if tick symbols are detected at all:**
   - Look for "Found tick symbol:" in logs
   - If no tick symbols found, OCR might not be detecting them
   - Try the fallback method

2. **Check distance calculations:**
   - Look for "Distance to MALE" and "Distance to FEMALE"
   - Verify the tick is being assigned to the correct label
   - If distances are wrong, labels might not be detected properly

3. **Check if both labels are found:**
   - Look for "Identified as MALE label" and "Identified as FEMALE label"
   - If one is missing, the label detection needs adjustment

## What Google Vision API Detects

Google Cloud Vision DOCUMENT_TEXT_DETECTION mode should detect:
- Text labels: "GENDER", "MALE", "FEMALE"
- Tick symbols: ✓, √, ✔ (may also detect as "V" or "v")
- Cross symbols: ✗, X (but we now ignore these)

**Important notes:**
- Tick marks may be detected as the letter "V" or "v"
- This is why we include 'V' and 'v' in the tick_symbols list
- Cross marks are explicitly ignored in the new implementation

## Performance Impact

- **No performance impact**: Same number of OCR API calls
- **Slightly more logging**: Debug logs are more verbose but only in INFO level
- **Better accuracy**: Simpler logic should be more reliable

## Rollback Plan

If this fix causes issues, revert to previous version by:
1. Using git to restore the old `ocr_service.py`
2. Previous version had the `_has_checkmark_nearby()` method

```bash
git diff students/ocr_service.py
git checkout HEAD~1 -- students/ocr_service.py
```

## Future Improvements

Potential enhancements if issues persist:

1. **Image preprocessing:**
   - Enhance checkbox area before OCR
   - Apply morphological operations to make tick marks clearer

2. **Checkbox region detection:**
   - Use OpenCV to detect checkbox boxes
   - Analyze the fill percentage of each box
   - Box with more black pixels = ticked

3. **Template matching:**
   - Create templates for ticked/unticked checkboxes
   - Use OpenCV template matching to detect checkbox states
   - More reliable than OCR symbol detection

4. **Machine learning approach:**
   - Train a small CNN to classify checkbox states
   - Input: cropped checkbox images
   - Output: "ticked" or "unticked"

## Summary

**Before fix:**
- Looked for ANY symbols (✓, ✗, X, V, etc.)
- Treated all symbols equally as "checked" indicators
- Couldn't distinguish tick from cross
- Result: Wrong gender selection

**After fix:**
- Looks ONLY for tick symbols (✓, √, ✔, V, v)
- Ignores cross symbols (✗, X) completely
- Uses distance to assign ticks to correct label
- Result: Correct gender selection based on tick marks

**Key insight:** The form design uses tick=selected, cross=unselected. By ignoring crosses and focusing only on ticks, we get the correct result.
