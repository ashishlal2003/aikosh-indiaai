"""
Document OCR and Entity Extraction
Processes uploaded documents (invoices, etc.) and extracts structured data
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import structlog

try:
    import easyocr
    import cv2
    import numpy as np
    from PIL import Image
except ImportError as e:
    raise ImportError(
        f"Missing required dependencies for OCR: {e}. "
        "Install with: pip install easyocr opencv-python Pillow numpy"
    )

from src.models.dispute import Document

logger = structlog.get_logger()


class DocumentProcessor:
    """
    OCR and entity extraction processor for MSME dispute documents
    Supports Indian languages and extracts key invoice entities
    """

    def __init__(self, languages: List[str] = None):
        """
        Initialize the document processor with OCR capabilities

        Args:
            languages: List of language codes (default: ['en', 'hi', 'ta', 'kn'])
        """
        if languages is None:
            languages = ['en', 'hi', 'ta', 'kn']  # English, Hindi, Tamil, Kannada

        self.languages = languages
        self.reader = None
        self._initialize_reader()

        logger.info("DocumentProcessor initialized", languages=languages)

    def _initialize_reader(self) -> None:
        """Initialize EasyOCR reader with configured languages"""
        try:
            self.reader = easyocr.Reader(
                self.languages,
                gpu=False,  # Use CPU for broader compatibility
                verbose=False
            )
            logger.info("EasyOCR reader initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize EasyOCR reader", error=str(e))
            raise RuntimeError(f"OCR initialization failed: {e}")

    def process_document(
        self,
        file_path: str,
        document_type: str,
        name: Optional[str] = None
    ) -> Document:
        """
        Process a document: extract text, entities, and validate

        Args:
            file_path: Path to the document file
            document_type: Type of document (e.g., 'invoice', 'delivery_proof')
            name: Document name (defaults to document_type)

        Returns:
            Document model with populated OCR data and extracted entities
        """
        logger.info("Processing document", file_path=file_path, document_type=document_type)

        if name is None:
            name = document_type

        # Initialize document
        document = Document(
            name=name,
            file_path=file_path,
            is_mandatory=True if document_type in ['invoice', 'msme_registration'] else False
        )

        try:
            # Load and preprocess image
            image = self._load_image(file_path)

            # Extract text via OCR
            ocr_text, confidence = self.extract_text(image)
            document.ocr_text = ocr_text

            logger.info("OCR extraction completed", confidence=confidence)

            # Extract entities based on document type
            if document_type == 'invoice':
                entities = self.extract_entities(ocr_text, document_type)
                document.extracted_entities = entities

                # Validate extracted entities
                validation_errors = self._validate_entities(entities)
                document.validation_errors = validation_errors

                # Mark as verified if no critical errors
                document.is_verified = len(validation_errors) == 0

                logger.info(
                    "Entity extraction completed",
                    entities_found=len(entities),
                    validation_errors=len(validation_errors)
                )
            else:
                # For non-invoice documents, just store OCR text
                document.is_verified = True
                document.extracted_entities = {"confidence": confidence}

        except Exception as e:
            logger.error("Document processing failed", error=str(e), file_path=file_path)
            document.validation_errors.append(f"Processing error: {str(e)}")
            document.is_verified = False

        return document

    def _load_image(self, file_path: str) -> np.ndarray:
        """
        Load and preprocess image for OCR

        Args:
            file_path: Path to image file

        Returns:
            Preprocessed image as numpy array
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")

        # Handle different file types
        if path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
            # Load image using OpenCV
            image = cv2.imread(str(path))
            if image is None:
                raise ValueError(f"Failed to load image: {file_path}")

            # Preprocess: convert to grayscale and enhance contrast
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            # Apply adaptive thresholding for better OCR
            processed = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            return processed

        elif path.suffix.lower() == '.pdf':
            # For PDF support, we'd need pdf2image library
            # For MVP, raise error and suggest image format
            raise ValueError("PDF support requires additional setup. Please upload JPG/PNG.")

        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")

    def extract_text(self, image: np.ndarray) -> tuple[str, float]:
        """
        Extract text from image using OCR

        Args:
            image: Image as numpy array

        Returns:
            Tuple of (extracted_text, average_confidence)
        """
        if self.reader is None:
            raise RuntimeError("OCR reader not initialized")

        try:
            # Run OCR
            results = self.reader.readtext(image)

            # Combine all detected text
            text_lines = []
            confidences = []

            for detection in results:
                bbox, text, confidence = detection
                text_lines.append(text)
                confidences.append(confidence)

            full_text = "\n".join(text_lines)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            return full_text, avg_confidence

        except Exception as e:
            logger.error("OCR text extraction failed", error=str(e))
            raise RuntimeError(f"OCR failed: {e}")

    def extract_entities(self, text: str, document_type: str) -> Dict[str, Any]:
        """
        Extract structured entities from OCR text using regex patterns

        Args:
            text: OCR extracted text
            document_type: Type of document

        Returns:
            Dictionary of extracted entities
        """
        entities = {}

        if document_type == 'invoice':
            # Extract invoice number
            entities['invoice_number'] = self._extract_invoice_number(text)

            # Extract dates
            entities['invoice_date'] = self._extract_date(text, 'invoice')

            # Extract amounts
            entities['total_amount'] = self._extract_amount(text)

            # Extract party names
            entities['buyer_name'] = self._extract_party_name(text, 'buyer')
            entities['seller_name'] = self._extract_party_name(text, 'seller')

            # Extract GSTIN numbers
            entities['buyer_gstin'] = self._extract_gstin(text, 'buyer')
            entities['seller_gstin'] = self._extract_gstin(text, 'seller')

        return entities

    def _extract_invoice_number(self, text: str) -> Optional[str]:
        """Extract invoice number from text"""
        patterns = [
            r'invoice\s*(?:no|number|#|num)[:\s]+([A-Z0-9\-/]+)',
            r'bill\s*(?:no|number|#|num)[:\s]+([A-Z0-9\-/]+)',
            r'inv\s*(?:no|#|num)[:\s]+([A-Z0-9\-/]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                invoice_num = match.group(1).strip()
                # Filter out matches that are just words (like "Invoice")
                if len(invoice_num) > 2 and any(c.isdigit() for c in invoice_num):
                    return invoice_num

        return None

    def _extract_date(self, text: str, context: str = 'invoice') -> Optional[datetime]:
        """
        Extract and parse dates from text
        Supports Indian date formats: DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
        """
        date_patterns = [
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',  # DD/MM/YYYY or DD-MM-YYYY
            r'(\d{1,2})\.(\d{1,2})\.(\d{4})',      # DD.MM.YYYY
        ]

        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    day, month, year = match.groups()
                    date = datetime(int(year), int(month), int(day))
                    return date
                except ValueError:
                    continue

        return None

    def _extract_amount(self, text: str) -> Optional[float]:
        """
        Extract and parse amount from text
        Supports Indian currency formats: ₹10,00,000 or Rs. 100000 or 1,00,000.00
        """
        # Remove currency symbols and parse
        patterns = [
            r'total[:\s]+(?:₹|Rs\.?\s*)?([0-9,]+\.?\d{0,2})',
            r'amount[:\s]+(?:₹|Rs\.?\s*)?([0-9,]+\.?\d{0,2})',
            r'₹\s*([0-9,]+\.?\d{0,2})',
            r'Rs\.?\s+([0-9,]+\.?\d{0,2})',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1)
                return self.validate_amount(amount_str)

        return None

    def _extract_party_name(self, text: str, party_type: str) -> Optional[str]:
        """Extract buyer or seller name from text"""
        if party_type == 'buyer':
            patterns = [
                r'(?:bill to|buyer|customer)[:\s]+([A-Za-z\s&.]+?)(?:\n|GSTIN)',
                r'(?:to|buyer)[:\s]+([A-Za-z\s&.]+?)(?:\n)',
            ]
        else:  # seller
            patterns = [
                r'(?:from|seller|vendor)[:\s]+([A-Za-z\s&.]+?)(?:\n|GSTIN)',
                r'(?:seller|vendor)[:\s]+([A-Za-z\s&.]+?)(?:\n)',
            ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Clean up the name (remove extra spaces, newlines)
                name = re.sub(r'\s+', ' ', name)
                return name

        return None

    def _extract_gstin(self, text: str, party_type: str) -> Optional[str]:
        """
        Extract GSTIN number from text
        Looks for buyer/seller context around GSTIN
        """
        # Find all GSTIN-like patterns
        gstin_pattern = r'\b([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[Z]{1}[0-9A-Z]{1})\b'
        matches = re.findall(gstin_pattern, text)

        if not matches:
            return None

        # If only one GSTIN found, return it
        if len(matches) == 1:
            return matches[0]

        # If multiple GSTINs, try to determine which is buyer/seller
        # Look for context around the GSTIN
        for match in matches:
            # Find position of GSTIN in text
            pos = text.find(match)
            # Get surrounding context (100 chars before)
            context = text[max(0, pos-100):pos].lower()

            if party_type == 'buyer' and any(word in context for word in ['buyer', 'bill to', 'customer']):
                return match
            elif party_type == 'seller' and any(word in context for word in ['seller', 'vendor', 'from']):
                return match

        # Default: return first for seller, second for buyer
        return matches[0] if party_type == 'seller' and len(matches) > 0 else matches[-1]

    def validate_gstin(self, gstin: str) -> bool:
        """
        Validate GSTIN format
        GSTIN format: 22AAAAA0000A1Z5 (15 characters)
        """
        if not gstin or len(gstin) != 15:
            return False

        # Regex pattern for GSTIN validation
        pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[Z]{1}[0-9A-Z]{1}$'
        return bool(re.match(pattern, gstin))

    def validate_amount(self, amount_str: str) -> Optional[float]:
        """
        Parse and validate amount from string
        Handles Indian number formats with commas
        """
        if not amount_str:
            return None

        try:
            # Remove currency symbols but keep numbers, commas, and decimals
            cleaned = amount_str.strip()
            # Remove currency symbol ₹
            cleaned = cleaned.replace('₹', '')
            # Remove Rs followed by optional period
            cleaned = re.sub(r'Rs\.?\s*', '', cleaned)
            # Remove spaces
            cleaned = re.sub(r'\s+', '', cleaned)
            # Remove commas (Indian format uses commas as thousands separators)
            cleaned = cleaned.replace(',', '')

            amount = float(cleaned)

            # Validate positive amount
            if amount > 0:
                return round(amount, 2)

        except (ValueError, TypeError):
            logger.warning("Failed to parse amount", amount_str=amount_str)

        return None

    def validate_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse and validate date from string
        Supports Indian date formats
        """
        if not date_str:
            return None

        formats = [
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%d.%m.%Y',
            '%d/%m/%y',
            '%d-%m-%y',
        ]

        for fmt in formats:
            try:
                date = datetime.strptime(date_str, fmt)
                # Validate date is reasonable (not in future, not too old)
                if date <= datetime.now() and date.year >= 2000:
                    return date
            except ValueError:
                continue

        return None

    def _validate_entities(self, entities: Dict[str, Any]) -> List[str]:
        """
        Validate extracted entities

        Args:
            entities: Dictionary of extracted entities

        Returns:
            List of validation error messages
        """
        errors = []

        # Check for missing critical fields
        if not entities.get('invoice_number'):
            errors.append("Invoice number not found")

        if not entities.get('invoice_date'):
            errors.append("Invoice date not found or invalid")

        if not entities.get('total_amount'):
            errors.append("Total amount not found or invalid")

        # Validate GSTIN format if present
        buyer_gstin = entities.get('buyer_gstin')
        if buyer_gstin and not self.validate_gstin(buyer_gstin):
            errors.append(f"Invalid buyer GSTIN format: {buyer_gstin}")

        seller_gstin = entities.get('seller_gstin')
        if seller_gstin and not self.validate_gstin(seller_gstin):
            errors.append(f"Invalid seller GSTIN format: {seller_gstin}")

        # Validate amount is reasonable
        amount = entities.get('total_amount')
        if amount and amount > 100000000:  # 10 crores
            errors.append("Amount seems unusually high, please verify")

        # Validate date is reasonable
        invoice_date = entities.get('invoice_date')
        if invoice_date:
            if invoice_date > datetime.now():
                errors.append("Invoice date cannot be in the future")
            if (datetime.now() - invoice_date).days > 1095:  # 3 years
                errors.append("Invoice date is more than 3 years old")

        return errors
