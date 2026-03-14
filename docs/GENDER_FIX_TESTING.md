# Gender Checkbox Detection - Testing Guide

## Quick Test

Run this command with your scanned application form:

```bash
python test_gender_checkbox.py /path/to/your/scanned_form.jpg
```

## What to Look For

### 1. Correct Gender Extraction

**Expected on form**: MALE checkbox is ticked (☑MALE  ☐FEMALE)

**Expected output**:
```
GENDER FIELD:
  Value: MALE
  Confidence: HIGH
  Valid: True
  ✓ Extracted as MALE
```

### 2. Detection Logs

You should see detailed logs showing:

```
=== GENDER CHECKBOX DETECTION ===
Found MALE label: 'MALE' at x=..., y=...
Found FEMALE label: 'FEMALE' at x=..., y=...
  Checking for checkmarks near 'MALE'
  ✓ FOUND checkmark '...' at x=..., y=...
  Checking for checkmarks near 'FEMALE'
  ✗ No checkmark found near 'FEMALE'
MALE checkbox checked: True
FEMALE checkbox checked: False
DETECTED: MALE checkbox is marked
=== END GENDER CHECKBOX DETECTION ===
```

## Success Criteria

✅ **PASS** if:
- Gender is extracted as "MALE" when MALE checkbox is ticked
- Gender is extracted as "FEMALE" when FEMALE checkbox is ticked
- Logs show checkmark detection working correctly
- Confidence is "HIGH"
- Valid is "True"

❌ **FAIL** if:
- Wrong gender is extracted (e.g., MALE ticked but FEMALE extracted)
- No gender extracted when checkboxes are clear
- Confidence is "LOW" for clear checkboxes

## Debugging Failed Tests

### If wrong gender is extracted:

1. Check the logs for:
   ```
   Found MALE label: ...
   Found FEMALE label: ...
   ```
   - Are both labels detected?
   - Are the positions (x, y) reasonable?

2. Check checkmark detection:
   ```
   Checking for checkmarks near 'MALE'
   ```
   - Did it find a checkmark?
   - What symbol was detected?
   - What's the distance?

3. If no checkmark found:
   - Look at the raw OCR text (in logs or `_raw_text`)
   - Check what symbols appear near MALE/FEMALE
   - You may need to add that symbol to `checkmark_symbols` list

### If no gender extracted:

1. Check if MALE/FEMALE labels were found:
   ```
   No MALE or FEMALE labels found near gender field
   ```
   - OCR might not have detected the text
   - Check image quality

2. Check fallback detection:
   ```
   Using fallback gender detection
   ```
   - What heuristic was used?
   - Did it make a reasonable guess?

## Testing with Real Forms

### Test Case 1: MALE Checked
- **Form**: MALE checkbox ticked
- **Expected**: `gender: "MALE"`

### Test Case 2: FEMALE Checked
- **Form**: FEMALE checkbox ticked
- **Expected**: `gender: "FEMALE"`

### Test Case 3: Unclear/Both Checked
- **Form**: Both or neither checked (rare)
- **Expected**: Warning logged, fallback heuristic used

## Next Steps After Testing

### If test PASSES:
- ✅ The fix is working correctly
- You can now upload and process application forms
- Gender should be extracted accurately

### If test FAILS:
1. Share the log output
2. Share a screenshot of the form (if possible)
3. Note which checkmark symbols appear in the OCR text
4. We can adjust the detection logic accordingly

## Additional Notes

### Checkmark Symbols Detected

The system currently recognizes these symbols:
```
✓ ✗ ☑ ☐ ✔ √ V v X x / \ | * • ◆ ■ □
```

If your form uses a different symbol for checkmarks, it can be added to the list in `ocr_service.py` at line 1415.

### Spatial Detection Parameters

- **Left of label**: Searches 150px to the left of MALE/FEMALE text
- **Vertical alignment**: Within 1.5x label height
- **Nearby symbols**: Within 50px horizontally

These can be adjusted if needed based on your form layout.

---

**Ready to test!** Run the test script and check the results. 🚀
