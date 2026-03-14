# Parent Field Extraction Fix

## Problem Description

**Critical Bug**: Father's contact number and occupation were being extracted from mother's section, even though father's name was correctly extracted.

### Evidence

From the scanned form:

**Mother's Information (Correct):**
- Name: Randika Chamali Samarajeewa ✓
- Contact: 0713888262 ✓
- Occupation: Manager Human Resources ✓

**Father's Information (Before Fix):**
- Name: K.G.A Daminda Nalaka ✓ (correct)
- Contact: 0713888262 ✗ (THIS IS MOTHER'S CONTACT!)
- Occupation: Manager Human Resources ✗ (THIS IS MOTHER'S OCCUPATION!)

**Expected from Form:**
```
FATHER'S NAME    K.G.A Daminda Nalaka
CONTACT NUMBER   0771656172
OCCUPATION       Merchant Navy (Seaman)
```

## Root Cause Analysis

The OCR extraction in `students/ocr_service.py` uses multiple strategies to find field values:

1. **Strategy 1**: Find words RIGHT of label (same line)
2. **Strategy 2**: Check words BELOW for multi-line fields
3. **Strategy 3**: Find words BELOW label (next line)
4. **Strategy 4**: Checkbox extraction for gender
5. **Strategy 5**: Section-aware extraction for parent fields
6. **Strategy 6**: Section-aware for WhatsApp number

### The Bug

**Strategy 5 (section-aware extraction) only ran IF Strategy 1 failed!**

```python
# OLD CODE (BUGGY) - Line 513-515
if field_name in ['mother_name', 'father_name', 'mother_occupation', 'father_occupation',
                  'mother_contact_number', 'father_contact_number']:
    if not value_words or len(value_words) == 0:  # ← ONLY IF STRATEGY 1 FAILED!
        # Section-aware extraction...
```

### What Was Happening

For `father_contact_number`:
1. Labels searched: `['CONTACT NUMBER', 'FATHER CONTACT', ...]`
2. **Strategy 1** found "CONTACT NUMBER" label
3. But it found the FIRST "CONTACT NUMBER" in the document (mother's at y=1250)
4. Strategy 1 returned "0713888262" (mother's contact)
5. **Strategy 5 was NEVER reached** because `value_words` was not empty!
6. Same issue for `father_occupation`

### Why Father's Name Was Correct

Father's name worked because:
- It has specific labels: `["FATHER'S FULL NAME", "FATHER'S NAME", "FATHER NAME"]`
- These are unique and don't appear in mother's section
- Strategy 1 correctly found father's name field

But contact and occupation use generic labels:
- `"CONTACT NUMBER"` - appears in BOTH sections
- `"OCCUPATION"` - appears in BOTH sections

## The Fix

### Solution: Force Section-Aware Extraction for Contact/Occupation Fields

For fields with generic labels that appear in multiple parent sections, we **SKIP generic strategies** and go **DIRECTLY to section-aware extraction**.

### Code Changes

**File**: `/Users/sas/Repos/PolymathYLE/students/ocr_service.py`

**Change 1**: Added early detection and forced section-aware extraction (lines 392-493)

```python
# CRITICAL FIX: For parent contact/occupation fields, SKIP generic strategies
# These fields have generic labels (CONTACT NUMBER, OCCUPATION) that appear in BOTH
# mother and father sections. Generic label matching will always find the FIRST occurrence
# (mother's section), which is WRONG for father fields.
#
# Solution: Use ONLY section-aware extraction (Strategy 5) for these fields
parent_contact_occupation_fields = [
    'mother_contact_number', 'father_contact_number',
    'mother_occupation', 'father_occupation'
]

if field_name in parent_contact_occupation_fields:
    logger.info(f"{'=' * 60}")
    logger.info(f"CRITICAL: {field_name} requires section-aware extraction")
    logger.info(f"Skipping generic strategies to prevent cross-contamination")
    logger.info(f"{'=' * 60}")

    # Determine parent type
    parent_prefix = 'FATHER' if field_name.startswith('father_') else 'MOTHER'

    # Find label (still needed for section boundary detection)
    # ... label finding code ...

    # Use ONLY section-aware extraction
    logger.info(f"Calling section-aware extraction for {parent_prefix}...")
    value_words = self._find_in_parent_section(words, label_bounds, parent_prefix, field_name)

    # Skip to final processing (label filtering and value assembly)
    # ... filtering and return value ...
```

**Change 2**: Updated Strategy 5 to only handle NAME fields (lines 616-625)

```python
# Strategy 5: For parent NAME fields only (contact/occupation handled separately above)
# Names can use section-aware extraction as a fallback
if field_name in ['mother_name', 'father_name']:
    if not value_words or len(value_words) == 0:
        parent_prefix = 'MOTHER' if 'mother' in field_name else 'FATHER'
        if is_parent_field:
            logger.info(f"Strategy 5 - Attempting section-aware extraction for {parent_prefix} NAME")
        value_words = self._find_in_parent_section(words, label_bounds, parent_prefix, field_name)
```

**Change 3**: Enhanced logging for all parent fields (not just father)

```python
# Extra debugging for parent fields
is_parent_field = 'mother' in field_name or 'father' in field_name
is_father_field = 'father' in field_name
```

## How Section-Aware Extraction Works

The `_find_in_parent_section()` method:

1. **Finds the parent section header**
   - Looks for "FATHER'S NAME" or "MOTHER'S NAME" as section start
   - Falls back to "FATHER" or "MOTHER" if specific name field not found

2. **Determines section boundaries**
   - Start: Y-coordinate of parent section header
   - End: Y-coordinate of next major section
   - For MOTHER: Ends at FATHER section
   - For FATHER: Ends at CONTACT INFORMATION, HOME ADDRESS, etc.

3. **Searches for field label WITHIN section**
   - For contact: Looks for "CONTACT", "NUMBER", "TEL", "PHONE"
   - For occupation: Looks for "OCCUPATION"
   - Only considers labels within the section boundaries

4. **Extracts value relative to section-specific label**
   - Finds words RIGHT of the label (same line)
   - Falls back to words BELOW if needed
   - Filters to only include words within section boundaries

## Expected Results After Fix

**Mother's Information:**
- Name: Randika Chamali Samarajeewa ✓
- Contact: 0713888262 ✓
- Occupation: Manager Human Resources ✓

**Father's Information:**
- Name: K.G.A Daminda Nalaka ✓
- Contact: 0771656172 ✓ (CORRECTED - was 0713888262)
- Occupation: Merchant Navy (Seaman) ✓ (CORRECTED - was Manager Human Resources)

## Debug Logging Output

When extracting `father_contact_number`, you should now see:

```
============================================================
CRITICAL: father_contact_number requires section-aware extraction
Skipping generic strategies to prevent cross-contamination
============================================================
Found label 'CONTACT NUMBER' at y=1350
Calling section-aware extraction for FATHER...
=== PARENT SECTION EXTRACTION for FATHER ===
Field name: father_contact_number
Found FATHER's NAME field at index 45: 'FATHER' at y=1300
FATHER section boundaries: start_y=1300, end_y=1500
Searching for 'CONTACT' label within section boundaries...
Found 'CONTACT' label in FATHER section: 'CONTACT' at y=1350
Words right of 'CONTACT' label: ['0771656172']
After section filtering: 1 value words: ['0771656172']
FINAL VALUE for father_contact_number: '0771656172'
============================================================
```

## Testing Instructions

1. **Run the test script**:
   ```bash
   python3 test_parent_field_fix.py
   ```

2. **Verify output shows**:
   - Section-aware extraction being used for contact/occupation
   - Correct values extracted from correct sections
   - Y-coordinates prove data is from right section

3. **Check verification results**:
   ```
   ✓ PASS - mother_contact_number
   ✓ PASS - mother_occupation
   ✓ PASS - father_contact_number
   ✓ PASS - father_occupation
   ```

## Impact Assessment

**Fields Affected**:
- `mother_contact_number`
- `mother_occupation`
- `father_contact_number`
- `father_occupation`

**Fields NOT Affected**:
- `mother_name` - Uses unique labels, generic strategies work fine
- `father_name` - Uses unique labels, generic strategies work fine
- All student fields - No duplicate sections
- Other fields - Unaffected

**Performance Impact**:
- Minimal - Section-aware extraction is already implemented
- Actually FASTER for these fields (skips Strategy 1-4)
- More accurate by design

## Related Files

- `/Users/sas/Repos/PolymathYLE/students/ocr_service.py` - Main OCR service (FIXED)
- `/Users/sas/Repos/PolymathYLE/test_parent_field_fix.py` - Test script
- `/Users/sas/Repos/PolymathYLE/students/views.py` - Uses OCR service

## Commit Message

```
Fix critical bug in parent field extraction

PROBLEM:
Father's contact number and occupation were being extracted from
mother's section, even though father's name was correct.

ROOT CAUSE:
Generic strategies (Strategy 1-4) were running BEFORE section-aware
extraction (Strategy 5). For fields with generic labels like
"CONTACT NUMBER" and "OCCUPATION" that appear in BOTH mother and
father sections, Strategy 1 would find the FIRST occurrence
(mother's section) and return it, preventing Strategy 5 from running.

SOLUTION:
For parent contact/occupation fields, SKIP generic strategies and
go DIRECTLY to section-aware extraction. This ensures we find the
correct "CONTACT NUMBER" or "OCCUPATION" label WITHIN the specific
parent's section.

CHANGES:
- Force section-aware extraction for: mother_contact_number,
  father_contact_number, mother_occupation, father_occupation
- Update Strategy 5 to only handle parent NAME fields as fallback
- Enhanced logging for all parent fields (not just father)

IMPACT:
- Father's contact now extracts "0771656172" (correct)
  instead of "0713888262" (mother's)
- Father's occupation now extracts "Merchant Navy (Seaman)" (correct)
  instead of "Manager Human Resources" (mother's)
- Mother's fields remain correct
- All other fields unaffected

TESTING:
Run: python3 test_parent_field_fix.py
```

## Next Steps

1. Test with the actual scanned form that showed the issue
2. Verify all 4 fields extract correctly:
   - mother_contact_number: 0713888262
   - mother_occupation: Manager Human Resources
   - father_contact_number: 0771656172
   - father_occupation: Merchant Navy (Seaman)
3. Check logs show section-aware extraction is being used
4. Test with multiple different scanned forms
5. If all tests pass, commit the fix
