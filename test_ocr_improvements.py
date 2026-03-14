#!/usr/bin/env python
"""
Test script for OCR improvements
Tests the enhanced spatial extraction and validation features
"""

import os
import sys
import json
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'polymathyle.settings')
import django
django.setup()

from students.ocr_service import get_ocr_service, extract_application_data


def print_separator():
    print("\n" + "=" * 80 + "\n")


def test_ocr_service_availability():
    """Test if OCR service is properly configured"""
    print("TEST 1: OCR Service Availability")
    print_separator()

    service = get_ocr_service()
    if service.is_available():
        print("✓ OCR service is available and configured")
        print("✓ Google Cloud Vision credentials are valid")
        return True
    else:
        print("✗ OCR service is NOT available")
        print("✗ Please configure GOOGLE_APPLICATION_CREDENTIALS")
        print("\nSetup instructions:")
        print("1. Set environment variable:")
        print("   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json")
        print("2. Or add to .env file:")
        print("   GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json")
        return False


def test_date_parsing():
    """Test improved date parsing with OCR error correction"""
    print("TEST 2: Date Parsing with OCR Error Correction")
    print_separator()

    service = get_ocr_service()

    test_cases = [
        # (input, expected_output, description)
        ("01/12/2017", "2017-12-01", "Standard DD/MM/YYYY format"),
        ("O1/I2/2OI7", "2017-12-01", "OCR errors: O→0, I→1"),
        ("01-12-2017", "2017-12-01", "Dash separator"),
        ("2017/12/01", "2017-12-01", "YYYY/MM/DD format"),
        ("1/12/2017", "2017-12-01", "Single digit day"),
        ("01122017", "2017-12-01", "No separators"),
        ("yyyy", None, "Placeholder text - should be rejected"),
        ("dd/mm/yyyy", None, "Placeholder text - should be rejected"),
        ("32/13/2025", None, "Invalid date - should be rejected"),
    ]

    passed = 0
    failed = 0

    for input_date, expected, description in test_cases:
        result = service._parse_date(input_date)
        status = "✓" if result == expected else "✗"

        if result == expected:
            passed += 1
        else:
            failed += 1

        print(f"{status} {description}")
        print(f"   Input: {input_date}")
        print(f"   Expected: {expected}")
        print(f"   Got: {result}")
        print()

    print(f"Results: {passed} passed, {failed} failed")
    return failed == 0


def test_field_confidence():
    """Test confidence scoring for different field types"""
    print("TEST 3: Field Confidence Scoring")
    print_separator()

    service = get_ocr_service()

    test_cases = [
        # (field_name, value, expected_confidence, expected_valid)
        ("date_of_birth", "01/12/2017", "HIGH", True),
        ("date_of_birth", "yyyy", "LOW", False),
        ("mother_contact_number", "0719888262", "HIGH", True),
        ("mother_contact_number", "719888262", "LOW", False),
        ("gender", "FEMALE", "HIGH", True),
        ("gender", "F", "MEDIUM", False),
        ("age", "08", "HIGH", True),
        ("age", "25", "LOW", False),
        ("admission_number", "YLE-2021-1660", "HIGH", True),
        ("admission_number", "YLE-1660", "MEDIUM", False),
    ]

    passed = 0
    failed = 0

    for field_name, value, expected_conf, expected_valid in test_cases:
        confidence = service._calculate_field_confidence(field_name, value)
        is_valid = service._validate_field_value(field_name, value)

        conf_match = confidence == expected_conf
        valid_match = is_valid == expected_valid
        status = "✓" if (conf_match and valid_match) else "✗"

        if conf_match and valid_match:
            passed += 1
        else:
            failed += 1

        print(f"{status} {field_name}: {value}")
        print(f"   Expected: Confidence={expected_conf}, Valid={expected_valid}")
        print(f"   Got: Confidence={confidence}, Valid={is_valid}")
        print()

    print(f"Results: {passed} passed, {failed} failed")
    return failed == 0


def test_label_detection():
    """Test that label text is correctly identified"""
    print("TEST 4: Label Text Detection")
    print_separator()

    service = get_ocr_service()

    test_cases = [
        # (text, is_label, description)
        ("DATE OF BIRTH", True, "Field label"),
        ("MOTHER'S NAME", True, "Field label with apostrophe"),
        ("01/12/2017", False, "Date value"),
        ("Sinhalese", False, "Nationality value"),
        ("CONTACT NUMBER:", True, "Label ending with colon"),
        ("K.G.A Leon Nimshan", False, "Name value"),
        ("GENDER MALE FEMALE", True, "Multiple label indicators"),
    ]

    passed = 0
    failed = 0

    for text, expected_is_label, description in test_cases:
        result = service._is_label_text(text)
        status = "✓" if result == expected_is_label else "✗"

        if result == expected_is_label:
            passed += 1
        else:
            failed += 1

        print(f"{status} {description}")
        print(f"   Text: {text}")
        print(f"   Expected is_label: {expected_is_label}")
        print(f"   Got is_label: {result}")
        print()

    print(f"Results: {passed} passed, {failed} failed")
    return failed == 0


