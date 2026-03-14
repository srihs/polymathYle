# Section Boundary Detection - Visual Diagram

## Before Fix (INCORRECT)

```
┌─────────────────────────────────────────────────┐
│  PERSONAL INFORMATION: FAMILY                   │
├─────────────────────────────────────────────────┤
│                                                 │
│  MOTHER'S NAME: Randika Chamali Samarajewa     │ ← MOTHER section starts (y=1000)
│  CONTACT NUMBER: 0719 888262                    │
│  OCCUPATION: Manager Human Resources            │
│                                                 │ ← MOTHER section ends at FATHER (y=1200)
├─────────────────────────────────────────────────┤
│                                                 │
│  FATHER'S NAME: K.G.A Daminda Nalaka           │ ← FATHER section starts (y=1200)
│  CONTACT NUMBER: 0771656172                     │
│  OCCUPATION: Merchant Navy (Seaman)             │
│                                                 │
│                                                 │
│                                                 │ ← FATHER section should end here
├─────────────────────────────────────────────────┤
│  CONTACT INFORMATION                            │ ← But actually extends to here (y=1700)
│  HOME ADDRESS: ...                              │   (500px default)
│  WHATSAPP NUMBER: ...                           │
└─────────────────────────────────────────────────┘

PROBLEM:
- MOTHER section: y=1000 to y=1200 ✓ CORRECT
  (ends at FATHER keyword)

- FATHER section: y=1200 to y=1700 ✗ WRONG
  (extends full 500px because MOTHER keyword at y=1000
   fails the condition: word['bounds']['y'] > section_start_y
   since 1000 < 1200 is FALSE)

RESULT: Father section includes too much, potentially wrong data
```

## After Fix (CORRECT)

```
┌─────────────────────────────────────────────────┐
│  PERSONAL INFORMATION: FAMILY                   │
├─────────────────────────────────────────────────┤
│                                                 │
│  MOTHER'S NAME: Randika Chamali Samarajewa     │ ← MOTHER section starts (y=1000)
│  CONTACT NUMBER: 0719 888262                    │ ← Extract from here
│  OCCUPATION: Manager Human Resources            │ ← Extract from here
│                                                 │
│                                                 │ ← MOTHER section ends at FATHER (y=1200)
├─────────────────────────────────────────────────┤
│                                                 │
│  FATHER'S NAME: K.G.A Daminda Nalaka           │ ← FATHER section starts (y=1200)
│  CONTACT NUMBER: 0771656172                     │ ← Extract from here ✓
│  OCCUPATION: Merchant Navy (Seaman)             │ ← Extract from here ✓
│                                                 │
│                                                 │ ← FATHER section ends at next section (y=1400)
├─────────────────────────────────────────────────┤
│  CONTACT INFORMATION                            │ ← Next section marker found
│  HOME ADDRESS: ...                              │
│  WHATSAPP NUMBER: ...                           │
└─────────────────────────────────────────────────┘

SOLUTION:
- MOTHER section: y=1000 to y=1200 ✓ CORRECT
  (ends at FATHER keyword which comes AFTER mother)

- FATHER section: y=1200 to y=1400 ✓ CORRECT
  (ends at "CONTACT INFORMATION" section which comes AFTER father)

RESULT: Father section contains only father's fields
```

## Section Detection Strategy

### Mother Section:
```python
# Find MOTHER keyword/field
mother_y = find_mother_name_field()  # e.g., y=1000

# Section boundaries
section_start_y = mother_y  # 1000
section_end_y = find_next_keyword_after(mother_y, ['FATHER', ...])  # 1200

# Extract fields within: y=1000 to y=1200
# ✓ Includes: MOTHER'S NAME, CONTACT NUMBER, OCCUPATION
```

### Father Section:
```python
# Find FATHER keyword/field
father_y = find_father_name_field()  # e.g., y=1200

# Section boundaries
section_start_y = father_y  # 1200
# DON'T look for MOTHER (it's before, at y=1000)
# INSTEAD look for sections that come AFTER father
section_end_y = find_next_keyword_after(father_y, [
    'CONTACT INFORMATION',  # Typically after family section
    'HOME ADDRESS',
    'STUDENT INFORMATION',
    'SIBLINGS',
    ...
])  # e.g., 1400

# Extract fields within: y=1200 to y=1400
# ✓ Includes: FATHER'S NAME, CONTACT NUMBER, OCCUPATION
```

