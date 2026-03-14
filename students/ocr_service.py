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
        'receipt_number': [
            'RECEIPT NUMBER', 'RECEIPT NO', 'RECEIPT', 'REC NO'
        ],
        'application_date': [
            'DATE', 'APPLICATION DATE', 'RECEIVED DATE', 'DATE RECEIVED', 'OFFICE DATE'
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
            'SIBLING INFORMATION', 'SIBLINGS DETAILS'
        ],

        # Mother's Information
        'mother_name': [
            "MOTHER'S FULL NAME", "MOTHER'S NAME", 'MOTHER NAME',
            'MOTHER FULL NAME', 'MOTHER:'
        ],
        'mother_contact_number': [
            "MOTHER'S CONTACT NUMBER", "MOTHER'S CONTACT", "MOTHER'S TEL",
            "MOTHER'S PHONE", 'MOTHER CONTACT NUMBER', 'MOTHER CONTACT',
            'MOTHER TEL', 'MOTHER PHONE', 'MOTHER NO', 'MOTHER MOBILE',
            'CONTACT NUMBER'  # Generic pattern for parent sections
        ],
        'mother_occupation': [
            "MOTHER'S OCCUPATION", 'MOTHER OCCUPATION', 'OCCUPATION'
        ],

        # Father's Information
        'father_name': [
            "FATHER'S FULL NAME", "FATHER'S NAME", 'FATHER NAME',
            'FATHER FULL NAME', 'FATHER:'
        ],
        'father_contact_number': [
            "FATHER'S CONTACT NUMBER", "FATHER'S CONTACT", "FATHER'S TEL",
            "FATHER'S PHONE", 'FATHER CONTACT NUMBER', 'FATHER CONTACT',
            'FATHER TEL', 'FATHER PHONE', 'FATHER NO', 'FATHER MOBILE',
            'CONTACT NUMBER'  # Generic pattern for parent sections
        ],
        'father_occupation': [
            "FATHER'S OCCUPATION", 'FATHER OCCUPATION', 'OCCUPATION'
        ],

        # Contact Information
        'home_address': [
            'HOME ADDRESS', 'RESIDENTIAL ADDRESS', 'PERMANENT ADDRESS',
            'ADDRESS'
        ],
        'whatsapp_number': [
            'WHATSAPP NUMBER', 'WHATSAPP NO', 'WHATS APP NUMBER', 'WHATS APP NO',
            'WHATSAPP', 'WHATS APP', 'WA NUMBER', 'WA NO', 'W/A NUMBER'
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
            # Add extra logging for critical fields
            if field_name in ['whatsapp_number', 'application_date', 'receipt_number']:
                logger.info(f"Starting extraction for {field_name} with labels: {labels}")

            # Strategy 1: Spatial extraction (most accurate for forms)
            value = self._extract_field_value_spatial(words, labels, field_name)

            # Strategy 2: Fall back to line-based extraction if spatial fails
            if not value:
                value = self._extract_field_value(
                    full_text, normalized_text, lines, normalized_lines, labels, field_name
                )

            if value:
                extracted_fields[field_name] = value
                if field_name in ['whatsapp_number', 'application_date', 'receipt_number']:
                    logger.info(f"Successfully extracted {field_name}: {value}")
                else:
                    logger.debug(f"Extracted {field_name}: {value}")
            else:
                if field_name in ['whatsapp_number', 'application_date', 'receipt_number']:
                    logger.warning(f"Failed to extract {field_name}")

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
        # Extra debugging for parent fields
        is_parent_field = 'mother' in field_name or 'father' in field_name
        is_father_field = 'father' in field_name

        if is_father_field:
            logger.info(f"=== EXTRACTING FATHER FIELD: {field_name} ===")
            logger.info(f"Labels to search: {labels}")

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

            # Find label for section boundary detection (we still need this)
            label_words = []
            matched_label = None

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

                        if matched and len(matches) >= len(label_tokens) * 0.7:
                            label_words.extend(matches)
                            matched_label = label
                            logger.info(f"Found label '{matched_label}' at y={matches[0]['bounds']['y']}")
                            break

                if label_words:
                    break

            if not label_words:
                logger.warning(f"No label found for {field_name}")
                return None

            label_bounds = self._calculate_combined_bounds(label_words)

            # Use ONLY section-aware extraction
            logger.info(f"Calling section-aware extraction for {parent_prefix}...")
            value_words = self._find_in_parent_section(words, label_bounds, parent_prefix, field_name)

            if value_words:
                logger.info(f"Section-aware extraction found {len(value_words)} words: {[w['text'] for w in value_words]}")
            else:
                logger.warning(f"Section-aware extraction found no words for {field_name}")

            # Skip to final processing (label filtering and value assembly)
            filtered_words = []
            for word in value_words:
                word_text = word['text'].upper()
                is_label = False

                # Check if this word is part of any label
                for label_list in self.FIELD_LABELS.values():
                    for label in label_list:
                        label_tokens = label.upper().split()
                        if word_text in label_tokens:
                            if len(word_text) > 3 or word_text in ['NAME', 'DATE', 'NUMBER', 'TEL', 'NO']:
                                is_label = True
                                break
                    if is_label:
                        break

                if not is_label:
                    filtered_words.append(word)

            if filtered_words:
                value = ' '.join(w['text'] for w in filtered_words)
                logger.info(f"FINAL VALUE for {field_name}: '{value}'")
                logger.info(f"{'=' * 60}\n")
                return value.strip()
            else:
                logger.warning(f"NO VALUE after filtering for {field_name}")
                logger.info(f"{'=' * 60}\n")
                return None

        # For all other fields, continue with normal extraction strategies
        # Find label word(s) in the document
        label_words = []
        matched_label = None

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
                        matched_label = label
                        if is_father_field:
                            logger.info(f"Found label match: '{matched_label}' at position {matches[0]['bounds']}")
                        break

            if label_words:
                break

        if not label_words:
            if is_parent_field:
                logger.warning(f"No label words found for {field_name} with labels: {labels}")
            else:
                logger.debug(f"No label words found for {field_name} with labels: {labels}")
            return None

        if is_parent_field:
            logger.info(f"Found label '{matched_label}' for {field_name} at position {label_words[0]['bounds']}")
        else:
            logger.debug(f"Found label '{matched_label}' for {field_name} at position {label_words[0]['bounds']}")

        # Calculate label bounding box
        label_bounds = self._calculate_combined_bounds(label_words)

        # Strategy 1: Look for words on the same horizontal line (right of label)
        # Use larger gap tolerance for fields that may have multiple words with spaces
        gap_multiplier = 2.5 if field_name in ['siblings_info', 'full_name'] else 1.0
        value_words = self._find_words_right_of(words, label_bounds, same_line=True,
                                                 max_gap_multiplier=gap_multiplier)
        if is_parent_field:
            logger.info(f"Strategy 1 - Right of label: Found {len(value_words)} words: {[w['text'] for w in value_words]}")
        else:
            logger.debug(f"{field_name}: Found {len(value_words)} words right of label: {[w['text'] for w in value_words]}")

        # Strategy 2: For full_name specifically, also check words below and combine them
        # This handles names that span multiple rows (e.g., "Kamburugamuwe Gam Acharige" on row 1,
        # "Leon Nimshan" on row 2)
        if field_name == 'full_name' and value_words:
            # Get the rightmost word from the first row to determine where the name field ends horizontally
            rightmost_x_end = max(w['bounds']['x_end'] for w in value_words)
            label_bottom = label_bounds['y_end']

            # Look for continuation words in the next row (below the label, but within the name field area)
            continuation_words = []
            for word in words:
                word_y = word['bounds']['y']
                word_x = word['bounds']['x']

                # Check if word is below the label's bottom
                if word_y > label_bottom:
                    # Check if word is horizontally aligned with the name field (not the label)
                    # Name field typically starts to the right of the label
                    if word_x >= label_bounds['x_end'] - 50:  # Allow small tolerance
                        # Check it's not too far below (within 2 line heights)
                        if word_y < label_bottom + label_bounds['height'] * 2:
                            continuation_words.append(word)

            # Sort continuation words and add them to value_words
            if continuation_words:
                continuation_words.sort(key=lambda w: (w['bounds']['y'], w['bounds']['x']))
                logger.debug(f"{field_name}: Found {len(continuation_words)} continuation words: {[w['text'] for w in continuation_words]}")

                # Stop at the first word that looks like a new field label
                filtered_continuation = []
                for word in continuation_words:
                    if not self._is_label_text(word['text']):
                        filtered_continuation.append(word)
                    else:
                        logger.debug(f"{field_name}: Stopped at label word: {word['text']}")
                        break

                value_words.extend(filtered_continuation)
                logger.debug(f"{field_name}: Combined total of {len(value_words)} words: {[w['text'] for w in value_words]}")

        # Strategy 3: Look for words below the label (next line) - for when nothing is on the same line
        if not value_words or self._is_label_text(' '.join(w['text'] for w in value_words)):
            # For multi-line fields like siblings or address, look further down and allow multiline
            max_lines = 5 if field_name in ['siblings_info', 'home_address', 'full_name'] else 3
            allow_multiline = field_name in ['siblings_info', 'home_address', 'full_name']
            value_words = self._find_words_below(words, label_bounds, max_lines=max_lines,
                                                 allow_multiline=allow_multiline)
            if is_father_field:
                logger.info(f"Strategy 3 - Below label: Found {len(value_words)} words: {[w['text'] for w in value_words]}")
            else:
                logger.debug(f"{field_name}: Found {len(value_words)} words below label: {[w['text'] for w in value_words]}")

        # Strategy 4: For checkboxes/gender, look for checked indicators
        if field_name == 'gender' and not value_words:
            value_words = self._extract_checkbox_value(words, label_bounds)

        # Strategy 5: For parent NAME fields only (contact/occupation handled separately above)
        # Names can use section-aware extraction as a fallback
        if field_name in ['mother_name', 'father_name']:
            if not value_words or len(value_words) == 0:
                parent_prefix = 'MOTHER' if 'mother' in field_name else 'FATHER'
                if is_parent_field:
                    logger.info(f"Strategy 5 - Attempting section-aware extraction for {parent_prefix} NAME")
                value_words = self._find_in_parent_section(words, label_bounds, parent_prefix, field_name)
                if is_parent_field:
                    logger.info(f"Strategy 5 result: Found {len(value_words)} words: {[w['text'] for w in value_words]}")

        # Strategy 6: For WhatsApp number in Contact Information section
        # WhatsApp often appears under HOME ADDRESS section
        if field_name == 'whatsapp_number':
            if not value_words or len(value_words) == 0:
                value_words = self._find_in_contact_section(words, label_bounds, field_name)
                logger.info(f"{field_name}: Found {len(value_words)} words in Contact Information section: {[w['text'] for w in value_words]}")

        # Filter out words that are labels themselves
        filtered_words = []
        for word in value_words:
            word_text = word['text'].upper()
            is_label = False

            # Special handling for short words - don't filter age numbers
            if field_name == 'age' and word_text.isdigit():
                filtered_words.append(word)
                continue

            # Check if this word is part of any label
            for label_list in self.FIELD_LABELS.values():
                for label in label_list:
                    label_tokens = label.upper().split()
                    # Only filter if word matches a complete label token (not partial)
                    if word_text in label_tokens:
                        # Avoid filtering short generic words that might be values
                        if len(word_text) > 3 or word_text in ['NAME', 'DATE', 'NUMBER', 'TEL', 'NO']:
                            is_label = True
                            break
                if is_label:
                    break

            if not is_label:
                filtered_words.append(word)

        if is_parent_field:
            logger.info(f"After label filtering: {len(filtered_words)} words: {[w['text'] for w in filtered_words]}")
        else:
            logger.debug(f"{field_name}: {len(filtered_words)} words after filtering: {[w['text'] for w in filtered_words]}")

        if filtered_words:
            # Combine words into value, respecting spatial order
            value = ' '.join(w['text'] for w in filtered_words)
            if is_parent_field:
                logger.info(f"FINAL EXTRACTED VALUE for {field_name}: '{value}'")
                if is_father_field:
                    logger.info(f"=== END EXTRACTION FOR {field_name} ===\n")
            return value.strip()

        if is_parent_field:
            logger.warning(f"NO VALUE EXTRACTED for {field_name}")
            if is_father_field:
                logger.info(f"=== END EXTRACTION FOR {field_name} ===\n")
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

    def _find_words_right_of(self, words: List[Dict], label_bounds: Dict, same_line: bool = True,
                             max_gap_multiplier: float = 1.0) -> List[Dict]:
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
                # Use dynamic gap threshold based on label width
                max_gap = label_bounds['width'] * max_gap_multiplier
                if gap > max_gap:
                    break
                consecutive.append(result_words[i])

            return consecutive

        return []

    def _find_words_below(self, words: List[Dict], label_bounds: Dict, max_lines: int = 3,
                          allow_multiline: bool = False) -> List[Dict]:
        """Find words below a label (next line in form)."""
        result_words = []
        label_bottom = label_bounds['y_end']
        label_x = label_bounds['x']
        label_width = label_bounds['width']
        label_height = label_bounds['height']

        # Look in the area below the label
        search_height = label_height * max_lines  # Look up to N lines below

        for word in words:
            word_y = word['bounds']['y']
            word_x_center = word['bounds']['x'] + word['bounds']['width'] / 2
            label_x_center = label_x + label_width / 2

            # Check if word is below the label
            if word_y > label_bottom and word_y < label_bottom + search_height:
                # Check horizontal alignment (should be roughly aligned)
                horizontal_distance = abs(word_x_center - label_x_center)

                # Allow some horizontal deviation but not too much
                # Be more lenient for horizontally offset content
                if horizontal_distance < label_width * 3:
                    result_words.append(word)

        # Sort words by vertical position, then horizontal
        result_words.sort(key=lambda w: (w['bounds']['y'], w['bounds']['x']))

        # For multiline fields, take all consecutive lines
        if allow_multiline and result_words:
            all_lines = []
            current_line = [result_words[0]]
            current_y = result_words[0]['bounds']['y']

            for i in range(1, len(result_words)):
                word = result_words[i]
                # If this word is on a new line
                if abs(word['bounds']['y'] - current_y) > label_height * 0.5:
                    # Check if there's a big vertical gap (indicates new section)
                    if len(current_line) > 0:
                        prev_y_end = max(w['bounds']['y_end'] for w in current_line)
                        if word['bounds']['y'] - prev_y_end > label_height * 2:
                            break  # Stop at large vertical gap
                    # Start new line
                    all_lines.extend(current_line)
                    current_line = [word]
                    current_y = word['bounds']['y']
                else:
                    # Same line
                    current_line.append(word)

            # Add the last line
            all_lines.extend(current_line)
            # Sort horizontally within the combined result
            all_lines.sort(key=lambda w: (w['bounds']['y'], w['bounds']['x']))
            return all_lines

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

    def _find_in_parent_section(self, words: List[Dict], label_bounds: Dict,
                                 parent_prefix: str, field_name: str) -> List[Dict]:
        """
        Find field value within a parent section (e.g., Mother's or Father's section).
        This is useful when generic labels like "CONTACT NUMBER" or "OCCUPATION" appear
        multiple times in the form.

        Args:
            words: List of all words in the document
            label_bounds: Bounding box of the label
            parent_prefix: 'MOTHER' or 'FATHER'
            field_name: The field being extracted

        Returns:
            List of words that are the field value
        """
        is_father_field = 'father' in field_name
        if is_father_field:
            logger.info(f"=== PARENT SECTION EXTRACTION for {parent_prefix} ===")
            logger.info(f"Field name: {field_name}")

        # Find the parent section header or parent NAME field
        # Strategy: Look for "MOTHER'S NAME" / "FATHER'S NAME" as the section start
        # This is more reliable than looking for just "MOTHER" or "FATHER"
        parent_words = []
        parent_name_found = False

        # First, try to find "PARENT'S NAME" or "PARENT NAME" field
        for i, word in enumerate(words):
            word_text = word['text'].upper()
            if parent_prefix in word_text:
                # Check if this is the NAME field for this parent
                # Look at the next few words to see if "NAME" appears
                is_name_field = False
                if 'NAME' in word_text:  # "FATHER'S" and "NAME" in same word
                    is_name_field = True
                else:
                    # Check next 2 words for "NAME"
                    for j in range(i+1, min(i+3, len(words))):
                        if 'NAME' in words[j]['text'].upper():
                            is_name_field = True
                            break

                if is_name_field:
                    parent_words.append(word)
                    parent_name_found = True
                    if is_father_field:
                        logger.info(f"Found {parent_prefix}'s NAME field at index {i}: '{word['text']}' at y={word['bounds']['y']}")
                    # Add next word if it contains NAME
                    if i+1 < len(words) and 'NAME' in words[i+1]['text'].upper():
                        parent_words.append(words[i+1])
                        if is_father_field:
                            logger.info(f"  - Added NAME word: '{words[i+1]['text']}'")
                    break

        # If NAME field not found, fall back to looking for section header
        if not parent_name_found:
            for i, word in enumerate(words):
                if parent_prefix in word['text'].upper():
                    parent_words.append(word)
                    if is_father_field:
                        logger.info(f"Found {parent_prefix} word at index {i}: '{word['text']}' at y={word['bounds']['y']}")
                    # Look for nearby words that might complete the section header
                    for j in range(i+1, min(i+3, len(words))):
                        if any(keyword in words[j]['text'].upper()
                              for keyword in ['INFORMATION', 'DETAILS', 'INFO', 'PARTICULARS']):
                            parent_words.append(words[j])
                            if is_father_field:
                                logger.info(f"  - Added section keyword: '{words[j]['text']}'")
                            break
                    break

        if not parent_words:
            if is_father_field:
                logger.warning(f"No {parent_prefix} section header found!")
                # Log all words containing parent prefix for debugging
                logger.info(f"All words containing '{parent_prefix}':")
                for i, word in enumerate(words):
                    if parent_prefix in word['text'].upper():
                        logger.info(f"  Word {i}: '{word['text']}' at y={word['bounds']['y']}")
            else:
                logger.debug(f"No {parent_prefix} section header found")
            return []

        parent_section_bounds = self._calculate_combined_bounds(parent_words)
        if is_father_field:
            logger.info(f"Found {parent_prefix} section at y={parent_section_bounds['y']}")
        else:
            logger.debug(f"Found {parent_prefix} section at y={parent_section_bounds['y']}")

        # Determine the section boundaries
        # Section starts at the parent header and extends down until next major section
        section_start_y = parent_section_bounds['y']
        section_end_y = section_start_y + 500  # Default: 500px down

        if is_father_field:
            logger.info(f"Initial section boundaries: start_y={section_start_y}, end_y={section_end_y}")

        # Try to find the end of this section (next parent section or major header)
        # CRITICAL FIX: For FATHER section, we need to find the NEXT section AFTER father
        # For MOTHER section, we need to find FATHER section (which comes after)
        if parent_prefix == 'MOTHER':
            # Mother section ends where Father section begins
            other_parent = 'FATHER'
            section_end_markers = [other_parent, 'CONTACT INFORMATION', 'STUDENT INFORMATION', 'ADDRESS']

            for word in words:
                if word['bounds']['y'] > section_start_y:
                    if (other_parent in word['text'].upper() or
                        any(header in word['text'].upper() for header in section_end_markers)):
                        section_end_y = min(section_end_y, word['bounds']['y'])
                        logger.debug(f"Mother section ends at: '{word['text']}' at y={section_end_y}")
                        break
        else:
            # Father section ends at next major section (NOT mother, as mother comes before)
            # Look for section markers that typically come AFTER the family information
            section_end_markers = ['CONTACT INFORMATION', 'HOME ADDRESS', 'STUDENT INFORMATION',
                                   'SIBLINGS', 'PAYMENT', 'OFFICE USE', 'REMARKS']

            if is_father_field:
                logger.info(f"Searching for FATHER section end markers: {section_end_markers}")

            for word in words:
                word_y = word['bounds']['y']
                if word_y > section_start_y:
                    word_text = word['text'].upper()
                    for marker in section_end_markers:
                        if marker in word_text:
                            # Make sure this is a section header, not just a word containing the marker
                            # Check if this looks like a header (all caps, at start of line)
                            if len(word_text) > 3:  # Skip short words
                                section_end_y = min(section_end_y, word_y)
                                if is_father_field:
                                    logger.info(f"Section boundary found: '{word['text']}' at y={word_y}")
                                    logger.info(f"FATHER section ends at y={section_end_y}")
                                break
                    if section_end_y < section_start_y + 500:  # Found a marker
                        break

        if is_father_field:
            logger.info(f"Final section boundaries: start_y={section_start_y}, end_y={section_end_y}")
            # Log all words in the FATHER section for debugging
            section_words = [w for w in words if section_start_y <= w['bounds']['y'] <= section_end_y]
            logger.info(f"Total words in {parent_prefix} section: {len(section_words)}")
            logger.info(f"First 30 words in {parent_prefix} section:")
            for i, w in enumerate(section_words[:30]):
                logger.info(f"  [{i}] y={w['bounds']['y']:4.0f}: '{w['text']}'")

        # Now look for the specific field label within this section
        # Determine what keyword to search for in the label
        if 'contact' in field_name:
            field_type = 'CONTACT'
            search_keywords = ['CONTACT', 'NUMBER', 'TEL', 'PHONE']
        elif 'occupation' in field_name:
            field_type = 'OCCUPATION'
            search_keywords = ['OCCUPATION']
        elif 'name' in field_name:
            field_type = 'NAME'
            # For name fields, look for "NAME" but prefer specific patterns like "FATHER'S NAME"
            search_keywords = ['NAME']
        else:
            field_type = 'UNKNOWN'
            search_keywords = []

        label_in_section = None

        if is_father_field:
            logger.info(f"Searching for '{field_type}' label within section boundaries...")
            logger.info(f"Search keywords: {search_keywords}")
            # Log all words in the section
            section_words = [w for w in words if section_start_y <= w['bounds']['y'] <= section_end_y]
            logger.info(f"Words in {parent_prefix} section ({len(section_words)} total):")
            for i, w in enumerate(section_words[:20]):  # Limit to first 20 for readability
                logger.info(f"  {i}: '{w['text']}' at y={w['bounds']['y']}")

        # Search for the field label within the section
        # Look for words that match any of the search keywords
        for i, word in enumerate(words):
            word_y = word['bounds']['y']
            if section_start_y <= word_y <= section_end_y:
                word_text = word['text'].upper()
                # Check if any search keyword is in this word
                for keyword in search_keywords:
                    if keyword in word_text:
                        # For NAME fields, also check if FATHER/MOTHER is nearby to avoid confusion
                        if field_type == 'NAME':
                            # Look for FATHER or MOTHER in the same word or within 2 words before
                            has_parent_context = False
                            if parent_prefix in word_text:
                                has_parent_context = True
                            else:
                                # Check previous 2 words
                                for j in range(max(0, i-2), i):
                                    if section_start_y <= words[j]['bounds']['y'] <= section_end_y:
                                        if parent_prefix in words[j]['text'].upper():
                                            has_parent_context = True
                                            break

                            # Only accept this NAME label if it has parent context
                            if not has_parent_context:
                                if is_father_field:
                                    logger.info(f"  Skipping '{word['text']}' - no {parent_prefix} context")
                                continue

                        label_in_section = word
                        if is_father_field:
                            logger.info(f"Found '{field_type}' label in {parent_prefix} section: '{word['text']}' at y={word_y}")
                        else:
                            logger.debug(f"Found '{field_type}' label in {parent_prefix} section at y={word_y}")
                        break

                if label_in_section:
                    break

        if not label_in_section:
            if is_father_field:
                logger.warning(f"No '{field_type}' label found in {parent_prefix} section")
                logger.info(f"Searched between y={section_start_y} and y={section_end_y}")
            else:
                logger.debug(f"No '{field_type}' label found in {parent_prefix} section")
            return []

        # Extract value relative to this label
        field_label_bounds = label_in_section['bounds']

        # Try right of label first
        # Use larger gap for names (may have multiple words)
        gap_mult = 2.0 if field_type == 'NAME' else 1.5
        value_words = self._find_words_right_of(words, field_label_bounds, same_line=True,
                                                max_gap_multiplier=gap_mult)
        if is_father_field:
            logger.info(f"Words right of '{field_type}' label: {[w['text'] for w in value_words]}")

        # Then try below
        if not value_words:
            # Allow multiline for names and occupations (they can wrap)
            allow_multi = field_type in ['NAME', 'OCCUPATION']
            value_words = self._find_words_below(words, field_label_bounds, max_lines=2,
                                                 allow_multiline=allow_multi)
            if is_father_field:
                logger.info(f"Words below '{field_type}' label: {[w['text'] for w in value_words]}")

        # Filter to only include words within the section
        filtered = [w for w in value_words
                   if section_start_y <= w['bounds']['y'] <= section_end_y]

        if is_father_field:
            logger.info(f"After section filtering: {len(filtered)} value words: {[w['text'] for w in filtered]}")
            logger.info(f"=== END PARENT SECTION EXTRACTION ===")
        else:
            logger.debug(f"Found {len(filtered)} value words in section: {[w['text'] for w in filtered]}")
        return filtered

    def _find_in_contact_section(self, words: List[Dict], label_bounds: Dict,
                                   field_name: str) -> List[Dict]:
        """
        Find field value within the Contact Information section.
        WhatsApp number typically appears under HOME ADDRESS section.

        Args:
            words: List of all words in the document
            label_bounds: Bounding box of the label
            field_name: The field being extracted

        Returns:
            List of words that are the field value
        """
        # Find the Contact Information or Home Address section header
        section_keywords = ['CONTACT INFORMATION', 'HOME ADDRESS', 'CONTACT DETAILS', 'ADDRESS']
        section_words = []

        for i, word in enumerate(words):
            word_text = word['text'].upper()
            for keyword in section_keywords:
                if keyword in word_text or any(part in word_text for part in keyword.split()):
                    section_words.append(word)
                    # Look for nearby words that might complete the section header
                    for j in range(i+1, min(i+3, len(words))):
                        next_text = words[j]['text'].upper()
                        if any(kw in next_text for kw in ['INFORMATION', 'DETAILS', 'ADDRESS']):
                            section_words.append(words[j])
                    break
            if section_words:
                break

        if not section_words:
            logger.debug(f"No Contact Information section header found")
            # Try without section - look in the general area
            return self._find_whatsapp_anywhere(words, label_bounds, field_name)

        section_bounds = self._calculate_combined_bounds(section_words)
        logger.debug(f"Found Contact Information section at y={section_bounds['y']}")

        # Determine the section boundaries
        # Section starts at the header and extends down until next major section
        section_start_y = section_bounds['y']
        section_end_y = section_start_y + 600  # Default: 600px down (larger for address section)

        # Try to find the end of this section
        end_markers = ['MOTHER', 'FATHER', 'PARENT', 'GUARDIAN', 'STUDENT INFORMATION', 'OFFICE USE']
        for word in words:
            if word['bounds']['y'] > section_start_y:
                if any(marker in word['text'].upper() for marker in end_markers):
                    section_end_y = min(section_end_y, word['bounds']['y'])
                    logger.debug(f"Contact section ends at y={section_end_y}")
                    break

        # Now look for the WhatsApp label within this section
        whatsapp_label = None
        for i, word in enumerate(words):
            word_y = word['bounds']['y']
            if section_start_y <= word_y <= section_end_y:
                word_text = word['text'].upper()
                if 'WHATSAPP' in word_text or 'W/A' in word_text or 'WA' == word_text:
                    whatsapp_label = word
                    logger.info(f"Found WHATSAPP label in Contact section at y={word_y}: '{word['text']}'")
                    break

        if not whatsapp_label:
            logger.debug(f"No WHATSAPP label found in Contact section, trying general search")
            # Fall back to general search
            return self._find_whatsapp_anywhere(words, label_bounds, field_name)

        # Extract value relative to this label
        field_label_bounds = whatsapp_label['bounds']

        # Try right of label first (same line)
        value_words = self._find_words_right_of(words, field_label_bounds, same_line=True,
                                                max_gap_multiplier=1.5)
        logger.info(f"WhatsApp - right of label: {[w['text'] for w in value_words]}")

        # Then try below (next line)
        if not value_words:
            value_words = self._find_words_below(words, field_label_bounds, max_lines=2,
                                                 allow_multiline=False)
            logger.info(f"WhatsApp - below label: {[w['text'] for w in value_words]}")

        # Filter to only include words within the section
        filtered = [w for w in value_words
                   if section_start_y <= w['bounds']['y'] <= section_end_y]

        # Additional filter: WhatsApp numbers should look like phone numbers
        phone_filtered = []
        for w in filtered:
            # Check if word looks like a phone number (digits, possibly with spaces/dashes)
            if re.match(r'^[\d\s\-\+]+$', w['text']):
                phone_filtered.append(w)
            # Also accept if it starts with 0 or +94 (Sri Lankan numbers)
            elif w['text'].startswith('0') or w['text'].startswith('+94'):
                phone_filtered.append(w)

        if phone_filtered:
            logger.info(f"WhatsApp - after phone filtering: {[w['text'] for w in phone_filtered]}")
            return phone_filtered

        logger.info(f"WhatsApp - found {len(filtered)} value words in section: {[w['text'] for w in filtered]}")
        return filtered

    def _find_whatsapp_anywhere(self, words: List[Dict], label_bounds: Dict,
                                 field_name: str) -> List[Dict]:
        """
        Find WhatsApp number anywhere in the document when section-based search fails.
        This is a fallback method.

        Args:
            words: List of all words in the document
            label_bounds: Bounding box of the label (if found)
            field_name: The field being extracted

        Returns:
            List of words that are the field value
        """
        logger.debug("Attempting fallback WhatsApp search across entire document")

        # Look for any word that contains "WHATSAPP" or similar
        whatsapp_labels = []
        for i, word in enumerate(words):
            word_text = word['text'].upper()
            if any(pattern in word_text for pattern in ['WHATSAPP', 'WHATS', 'W/A']):
                whatsapp_labels.append((i, word))

        if not whatsapp_labels:
            logger.debug("No WhatsApp label found anywhere in document")
            return []

        # Use the first WhatsApp label found
        label_idx, label_word = whatsapp_labels[0]
        logger.info(f"Found WhatsApp label at word index {label_idx}: '{label_word['text']}'")

        # Look for phone number pattern nearby (within next 10 words)
        for i in range(label_idx + 1, min(label_idx + 10, len(words))):
            word_text = words[i]['text']
            # Check if this looks like a phone number
            if re.match(r'^0\d{9}$', re.sub(r'[\s\-]', '', word_text)):
                logger.info(f"Found phone number near WhatsApp label: {word_text}")
                # Return all consecutive words that look like phone number parts
                phone_words = [words[i]]
                # Check if next words are also phone digits (in case it's split)
                for j in range(i + 1, min(i + 5, len(words))):
                    if re.match(r'^\d+$', words[j]['text']):
                        phone_words.append(words[j])
                    else:
                        break
                return phone_words

        # Try spatial extraction from the label
        value_words = self._find_words_right_of(words, label_word['bounds'], same_line=True,
                                                max_gap_multiplier=2.0)
        if not value_words:
            value_words = self._find_words_below(words, label_word['bounds'], max_lines=2,
                                                 allow_multiline=False)

        logger.info(f"Fallback WhatsApp search found: {[w['text'] for w in value_words]}")
        return value_words

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

        # Clean admission number - remove school names and unwanted text
        if 'admission_number' in processed:
            original_value = processed['admission_number']
            cleaned = self._clean_admission_number(processed['admission_number'])
            if cleaned != original_value:
                logger.info(f"Admission number cleaned: '{original_value}' -> '{cleaned}'")
            processed['admission_number'] = cleaned

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

        # Parse application date
        if 'application_date' in processed:
            app_date = processed['application_date']
            parsed_date = self._parse_date(app_date)
            if parsed_date:
                processed['application_date'] = parsed_date

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

    def _clean_admission_number(self, value):
        """
        Clean admission number by removing school names and other non-admission text.

        The OCR extraction may capture text from the school logo/header area near
        the admission number field, resulting in values like "YLE - 2021-1660 POLYMATH COLLEGE".
        This method filters out school-related words and normalizes the format.

        Args:
            value: Raw admission number value from OCR

        Returns:
            str: Cleaned admission number (e.g., "YLE-2021-1660")
        """
        if not value:
            return value

        logger.debug(f"Cleaning admission number: '{value}'")

        # Words to remove (school names, common school-related words)
        # These are often extracted from the header/logo area
        remove_words = [
            'POLYMATH', 'COLLEGE', 'SCHOOL', 'ENGLISH', 'ACADEMY',
            'UNIVERSITY', 'INSTITUTE', 'EDUCATION', 'LEARNING',
            'CENTER', 'CENTRE', 'INTERNATIONAL', 'CAMBRIDGE'
        ]

        # Split into words and filter out school-related terms
        words = value.split()
        filtered_words = []

        for word in words:
            word_upper = word.upper()
            # Skip if word is in removal list
            if word_upper in remove_words:
                logger.debug(f"  Removing school-related word: '{word}'")
                continue
            # Keep words that look like admission number parts
            # (e.g., "YLE", "2021", "1660", or with dashes like "YLE-2021-1660")
            filtered_words.append(word)

        # Join filtered words
        cleaned = ' '.join(filtered_words).strip()
        logger.debug(f"  After filtering: '{cleaned}'")

        # Normalize spacing around dashes: "YLE - 2021 - 1660" -> "YLE-2021-1660"
        cleaned = re.sub(r'\s*-\s*', '-', cleaned)
        logger.debug(f"  After dash normalization: '{cleaned}'")

        # Replace remaining spaces with dashes for multi-part admission numbers
        # "YLE 2021 1660" -> "YLE-2021-1660"
        # But only if it looks like an admission number pattern
        if re.search(r'[A-Z]+\s+\d{4}\s+\d+', cleaned):
            cleaned = re.sub(r'\s+', '-', cleaned)
            logger.debug(f"  After space-to-dash conversion: '{cleaned}'")

        # Final validation: try to extract just the admission number pattern
        # Pattern: PREFIX-YEAR-NUMBER (e.g., YLE-2021-1660)
        admission_pattern = r'([A-Z]+)-?(\d{4})-?(\d+)'
        match = re.search(admission_pattern, cleaned)
        if match:
            # Reconstruct in standard format
            prefix, year, number = match.groups()
            standardized = f"{prefix}-{year}-{number}"
            logger.debug(f"  Standardized format: '{standardized}'")
            return standardized

        logger.debug(f"  Final cleaned value: '{cleaned}'")
        return cleaned

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
        if field_name in ['date_of_birth', 'application_date']:
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
            # Pattern: PREFIX-YEAR-NUMBER (e.g., YLE-2021-1660)
            # Number part can be 1-6 digits
            if re.match(r'^[A-Z]{2,5}-\d{4}-\d{1,6}$', value):
                return 'HIGH'
            # Partial match (missing some parts but has the structure)
            elif re.match(r'^[A-Z]{2,5}-\d{4}', value):
                return 'MEDIUM'
            return 'LOW'

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
        if field_name in ['date_of_birth', 'application_date']:
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
            # Pattern: PREFIX-YEAR-NUMBER (e.g., YLE-2021-1660)
            # More flexible pattern - number part can be 1-6 digits
            return bool(re.match(r'^[A-Z]{2,5}-\d{4}-\d{1,6}$', value))

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
