"""
OCR Service for Polymath Application Forms
Uses Google Cloud Vision API for handwriting recognition and text extraction.

Enhanced version with spatial awareness for better field extraction accuracy.

Setup Requirements:
1. Enable Cloud Vision API in Google Cloud Console
2. Create a service account and download JSON credentials
3. Set environment variable: GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
   OR set GOOGLE_CLOUD_CREDENTIALS with the JSON content directly

Improvements in this version:
- Spatial awareness using bounding box coordinates
- Multi-strategy field extraction (same line, next line, spatial proximity)
- Better date parsing with OCR error tolerance
- Improved handwriting recognition handling
- Confidence scoring and validation
"""

import os
import re
import json
import base64
import logging
from datetime import datetime
from io import BytesIO
from typing import Dict, List, Optional, Tuple

from django.conf import settings

logger = logging.getLogger(__name__)


class OCRService:
    """
    Service class for extracting text from scanned application forms
    using Google Cloud Vision API DOCUMENT_TEXT_DETECTION.
    """

    # Form field labels to search for (case-insensitive)
    # Labels are ordered by specificity (most specific first)
    FIELD_LABELS = {
        # Office Use Only
        'admission_number': [
            'ADMISSION NUMBER', 'ADMISSION NO', 'ADM NO', 'ADM.NO',
            'YLE-', 'FCE-'
        ],

        # Student Personal Information
        'name_with_initials': [
            'NAME WITH INITIALS', 'NAME WITH INITIAL', 'INITIALS'
        ],
        'full_name': [
            'FULL NAME', 'NAME IN FULL', 'STUDENT NAME', 'STUDENT FULL NAME'
        ],
        'date_of_birth': [
            'DATE OF BIRTH', 'D.O.B', 'DOB', 'BIRTH DATE', 'BIRTHDAY', 'DATE BIRTH'
        ],
        'nationality': [
            'NATIONALITY', 'NATION', 'ETHNIC'
        ],
        'age': [
            'AGE'
        ],
        'gender': [
            'GENDER', 'SEX'
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
            "MOTHER'S FULL NAME", "MOTHER'S NAME", 'MOTHER NAME',
            'MOTHER FULL NAME'
        ],
        'mother_contact_number': [
            "MOTHER'S CONTACT", "MOTHER'S TEL", "MOTHER'S PHONE",
            'MOTHER CONTACT', 'MOTHER TEL', 'MOTHER PHONE', 'MOTHER NO'
        ],
        'mother_occupation': [
            "MOTHER'S OCCUPATION", 'MOTHER OCCUPATION'
        ],

        # Father's Information
        'father_name': [
            "FATHER'S FULL NAME", "FATHER'S NAME", 'FATHER NAME',
            'FATHER FULL NAME'
        ],
        'father_contact_number': [
            "FATHER'S CONTACT", "FATHER'S TEL", "FATHER'S PHONE",
            'FATHER CONTACT', 'FATHER TEL', 'FATHER PHONE', 'FATHER NO'
        ],
        'father_occupation': [
            "FATHER'S OCCUPATION", 'FATHER OCCUPATION'
        ],

        # Contact Information
        'home_address': [
            'HOME ADDRESS', 'RESIDENTIAL ADDRESS', 'PERMANENT ADDRESS',
            'ADDRESS'
        ],
        'whatsapp_number': [
            'WHATSAPP NUMBER', 'WHATSAPP', 'WHATS APP', 'WA NUMBER'
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
        Enhanced to extract words with bounding boxes for spatial analysis.

        Args:
            image_data: Either a file path, bytes, or base64-encoded string

        Returns:
            dict: Contains 'text' (full text), 'blocks' (text blocks), and 'words' (individual words with positions)
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

        # Extract text blocks AND individual words with positions
        blocks = []
        words = []

        if response.full_text_annotation:
            for page in response.full_text_annotation.pages:
                for block in page.blocks:
                    block_text = ""
                    block_words = []

                    for paragraph in block.paragraphs:
                        para_words = []
                        for word in paragraph.words:
                            word_text = "".join(
                                symbol.text for symbol in word.symbols
                            )

                            # Get word bounding box
                            word_vertices = word.bounding_box.vertices
                            word_bounds = {
                                'x': min(v.x for v in word_vertices),
                                'y': min(v.y for v in word_vertices),
                                'x_end': max(v.x for v in word_vertices),
                                'y_end': max(v.y for v in word_vertices),
                                'width': max(v.x for v in word_vertices) - min(v.x for v in word_vertices),
                                'height': max(v.y for v in word_vertices) - min(v.y for v in word_vertices),
                            }

                            word_info = {
                                'text': word_text,
                                'bounds': word_bounds,
                                'confidence': word.confidence if hasattr(word, 'confidence') else None
                            }

                            words.append(word_info)
                            block_words.append(word_info)
                            para_words.append(word_text)

                            block_text += word_text + " "
                        block_text = block_text.strip() + "\n"

                    if block_text.strip():
                        # Get block bounding box for spatial analysis
                        vertices = block.bounding_box.vertices
                        bounds = {
                            'x': min(v.x for v in vertices),
                            'y': min(v.y for v in vertices),
                            'x_end': max(v.x for v in vertices),
                            'y_end': max(v.y for v in vertices),
                            'width': max(v.x for v in vertices) - min(v.x for v in vertices),
                            'height': max(v.y for v in vertices) - min(v.y for v in vertices),
                        }
                        blocks.append({
                            'text': block_text.strip(),
                            'bounds': bounds,
                            'words': block_words,
                            'confidence': block.confidence if hasattr(block, 'confidence') else None
                        })

        return {
            'text': full_text,
            'blocks': blocks,
            'words': words
        }

    def extract_form_fields(self, image_data):
        """
        Extract structured form fields from a scanned application form.
        Uses enhanced spatial awareness for better accuracy.

        Args:
            image_data: Image file path, bytes, or base64 string

        Returns:
            dict: Extracted form fields with field names as keys
        """
        result = self.extract_text_from_image(image_data)
        full_text = result['text']
        words = result['words']
        blocks = result['blocks']

        if not full_text:
            return {'error': 'No text could be extracted from the image'}

        extracted_fields = {}

        # Normalize text for searching
        normalized_text = full_text.upper()
        lines = full_text.split('\n')
        normalized_lines = [line.upper() for line in lines]

        # Extract each field using multiple strategies
        for field_name, labels in self.FIELD_LABELS.items():
            # Strategy 1: Spatial extraction (most accurate for forms)
            value = self._extract_field_value_spatial(words, labels, field_name)

            # Strategy 2: Fall back to line-based extraction if spatial fails
            if not value:
                value = self._extract_field_value(
                    full_text, normalized_text, lines, normalized_lines, labels, field_name
                )

            if value:
                extracted_fields[field_name] = value
                logger.debug(f"Extracted {field_name}: {value}")

        # Post-process specific fields
        extracted_fields = self._post_process_fields(extracted_fields)

        # Validate and add confidence scores
        extracted_fields = self._add_field_confidence(extracted_fields)

        # Add raw text for reference
        extracted_fields['_raw_text'] = full_text

        # Add extraction metadata
        extracted_fields['_extraction_metadata'] = {
            'total_words_detected': len(words),
            'total_blocks_detected': len(blocks),
            'extraction_timestamp': datetime.now().isoformat(),
            'fields_extracted': len([k for k in extracted_fields.keys() if not k.startswith('_')])
        }

        return extracted_fields

    def _extract_field_value_spatial(self, words: List[Dict], labels: List[str], field_name: str) -> Optional[str]:
        """
        Extract field value using spatial analysis of word positions.
        This is more accurate for forms than simple line-based matching.

        Args:
            words: List of word dictionaries with 'text' and 'bounds'
            labels: List of possible labels for this field
            field_name: Name of the field being extracted

        Returns:
            str: Extracted value or None
        """
        # Find label word(s) in the document
        label_words = []

        for label in labels:
            label_upper = label.upper()
            label_tokens = label_upper.split()

            # Try to find multi-word labels
            for i, word in enumerate(words):
                word_upper = word['text'].upper()

                # Check if this starts a multi-word label match
                if word_upper == label_tokens[0] or label_tokens[0] in word_upper:
                    # Check if subsequent words match
                    matches = [word]
                    matched = True

                    for j, token in enumerate(label_tokens[1:], 1):
                        if i + j < len(words):
                            next_word = words[i + j]['text'].upper()
                            if token not in next_word and next_word not in token:
                                matched = False
                                break
                            matches.append(words[i + j])
                        else:
                            matched = False
                            break

                    if matched and len(matches) >= len(label_tokens) * 0.7:  # Allow partial matches
                        label_words.extend(matches)
                        break

            if label_words:
                break

        if not label_words:
            return None

        # Calculate label bounding box
        label_bounds = self._calculate_combined_bounds(label_words)

        # Strategy 1: Look for words on the same horizontal line (right of label)
        value_words = self._find_words_right_of(words, label_bounds, same_line=True)

        # Strategy 2: Look for words below the label (next line)
        if not value_words or self._is_label_text(' '.join(w['text'] for w in value_words)):
            value_words = self._find_words_below(words, label_bounds)

        # Strategy 3: For checkboxes/gender, look for checked indicators
        if field_name == 'gender' and not value_words:
            value_words = self._extract_checkbox_value(words, label_bounds)

        # Filter out words that are labels themselves
        filtered_words = []
        for word in value_words:
            word_text = word['text'].upper()
            is_label = False

            # Check if this word is part of any label
            for label_list in self.FIELD_LABELS.values():
                for label in label_list:
                    if word_text in label.upper() or label.upper() in word_text:
                        if len(word_text) > 3:  # Avoid filtering short words like "NO"
                            is_label = True
                            break
                if is_label:
                    break

            if not is_label:
                filtered_words.append(word)

        if filtered_words:
            # Combine words into value, respecting spatial order
            value = ' '.join(w['text'] for w in filtered_words)
            return value.strip()

        return None

    def _calculate_combined_bounds(self, words: List[Dict]) -> Dict:
        """Calculate the combined bounding box for multiple words."""
        if not words:
            return {'x': 0, 'y': 0, 'x_end': 0, 'y_end': 0, 'width': 0, 'height': 0}

        x_min = min(w['bounds']['x'] for w in words)
        y_min = min(w['bounds']['y'] for w in words)
        x_max = max(w['bounds']['x_end'] for w in words)
        y_max = max(w['bounds']['y_end'] for w in words)

        return {
            'x': x_min,
            'y': y_min,
            'x_end': x_max,
            'y_end': y_max,
            'width': x_max - x_min,
            'height': y_max - y_min
        }

    def _find_words_right_of(self, words: List[Dict], label_bounds: Dict, same_line: bool = True) -> List[Dict]:
        """Find words to the right of a label (same horizontal line)."""
        result_words = []
        label_right = label_bounds['x_end']
        label_y_center = label_bounds['y'] + label_bounds['height'] / 2
        label_height = label_bounds['height']

        for word in words:
            word_x = word['bounds']['x']
            word_y_center = word['bounds']['y'] + word['bounds']['height'] / 2

            # Check if word is to the right of label
            if word_x > label_right:
                # Check if word is on the same horizontal line
                vertical_distance = abs(word_y_center - label_y_center)

                if same_line:
                    # Must be on approximately the same line (within label height)
                    if vertical_distance < label_height * 1.5:
                        result_words.append(word)
                else:
                    # Can be anywhere to the right
                    result_words.append(word)

        # Sort words left to right
        result_words.sort(key=lambda w: w['bounds']['x'])

        # Take consecutive words (stop at large gaps)
        if result_words:
            consecutive = [result_words[0]]
            for i in range(1, len(result_words)):
                prev_x_end = result_words[i-1]['bounds']['x_end']
                curr_x = result_words[i]['bounds']['x']
                gap = curr_x - prev_x_end

                # If gap is too large, stop (new field)
                if gap > label_bounds['width']:
                    break
                consecutive.append(result_words[i])

            return consecutive

        return []

    def _find_words_below(self, words: List[Dict], label_bounds: Dict) -> List[Dict]:
        """Find words below a label (next line in form)."""
        result_words = []
        label_bottom = label_bounds['y_end']
        label_x = label_bounds['x']
        label_width = label_bounds['width']
        label_height = label_bounds['height']

        # Look in the area below the label
        search_height = label_height * 3  # Look up to 3 lines below

        for word in words:
            word_y = word['bounds']['y']
            word_x_center = word['bounds']['x'] + word['bounds']['width'] / 2
            label_x_center = label_x + label_width / 2

            # Check if word is below the label
            if word_y > label_bottom and word_y < label_bottom + search_height:
                # Check horizontal alignment (should be roughly aligned)
                horizontal_distance = abs(word_x_center - label_x_center)

                # Allow some horizontal deviation but not too much
                if horizontal_distance < label_width * 2:
                    result_words.append(word)

        # Sort words by vertical position, then horizontal
        result_words.sort(key=lambda w: (w['bounds']['y'], w['bounds']['x']))

        # Take only the first line below
        if result_words:
            first_y = result_words[0]['bounds']['y']
            first_line = []

            for word in result_words:
                if abs(word['bounds']['y'] - first_y) < label_height * 0.5:
                    first_line.append(word)
                else:
                    break

            # Sort horizontally
            first_line.sort(key=lambda w: w['bounds']['x'])
            return first_line

        return []

    def _extract_checkbox_value(self, words: List[Dict], label_bounds: Dict) -> List[Dict]:
        """Extract gender from checkbox indicators."""
        # Look for MALE or FEMALE near checkboxes
        # This is a simplified version - could be enhanced with checkbox detection
        gender_words = []

        for word in words:
            word_text = word['text'].upper()
            if 'MALE' in word_text or 'FEMALE' in word_text:
                # Check if it's near the gender label area
                vertical_distance = abs(word['bounds']['y'] - label_bounds['y'])
                if vertical_distance < label_bounds['height'] * 3:
                    gender_words.append(word)

        return gender_words

    def _is_label_text(self, text: str) -> bool:
        """Check if text appears to be a form label rather than a value."""
        text_upper = text.upper()
        label_indicators = [
            'NAME', 'ADDRESS', 'CONTACT', 'OCCUPATION', 'DATE',
            'GENDER', 'SCHOOL', 'NATIONALITY', 'NUMBER', 'TEL',
            'MOTHER', 'FATHER', 'PARENT', 'GUARDIAN', 'BIRTH',
            'INITIALS', 'FULL', 'CURRENT', 'WHATSAPP'
        ]

        # Count how many label indicators are in the text
        count = sum(1 for indicator in label_indicators if indicator in text_upper)

        # If multiple indicators or ends with colon, it's a label
        return count >= 2 or text.strip().endswith(':')

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
        Parse various date formats to YYYY-MM-DD with OCR error tolerance.
        Handles common OCR misreads like 'O' for '0', 'l' for '1', etc.

        Args:
            date_str: Date string in various formats

        Returns:
            str: Date in YYYY-MM-DD format or None
        """
        if not date_str:
            return None

        date_str = date_str.strip()

        # Skip obvious placeholders
        if date_str.lower() in ['yyyy', 'dd/mm/yyyy', 'mm/dd/yyyy', 'date']:
            return None

        # Clean common OCR errors in dates
        date_str = self._clean_ocr_date_errors(date_str)

        # Common date patterns (DD/MM/YYYY is standard in Sri Lanka)
        patterns = [
            (r'(\d{2})[/\-\.](\d{2})[/\-\.](\d{4})', '%d/%m/%Y'),  # DD/MM/YYYY
            (r'(\d{4})[/\-\.](\d{2})[/\-\.](\d{2})', '%Y/%m/%d'),  # YYYY/MM/DD
            (r'(\d{2})[/\-\.](\d{2})[/\-\.](\d{2})', '%d/%m/%y'),  # DD/MM/YY
            (r'(\d{1})[/\-\.](\d{2})[/\-\.](\d{4})', '%d/%m/%Y'),  # D/MM/YYYY (single digit day)
            (r'(\d{2})[/\-\.](\d{1})[/\-\.](\d{4})', '%d/%m/%Y'),  # DD/M/YYYY (single digit month)
        ]

        for pattern, date_format in patterns:
            match = re.search(pattern, date_str)
            if match:
                try:
                    # Reconstruct date string with consistent separator
                    parts = match.groups()
                    reconstructed = '/'.join(parts)
                    parsed = datetime.strptime(reconstructed, date_format)

                    # Validate date is reasonable (between 1990 and current year + 5)
                    current_year = datetime.now().year
                    if 1990 <= parsed.year <= current_year + 5:
                        return parsed.strftime('%Y-%m-%d')
                except ValueError:
                    continue

        # Try to extract just digits and see if we can make sense of them
        digits_only = re.sub(r'\D', '', date_str)
        if len(digits_only) == 8:  # DDMMYYYY or YYYYMMDD
            # Try DDMMYYYY first (more common in Sri Lanka)
            try:
                parsed = datetime.strptime(digits_only, '%d%m%Y')
                if 1990 <= parsed.year <= datetime.now().year + 5:
                    return parsed.strftime('%Y-%m-%d')
            except ValueError:
                pass

            # Try YYYYMMDD
            try:
                parsed = datetime.strptime(digits_only, '%Y%m%d')
                if 1990 <= parsed.year <= datetime.now().year + 5:
                    return parsed.strftime('%Y-%m-%d')
            except ValueError:
                pass

        return None

    def _clean_ocr_date_errors(self, date_str: str) -> str:
        """
        Clean common OCR errors in date strings.

        Args:
            date_str: Raw date string from OCR

        Returns:
            str: Cleaned date string
        """
        # Common OCR substitutions
        replacements = {
            'O': '0',  # Letter O to zero
            'o': '0',
            'I': '1',  # Letter I to one
            'l': '1',  # Lowercase L to one
            'S': '5',  # Letter S to five (sometimes)
            'Z': '2',  # Letter Z to two (sometimes)
        }

        cleaned = date_str
        for old, new in replacements.items():
            # Only replace in numeric context (surrounded by digits or separators)
            cleaned = re.sub(rf'(?<=[/\-\.\d]){old}(?=[/\-\.\d])', new, cleaned)
            cleaned = re.sub(rf'^{old}(?=[/\-\.\d])', new, cleaned)
            cleaned = re.sub(rf'(?<=[/\-\.\d]){old}$', new, cleaned)

        return cleaned

    def _add_field_confidence(self, fields: Dict) -> Dict:
        """
        Add confidence scores and validation flags to extracted fields.

        Args:
            fields: Dictionary of extracted fields

        Returns:
            dict: Fields with added confidence metadata
        """
        confidence_data = {}

        for field_name, value in fields.items():
            if field_name.startswith('_'):
                continue

            confidence = self._calculate_field_confidence(field_name, value)
            is_valid = self._validate_field_value(field_name, value)

            confidence_data[f'_{field_name}_confidence'] = confidence
            confidence_data[f'_{field_name}_valid'] = is_valid

        fields.update(confidence_data)
        return fields

    def _calculate_field_confidence(self, field_name: str, value: str) -> str:
        """
        Calculate confidence level for an extracted field.

        Args:
            field_name: Name of the field
            value: Extracted value

        Returns:
            str: Confidence level (HIGH, MEDIUM, LOW)
        """
        if not value:
            return 'LOW'

        # Check for placeholder text
        placeholders = ['yyyy', 'dd/mm/yyyy', 'n/a', 'na', '...', '___']
        if value.lower() in placeholders:
            return 'LOW'

        # Field-specific confidence checks
        if field_name == 'date_of_birth':
            # High confidence if it's a valid date
            if self._parse_date(value):
                return 'HIGH'
            return 'LOW'

        if field_name in ['mother_contact_number', 'father_contact_number', 'whatsapp_number']:
            # High confidence if it matches phone pattern
            if re.match(r'^0\d{9}$', value):
                return 'HIGH'
            elif re.match(r'^\d{10}$', value):
                return 'MEDIUM'
            return 'LOW'

        if field_name == 'gender':
            if value.upper() in ['MALE', 'FEMALE']:
                return 'HIGH'
            return 'MEDIUM'

        if field_name == 'age':
            try:
                age = int(value)
                if 3 <= age <= 18:  # Reasonable age range for YLE students
                    return 'HIGH'
            except (ValueError, TypeError):
                return 'LOW'

        if field_name == 'admission_number':
            if re.match(r'^(YLE|FCE)-\d{4}-\d{4}$', value):
                return 'HIGH'
            return 'MEDIUM'

        # Check length - very short values are suspicious
        if len(value) < 2:
            return 'LOW'

        # Default to medium confidence
        return 'MEDIUM'

    def _validate_field_value(self, field_name: str, value: str) -> bool:
        """
        Validate if a field value is reasonable.

        Args:
            field_name: Name of the field
            value: Extracted value

        Returns:
            bool: True if value appears valid
        """
        if not value:
            return False

        # Check for placeholder text
        placeholders = ['yyyy', 'dd/mm/yyyy', 'n/a', 'na', '...', '___']
        if value.lower() in placeholders:
            return False

        # Field-specific validation
        if field_name == 'date_of_birth':
            return self._parse_date(value) is not None

        if field_name in ['mother_contact_number', 'father_contact_number', 'whatsapp_number']:
            # Should be 10 digits starting with 0
            return bool(re.match(r'^0\d{9}$', value))

        if field_name == 'gender':
            return value.upper() in ['MALE', 'FEMALE']

        if field_name == 'age':
            try:
                age = int(value)
                return 3 <= age <= 18
            except (ValueError, TypeError):
                return False

        if field_name == 'admission_number':
            return bool(re.match(r'^(YLE|FCE)-\d{4}-\d{4}$', value))

        # Must have reasonable length
        if len(value) < 2 or len(value) > 200:
            return False

        return True

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
