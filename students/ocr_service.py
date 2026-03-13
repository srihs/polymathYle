"""
OCR Service for Polymath Application Forms
Uses Google Cloud Vision API for handwriting recognition and text extraction.

Setup Requirements:
1. Enable Cloud Vision API in Google Cloud Console
2. Create a service account and download JSON credentials
3. Set environment variable: GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
   OR set GOOGLE_CLOUD_CREDENTIALS with the JSON content directly
"""

import os
import re
import json
import base64
import logging
from datetime import datetime
from io import BytesIO

from django.conf import settings

logger = logging.getLogger(__name__)


class OCRService:
    """
    Service class for extracting text from scanned application forms
    using Google Cloud Vision API DOCUMENT_TEXT_DETECTION.
    """

    # Form field labels to search for (case-insensitive)
    FIELD_LABELS = {
        # Office Use Only
        'admission_number': [
            'ADMISSION NO', 'ADMISSION NUMBER', 'ADM NO', 'ADM.NO',
            'YLE-', 'FCE-'
        ],

        # Student Personal Information
        'name_with_initials': [
            'NAME WITH INITIALS', 'NAME WITH INITIAL', 'INITIALS'
        ],
        'full_name': [
            'FULL NAME', 'NAME IN FULL', 'STUDENT NAME'
        ],
        'nationality': [
            'NATIONALITY', 'NATION'
        ],
        'date_of_birth': [
            'DATE OF BIRTH', 'D.O.B', 'DOB', 'BIRTH DATE', 'BIRTHDAY'
        ],
        'age': [
            'AGE'
        ],
        'gender': [
            'GENDER', 'SEX', 'MALE', 'FEMALE'
        ],
        'current_school': [
            'CURRENT SCHOOL', 'SCHOOL NAME', 'SCHOOL ATTENDING',
            'ATTENDING SCHOOL', 'SCHOOL'
        ],
        'siblings_info': [
            'SIBLINGS', 'BROTHER', 'SISTER', 'SIBLINGS INFO',
            'SIBLING INFORMATION'
        ],

        # Mother's Information
        'mother_name': [
            "MOTHER'S NAME", 'MOTHER NAME', "MOTHER'S FULL NAME",
            'MOTHER FULL NAME'
        ],
        'mother_contact_number': [
            "MOTHER'S CONTACT", "MOTHER'S TEL", "MOTHER'S PHONE",
            'MOTHER CONTACT', 'MOTHER TEL', 'MOTHER PHONE'
        ],
        'mother_occupation': [
            "MOTHER'S OCCUPATION", 'MOTHER OCCUPATION'
        ],

        # Father's Information
        'father_name': [
            "FATHER'S NAME", 'FATHER NAME', "FATHER'S FULL NAME",
            'FATHER FULL NAME'
        ],
        'father_contact_number': [
            "FATHER'S CONTACT", "FATHER'S TEL", "FATHER'S PHONE",
            'FATHER CONTACT', 'FATHER TEL', 'FATHER PHONE'
        ],
        'father_occupation': [
            "FATHER'S OCCUPATION", 'FATHER OCCUPATION'
        ],

        # Contact Information
        'home_address': [
            'HOME ADDRESS', 'ADDRESS', 'RESIDENTIAL ADDRESS',
            'PERMANENT ADDRESS'
        ],
        'whatsapp_number': [
            'WHATSAPP', 'WHATS APP', 'WA NUMBER', 'WHATSAPP NUMBER'
        ],
    }

    def __init__(self):
        """Initialize the OCR service with Google Cloud Vision client."""
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """
        Initialize Google Cloud Vision client.
        Supports both credentials file path and JSON content in environment variables.
        """
        try:
            from google.cloud import vision
            from google.oauth2 import service_account

            # Check for credentials JSON content first
            credentials_json = os.environ.get('GOOGLE_CLOUD_CREDENTIALS')
            if credentials_json:
                try:
                    credentials_info = json.loads(credentials_json)
                    credentials = service_account.Credentials.from_service_account_info(
                        credentials_info
                    )
                    self.client = vision.ImageAnnotatorClient(credentials=credentials)
                    logger.info("Google Cloud Vision client initialized from JSON credentials")
                    return
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON in GOOGLE_CLOUD_CREDENTIALS")

            # Fall back to GOOGLE_APPLICATION_CREDENTIALS file path
            credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            if credentials_path and os.path.exists(credentials_path):
                self.client = vision.ImageAnnotatorClient()
                logger.info("Google Cloud Vision client initialized from credentials file")
                return

            # Check Django settings as last resort
            if hasattr(settings, 'GOOGLE_CLOUD_CREDENTIALS_PATH'):
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = settings.GOOGLE_CLOUD_CREDENTIALS_PATH
                self.client = vision.ImageAnnotatorClient()
                logger.info("Google Cloud Vision client initialized from Django settings")
                return

            logger.warning(
                "Google Cloud Vision credentials not found. "
                "Set GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_CLOUD_CREDENTIALS environment variable."
            )

        except ImportError:
            logger.error(
                "google-cloud-vision package not installed. "
                "Run: pip install google-cloud-vision"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Google Cloud Vision client: {e}")

    def is_available(self):
        """Check if OCR service is properly configured and available."""
        # Try to initialize if not already done
        if self.client is None:
            self._initialize_client()
        return self.client is not None

    def extract_text_from_image(self, image_data):
        """
        Extract text from an image using Google Cloud Vision API.

        Args:
            image_data: Either a file path, bytes, or base64-encoded string

        Returns:
            dict: Contains 'text' (full text) and 'blocks' (structured text blocks)
        """
        if not self.is_available():
            raise RuntimeError(
                "OCR service not available. Please configure Google Cloud Vision credentials."
            )

        from google.cloud import vision

        # Prepare image for API
        image = vision.Image()

        if isinstance(image_data, str):
            if os.path.isfile(image_data):
                # File path
                with open(image_data, 'rb') as f:
                    image.content = f.read()
            elif image_data.startswith('data:image'):
                # Base64 data URL
                header, base64_data = image_data.split(',', 1)
                image.content = base64.b64decode(base64_data)
            else:
                # Assume raw base64
                image.content = base64.b64decode(image_data)
        elif isinstance(image_data, bytes):
            image.content = image_data
        elif hasattr(image_data, 'read'):
            # File-like object
            image.content = image_data.read()
        else:
            raise ValueError("Unsupported image data format")

        # Use DOCUMENT_TEXT_DETECTION for better handwriting recognition
        response = self.client.document_text_detection(image=image)

        if response.error.message:
            raise RuntimeError(f"Vision API error: {response.error.message}")

        full_text = response.full_text_annotation.text if response.full_text_annotation else ""

        # Extract text blocks for structured parsing
        blocks = []
        if response.full_text_annotation:
            for page in response.full_text_annotation.pages:
                for block in page.blocks:
                    block_text = ""
                    for paragraph in block.paragraphs:
                        for word in paragraph.words:
                            word_text = "".join(
                                symbol.text for symbol in word.symbols
                            )
                            block_text += word_text + " "
                        block_text = block_text.strip() + "\n"

                    if block_text.strip():
                        # Get bounding box for spatial analysis
                        vertices = block.bounding_box.vertices
                        bounds = {
                            'x': min(v.x for v in vertices),
                            'y': min(v.y for v in vertices),
                            'width': max(v.x for v in vertices) - min(v.x for v in vertices),
                            'height': max(v.y for v in vertices) - min(v.y for v in vertices),
                        }
                        blocks.append({
                            'text': block_text.strip(),
                            'bounds': bounds,
                            'confidence': block.confidence if hasattr(block, 'confidence') else None
                        })

        return {
            'text': full_text,
            'blocks': blocks
        }

    def extract_form_fields(self, image_data):
        """
        Extract structured form fields from a scanned application form.

        Args:
            image_data: Image file path, bytes, or base64 string

        Returns:
            dict: Extracted form fields with field names as keys
        """
        result = self.extract_text_from_image(image_data)
        full_text = result['text']

        if not full_text:
            return {'error': 'No text could be extracted from the image'}

        extracted_fields = {}

        # Normalize text for searching
        normalized_text = full_text.upper()
        lines = full_text.split('\n')
        normalized_lines = [line.upper() for line in lines]

        # Extract each field
        for field_name, labels in self.FIELD_LABELS.items():
            value = self._extract_field_value(
                full_text, normalized_text, lines, normalized_lines, labels, field_name
            )
            if value:
                extracted_fields[field_name] = value

        # Post-process specific fields
        extracted_fields = self._post_process_fields(extracted_fields)

        # Add raw text for reference
        extracted_fields['_raw_text'] = full_text

        return extracted_fields

    def _extract_field_value(self, full_text, normalized_text, lines, normalized_lines,
                             labels, field_name):
        """
        Extract the value for a specific field based on its labels.

        Args:
            full_text: Original extracted text
            normalized_text: Uppercase version for searching
            lines: Text split into lines
            normalized_lines: Uppercase lines
            labels: List of possible labels for this field
            field_name: Name of the field being extracted

        Returns:
            str: Extracted value or None
        """
        for label in labels:
            label_upper = label.upper()

            # Try to find the label in the text
            for i, norm_line in enumerate(normalized_lines):
                if label_upper in norm_line:
                    # Found the label - extract the value
                    original_line = lines[i]

                    # Check if value is on the same line after the label
                    label_idx = norm_line.find(label_upper)
                    after_label = original_line[label_idx + len(label):].strip()

                    # Remove common separators
                    after_label = re.sub(r'^[\s:;\-\.]+', '', after_label).strip()

                    if after_label and len(after_label) > 1:
                        return after_label

                    # Check the next line(s) for the value
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        # Make sure next line isn't another label
                        if next_line and not self._is_label_line(next_line.upper()):
                            return next_line

        # Special handling for admission number patterns
        if field_name == 'admission_number':
            patterns = [
                r'YLE-\d{4}-\d{4}',
                r'FCE-\d{4}-\d{4}',
                r'YLE\s*-?\s*\d{4}\s*-?\s*\d+',
            ]
            for pattern in patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    return match.group().replace(' ', '')

        # Special handling for phone numbers
        if 'contact' in field_name or 'phone' in field_name or 'whatsapp' in field_name:
            # Look near the relevant label
            for label in labels:
                label_upper = label.upper()
                idx = normalized_text.find(label_upper)
                if idx >= 0:
                    # Search in nearby text for phone pattern
                    search_area = full_text[idx:idx + 200]
                    phone_pattern = r'0\d{2}[\s\-]?\d{3}[\s\-]?\d{4}'
                    match = re.search(phone_pattern, search_area)
                    if match:
                        return re.sub(r'[\s\-]', '', match.group())

        return None

    def _is_label_line(self, line):
        """Check if a line appears to be a form label rather than a value."""
        label_indicators = [
            'NAME', 'ADDRESS', 'CONTACT', 'OCCUPATION', 'DATE',
            'GENDER', 'SCHOOL', 'NATIONALITY', 'NUMBER', 'TEL',
            'MOTHER', 'FATHER', 'PARENT', 'GUARDIAN'
        ]
        # If line contains multiple label indicators, it's probably a label
        count = sum(1 for indicator in label_indicators if indicator in line)
        return count >= 2 or line.endswith(':')

    def _post_process_fields(self, fields):
        """
        Post-process extracted fields to clean and format values.

        Args:
            fields: Dictionary of extracted field values

        Returns:
            dict: Cleaned and formatted fields
        """
        processed = fields.copy()

        # Clean phone numbers
        phone_fields = ['mother_contact_number', 'father_contact_number', 'whatsapp_number']
        for field in phone_fields:
            if field in processed:
                # Remove spaces and dashes, keep only digits and leading +
                cleaned = re.sub(r'[^\d+]', '', processed[field])
                # Ensure Sri Lankan format
                if cleaned.startswith('94'):
                    cleaned = '0' + cleaned[2:]
                processed[field] = cleaned

        # Parse date of birth
        if 'date_of_birth' in processed:
            dob = processed['date_of_birth']
            parsed_date = self._parse_date(dob)
            if parsed_date:
                processed['date_of_birth'] = parsed_date

        # Extract gender from checkbox or text
        if 'gender' in processed:
            gender_text = processed['gender'].upper()
            if 'MALE' in gender_text and 'FEMALE' not in gender_text:
                processed['gender'] = 'MALE'
            elif 'FEMALE' in gender_text:
                processed['gender'] = 'FEMALE'

        # Clean age - extract just the number
        if 'age' in processed:
            age_match = re.search(r'\d+', processed['age'])
            if age_match:
                processed['age'] = age_match.group()

        # Clean names - title case
        name_fields = ['name_with_initials', 'full_name', 'mother_name', 'father_name']
        for field in name_fields:
            if field in processed and processed[field]:
                # Keep initials uppercase, title case the rest
                processed[field] = self._format_name(processed[field])

        return processed

    def _parse_date(self, date_str):
        """
        Parse various date formats to YYYY-MM-DD.

        Args:
            date_str: Date string in various formats

        Returns:
            str: Date in YYYY-MM-DD format or None
        """
        date_str = date_str.strip()

        # Common date patterns
        patterns = [
            (r'(\d{2})[/\-\.](\d{2})[/\-\.](\d{4})', '%d/%m/%Y'),  # DD/MM/YYYY
            (r'(\d{4})[/\-\.](\d{2})[/\-\.](\d{2})', '%Y/%m/%d'),  # YYYY/MM/DD
            (r'(\d{2})[/\-\.](\d{2})[/\-\.](\d{2})', '%d/%m/%y'),  # DD/MM/YY
        ]

        for pattern, date_format in patterns:
            match = re.match(pattern, date_str)
            if match:
                try:
                    # Reconstruct date string with consistent separator
                    parts = match.groups()
                    reconstructed = '/'.join(parts)
                    parsed = datetime.strptime(reconstructed, date_format)
                    return parsed.strftime('%Y-%m-%d')
                except ValueError:
                    continue

        return None

    def _format_name(self, name):
        """
        Format a name properly - title case with uppercase initials.

        Args:
            name: Raw name string

        Returns:
            str: Properly formatted name
        """
        words = name.split()
        formatted = []

        for word in words:
            # Check if it's an initial (single letter with or without period)
            if len(word) <= 2 or (len(word) == 2 and word.endswith('.')):
                formatted.append(word.upper())
            else:
                formatted.append(word.title())

        return ' '.join(formatted)


# Singleton instance
_ocr_service = None


def get_ocr_service():
    """
    Get the singleton OCR service instance.

    Returns:
        OCRService: The OCR service instance
    """
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService()
    return _ocr_service


def extract_application_data(image_data):
    """
    Convenience function to extract application form data from an image.

    Args:
        image_data: Image file path, bytes, or base64 string

    Returns:
        dict: Extracted form fields or error information
    """
    service = get_ocr_service()

    if not service.is_available():
        return {
            'success': False,
            'error': 'OCR service not configured. Please set up Google Cloud Vision credentials.',
            'setup_instructions': (
                '1. Enable Cloud Vision API in Google Cloud Console\n'
                '2. Create a service account with Cloud Vision API access\n'
                '3. Download the JSON credentials file\n'
                '4. Set GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json\n'
                '   OR set GOOGLE_CLOUD_CREDENTIALS with the JSON content'
            )
        }

    try:
        fields = service.extract_form_fields(image_data)

        # Remove internal fields from response
        raw_text = fields.pop('_raw_text', '')

        return {
            'success': True,
            'fields': fields,
            'raw_text': raw_text[:1000] + '...' if len(raw_text) > 1000 else raw_text
        }
    except Exception as e:
        logger.exception("OCR extraction failed")
        return {
            'success': False,
            'error': str(e)
        }