## Key Differences

| Aspect | Before Fix | After Fix |
|--------|------------|-----------|
| **Section Detection** | Any word containing "FATHER"/"MOTHER" | Looks for "FATHER'S NAME"/"MOTHER'S NAME" field |
| **MOTHER Boundary** | Looks for FATHER (after) ✓ | Same ✓ |
| **FATHER Boundary** | Looks for MOTHER (before) ✗ | Looks for next section (after) ✓ |
| **Boundary Logic** | `y > section_start_y` fails for MOTHER | Separate logic for MOTHER vs FATHER |
| **Father Section Size** | Too large (500px default) | Precise (ends at next section) |
| **Cross-contamination** | Father gets mother's data | Each parent gets own data ✓ |

## Example Log Output

### Before Fix (WRONG):
```
INFO: Found FATHER word at index 25: 'FATHER'S' at y=1200
INFO: Section boundaries: start_y=1200, end_y=1700
INFO: Searching for 'CONTACT' label...
INFO: Found 'CONTACT' label at y=1050  ← This is MOTHER'S contact!
INFO: Extracted value: '0719888262'    ← WRONG - mother's number
```

### After Fix (CORRECT):
```
INFO: Found FATHER's NAME field at index 25: 'FATHER'S' at y=1200
INFO: Section boundary found: 'CONTACT' at y=1400
INFO: Final section boundaries: start_y=1200, end_y=1400
INFO: Total words in FATHER section: 12
INFO: Searching for 'CONTACT' label within section...
INFO: Found 'CONTACT' label in FATHER section at y=1250
INFO: Extracted value: '0771656172'    ← CORRECT - father's number
```

## Spatial Coordinates Explanation

OCR text extraction provides bounding boxes with coordinates:
- **x**: Horizontal position (left to right)
- **y**: Vertical position (top to bottom)
- **x_end, y_end**: Bottom-right corner of bounding box

### Vertical Positioning (y-axis):
```
y=0    ┌─────────────────────┐
       │   PAGE TOP          │
y=500  ├─────────────────────┤
       │   HEADER            │
y=1000 ├─────────────────────┤
       │   MOTHER SECTION    │ ← section_start_y = 1000
y=1050 │   - CONTACT: 0719.. │
y=1100 │   - OCCUPATION: ... │
y=1200 ├─────────────────────┤
       │   FATHER SECTION    │ ← section_start_y = 1200
y=1250 │   - CONTACT: 0771.. │ ← This should match
y=1300 │   - OCCUPATION: ... │
y=1400 ├─────────────────────┤ ← section_end_y = 1400
       │   NEXT SECTION      │
y=1500 │   ...               │
       └─────────────────────┘
```

### How Section Filtering Works:
```python
# For father_contact_number, we need y in range [1200, 1400]

# All words in document
words = [
    {'text': 'CONTACT', 'y': 1050},  # MOTHER's - excluded (1050 < 1200)
    {'text': '0719888262', 'y': 1060},  # MOTHER's - excluded (1060 < 1200)
    {'text': 'FATHER'S', 'y': 1200},  # FATHER - included
    {'text': 'CONTACT', 'y': 1250},  # FATHER's - included ✓
    {'text': '0771656172', 'y': 1260},  # FATHER's - included ✓
    {'text': 'CONTACT', 'y': 1450},  # Next section - excluded (1450 > 1400)
]

# Filter to father section
section_words = [
    w for w in words
    if section_start_y <= w['y'] <= section_end_y  # 1200 <= y <= 1400
]
# Result: Only FATHER's CONTACT and number are included!
```

## Summary

The fix ensures that:
1. Each parent (MOTHER/FATHER) has a clearly defined section
2. Section boundaries are based on actual form structure
3. Fields are extracted only from the correct parent's section
4. No cross-contamination between similar field labels
5. Extensive logging helps diagnose any future issues