def test_with_sample_image(image_path):
    """Test extraction with an actual image file"""
    print("TEST 5: Actual Image Extraction")
    print_separator()

    if not os.path.exists(image_path):
        print(f"✗ Image file not found: {image_path}")
        print("  Please provide a path to a scanned application form")
        return False

    print(f"Processing image: {image_path}")
    print()

    result = extract_application_data(image_path)

    if not result['success']:
        print(f"✗ Extraction failed: {result.get('error')}")
        return False

    fields = result['fields']
    metadata = fields.get('_extraction_metadata', {})

    print(f"✓ Extraction successful!")
    print(f"  Total words detected: {metadata.get('total_words_detected', 'N/A')}")
    print(f"  Total blocks detected: {metadata.get('total_blocks_detected', 'N/A')}")
    print(f"  Fields extracted: {metadata.get('fields_extracted', 'N/A')}")
    print()

    # Display extracted fields with confidence
    print("Extracted Fields:")
    print("-" * 80)

    for field_name, value in fields.items():
        if field_name.startswith('_'):
            continue

        confidence = fields.get(f'_{field_name}_confidence', 'N/A')
        is_valid = fields.get(f'_{field_name}_valid', 'N/A')

        # Format display
        conf_symbol = {
            'HIGH': '✓✓',
            'MEDIUM': '✓',
            'LOW': '⚠',
            'N/A': '?'
        }.get(confidence, '?')

        valid_symbol = '✓' if is_valid else '✗'

        print(f"{conf_symbol} {field_name}:")
        print(f"   Value: {value}")
        print(f"   Confidence: {confidence} | Valid: {is_valid}")
        print()

    # Highlight fields that need review
    needs_review = []
    for field_name, value in fields.items():
        if field_name.startswith('_'):
            continue

        confidence = fields.get(f'_{field_name}_confidence')
        is_valid = fields.get(f'_{field_name}_valid')

        if confidence == 'LOW' or not is_valid:
            needs_review.append(f"{field_name}: {value}")

    if needs_review:
        print("\n⚠ Fields that need manual review:")
        print("-" * 80)
        for field in needs_review:
            print(f"  • {field}")
    else:
        print("\n✓ All fields have acceptable confidence!")

    # Show raw text sample
    raw_text = fields.get('_raw_text', '')
    if raw_text:
        print(f"\nRaw OCR Text (first 500 chars):")
        print("-" * 80)
        print(raw_text[:500])
        if len(raw_text) > 500:
            print(f"... ({len(raw_text) - 500} more characters)")

    return True


def main():
    """Run all tests"""
    print("=" * 80)
    print("OCR IMPROVEMENTS TEST SUITE")
    print("=" * 80)

    # Track results
    results = {}

    # Test 1: Service availability
    results['service_available'] = test_ocr_service_availability()
    print_separator()

    if not results['service_available']:
        print("Cannot continue tests without OCR service configured.")
        print("Please set up Google Cloud Vision credentials first.")
        return

    # Test 2: Date parsing
    results['date_parsing'] = test_date_parsing()
    print_separator()

    # Test 3: Field confidence
    results['field_confidence'] = test_field_confidence()
    print_separator()

    # Test 4: Label detection
    results['label_detection'] = test_label_detection()
    print_separator()

    # Test 5: Actual image (if provided)
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        results['image_extraction'] = test_with_sample_image(image_path)
        print_separator()
    else:
        print("TEST 5: Actual Image Extraction")
        print_separator()
        print("⊘ Skipped - no image file provided")
        print("  To test with an actual image, run:")
        print(f"  python {sys.argv[0]} /path/to/scanned_form.jpg")
        print_separator()

    # Summary
    print("TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for v in results.values() if v is True)
    total = len(results)

    for test_name, result in results.items():
        symbol = "✓" if result else "✗"
        print(f"{symbol} {test_name}: {'PASSED' if result else 'FAILED'}")

    print()
    print(f"Overall: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓✓✓ All tests passed! OCR improvements are working correctly.")
    else:
        print(f"\n⚠ {total - passed} test(s) failed. Please review the output above.")


if __name__ == '__main__':
    main()
