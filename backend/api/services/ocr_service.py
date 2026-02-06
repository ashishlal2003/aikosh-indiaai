"""
OCR Service for document text extraction and structured data parsing.
Uses IndicPhotoOCR (Bhashini/IIT Jodhpur) for Indian language OCR.
Uses Groq LLM for extracting structured invoice/document data.
"""

import os
import logging
import tempfile
import json
from pathlib import Path
from typing import Dict, Optional, List, Any
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

logger = logging.getLogger(__name__)

# Lazy load IndicPhotoOCR to avoid import errors if not installed
_ocr_system = None


def get_ocr_system():
    """Lazy load OCR system to avoid slow imports on startup."""
    global _ocr_system
    if _ocr_system is None:
        try:
            from IndicPhotoOCR.ocr import OCR
            _ocr_system = OCR(verbose=False)
            logger.info("[OCR] IndicPhotoOCR initialized successfully")
        except ImportError as e:
            logger.warning(f"[OCR] IndicPhotoOCR not available: {e}. Falling back to basic extraction.")
            _ocr_system = "fallback"
        except Exception as e:
            logger.error(f"[OCR] Error initializing IndicPhotoOCR: {e}")
            _ocr_system = "fallback"
    return _ocr_system


class OCRService:
    """
    Service for extracting text from documents and images.
    Supports invoices, purchase orders, and other MSME documents.
    """

    # Fields to extract from invoices
    INVOICE_FIELDS = [
        "invoice_number",
        "invoice_date",
        "due_date",
        "seller_name",
        "seller_gstin",
        "seller_address",
        "buyer_name",
        "buyer_gstin",
        "buyer_address",
        "total_amount",
        "tax_amount",
        "items",  # List of line items
        "payment_terms",
        "bank_details",
    ]

    def __init__(self):
        """Initialize OCR service with Groq client for structured extraction."""
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        if not self.groq_api_key:
            logger.warning("GROQ_API_KEY not found - structured extraction will be limited")
            self.groq_client = None
        else:
            self.groq_client = Groq(api_key=self.groq_api_key)

        self.model = "llama-3.1-8b-instant"

    def extract_text_from_image(self, image_path: str, language: str = "hi") -> str:
        """
        Extract text from image using IndicPhotoOCR.

        Args:
            image_path: Path to image file
            language: Language code (hi=Hindi, en=English, ta=Tamil, etc.)

        Returns:
            Extracted text string
        """
        ocr = get_ocr_system()

        if ocr == "fallback":
            logger.warning("[OCR] Using fallback - no OCR available")
            return "[OCR not available - please install IndicPhotoOCR]"

        try:
            logger.info(f"[OCR] Extracting text from: {image_path}")

            # Run OCR
            results = ocr.ocr(image_path)

            # Combine all detected text
            extracted_texts = []
            if results:
                for result in results:
                    if isinstance(result, dict) and 'text' in result:
                        extracted_texts.append(result['text'])
                    elif isinstance(result, (list, tuple)) and len(result) > 1:
                        # Handle different result formats
                        text = result[1] if len(result) > 1 else result[0]
                        if isinstance(text, str):
                            extracted_texts.append(text)
                        elif isinstance(text, (list, tuple)) and len(text) > 0:
                            extracted_texts.append(str(text[0]))

            full_text = "\n".join(extracted_texts)
            logger.info(f"[OCR] Extracted {len(full_text)} characters")

            return full_text if full_text else "[No text detected in image]"

        except Exception as e:
            logger.error(f"[OCR] Error extracting text: {e}")
            return f"[OCR Error: {str(e)}]"

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract text from PDF file.
        Uses pypdf for digital PDFs, converts to image for scanned PDFs.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text string
        """
        try:
            from pypdf import PdfReader

            reader = PdfReader(pdf_path)
            text_parts = []

            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

            full_text = "\n\n".join(text_parts)

            # If no text extracted (scanned PDF), try OCR
            if not full_text.strip():
                logger.info("[OCR] PDF appears to be scanned, attempting image conversion")
                return self._ocr_scanned_pdf(pdf_path)

            logger.info(f"[OCR] Extracted {len(full_text)} characters from PDF")
            return full_text

        except Exception as e:
            logger.error(f"[OCR] Error reading PDF: {e}")
            return f"[PDF Error: {str(e)}]"

    def _ocr_scanned_pdf(self, pdf_path: str) -> str:
        """
        Convert scanned PDF to images and OCR each page.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text string
        """
        try:
            from pdf2image import convert_from_path

            # Convert PDF pages to images
            images = convert_from_path(pdf_path, dpi=200)

            all_text = []
            for i, image in enumerate(images):
                # Save temp image
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    image.save(tmp.name, 'PNG')
                    page_text = self.extract_text_from_image(tmp.name)
                    all_text.append(f"--- Page {i+1} ---\n{page_text}")
                    os.unlink(tmp.name)  # Clean up temp file

            return "\n\n".join(all_text)

        except ImportError:
            logger.warning("[OCR] pdf2image not available for scanned PDF OCR")
            return "[Scanned PDF - pdf2image required for OCR]"
        except Exception as e:
            logger.error(f"[OCR] Error OCRing scanned PDF: {e}")
            return f"[Scanned PDF OCR Error: {str(e)}]"

    def extract_structured_data(
        self,
        raw_text: str,
        document_type: str = "invoice"
    ) -> Dict[str, Any]:
        """
        Use LLM to extract structured data from raw OCR text.

        Args:
            raw_text: Raw text from OCR
            document_type: Type of document (invoice, po, receipt, etc.)

        Returns:
            Dictionary with extracted fields
        """
        if not self.groq_client:
            return {
                "raw_text": raw_text,
                "error": "Groq client not available for structured extraction"
            }

        if not raw_text or raw_text.startswith("["):
            return {
                "raw_text": raw_text,
                "error": "No valid text to extract from"
            }

        # Build extraction prompt based on document type
        if document_type == "invoice":
            prompt = self._build_invoice_extraction_prompt(raw_text)
        elif document_type == "purchase_order":
            prompt = self._build_po_extraction_prompt(raw_text)
        else:
            prompt = self._build_generic_extraction_prompt(raw_text)

        try:
            response = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a document extraction AI. Extract structured data from documents and return valid JSON only. Be precise with numbers and dates."},
                    {"role": "user", "content": prompt}
                ],
                model=self.model,
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=1024,
            )

            result_text = response.choices[0].message.content

            # Try to parse JSON from response
            try:
                # Find JSON in response (handle markdown code blocks)
                if "```json" in result_text:
                    json_str = result_text.split("```json")[1].split("```")[0]
                elif "```" in result_text:
                    json_str = result_text.split("```")[1].split("```")[0]
                else:
                    json_str = result_text

                extracted_data = json.loads(json_str.strip())
                extracted_data["raw_text"] = raw_text
                extracted_data["extraction_status"] = "success"

                logger.info(f"[OCR] Successfully extracted structured data: {list(extracted_data.keys())}")
                return extracted_data

            except json.JSONDecodeError:
                logger.warning("[OCR] Could not parse LLM response as JSON")
                return {
                    "raw_text": raw_text,
                    "llm_response": result_text,
                    "extraction_status": "partial"
                }

        except Exception as e:
            logger.error(f"[OCR] Error in LLM extraction: {e}")
            return {
                "raw_text": raw_text,
                "error": str(e),
                "extraction_status": "failed"
            }

    def _build_invoice_extraction_prompt(self, raw_text: str) -> str:
        """Build prompt for invoice data extraction."""
        return f"""Extract the following information from this invoice text and return as JSON:

Required fields:
- invoice_number: The invoice/bill number
- invoice_date: Date of invoice (format: YYYY-MM-DD)
- due_date: Payment due date if mentioned (format: YYYY-MM-DD)
- seller_name: Name of the seller/vendor company
- seller_gstin: Seller's GST number (15 characters)
- buyer_name: Name of the buyer company
- buyer_gstin: Buyer's GST number if present
- total_amount: Total invoice amount (number only, in INR)
- tax_amount: Tax/GST amount if shown separately
- items: List of items with description, quantity, rate, amount
- payment_terms: Payment terms if mentioned

Return ONLY valid JSON, no explanations.

Invoice Text:
---
{raw_text}
---

JSON:"""

    def _build_po_extraction_prompt(self, raw_text: str) -> str:
        """Build prompt for purchase order data extraction."""
        return f"""Extract the following information from this purchase order and return as JSON:

Required fields:
- po_number: Purchase order number
- po_date: Date of PO (format: YYYY-MM-DD)
- buyer_name: Name of the buyer company
- buyer_address: Buyer's address
- seller_name: Name of the vendor/supplier
- items: List of ordered items with description, quantity, rate
- total_amount: Total PO value
- delivery_date: Expected delivery date if mentioned
- payment_terms: Payment terms

Return ONLY valid JSON, no explanations.

Purchase Order Text:
---
{raw_text}
---

JSON:"""

    def _build_generic_extraction_prompt(self, raw_text: str) -> str:
        """Build prompt for generic document extraction."""
        return f"""Extract key information from this document and return as JSON:

Try to identify:
- document_type: What type of document is this?
- date: Any dates mentioned
- parties: Names of companies/people involved
- amounts: Any monetary amounts
- reference_numbers: Any reference/ID numbers
- key_details: Other important information

Return ONLY valid JSON, no explanations.

Document Text:
---
{raw_text}
---

JSON:"""

    def process_document(
        self,
        file_path: str,
        file_type: str,
        document_type: str = "invoice"
    ) -> Dict[str, Any]:
        """
        Full document processing pipeline: OCR + structured extraction.

        Args:
            file_path: Path to document file
            file_type: MIME type of file
            document_type: Type of document for extraction

        Returns:
            Dictionary with extracted data and metadata
        """
        logger.info(f"[OCR] Processing document: {file_path} ({file_type})")

        # Step 1: Extract raw text
        if "pdf" in file_type.lower():
            raw_text = self.extract_text_from_pdf(file_path)
        elif "image" in file_type.lower():
            raw_text = self.extract_text_from_image(file_path)
        else:
            raw_text = "[Unsupported file type for OCR]"

        # Step 2: Extract structured data
        structured_data = self.extract_structured_data(raw_text, document_type)

        # Add file metadata
        structured_data["file_path"] = file_path
        structured_data["file_type"] = file_type
        structured_data["document_type"] = document_type

        return structured_data

    def format_for_chat(self, extracted_data: Dict[str, Any]) -> str:
        """
        Format extracted data as a readable string for chat display.

        Args:
            extracted_data: Dictionary with extracted document data

        Returns:
            Formatted string for display
        """
        if extracted_data.get("extraction_status") == "failed":
            return f"""📄 **Document Uploaded**

⚠️ Could not fully extract document details.

Raw text preview:
```
{extracted_data.get('raw_text', 'No text extracted')[:500]}...
```

Please verify the document is clear and try again, or manually enter the details."""

        lines = ["📄 **Document Extracted Successfully**\n"]

        # Invoice-specific formatting
        if extracted_data.get("invoice_number"):
            lines.append(f"**Invoice Number:** {extracted_data['invoice_number']}")
        if extracted_data.get("invoice_date"):
            lines.append(f"**Invoice Date:** {extracted_data['invoice_date']}")
        if extracted_data.get("seller_name"):
            lines.append(f"**Seller:** {extracted_data['seller_name']}")
        if extracted_data.get("seller_gstin"):
            lines.append(f"**Seller GSTIN:** {extracted_data['seller_gstin']}")
        if extracted_data.get("buyer_name"):
            lines.append(f"**Buyer:** {extracted_data['buyer_name']}")
        if extracted_data.get("buyer_gstin"):
            lines.append(f"**Buyer GSTIN:** {extracted_data['buyer_gstin']}")
        if extracted_data.get("total_amount"):
            lines.append(f"**Total Amount:** ₹{extracted_data['total_amount']}")
        if extracted_data.get("tax_amount"):
            lines.append(f"**Tax/GST:** ₹{extracted_data['tax_amount']}")
        if extracted_data.get("due_date"):
            lines.append(f"**Due Date:** {extracted_data['due_date']}")
        if extracted_data.get("payment_terms"):
            lines.append(f"**Payment Terms:** {extracted_data['payment_terms']}")

        # Items if present
        items = extracted_data.get("items", [])
        if items and isinstance(items, list):
            lines.append("\n**Items:**")
            for item in items[:5]:  # Show first 5 items
                if isinstance(item, dict):
                    desc = item.get("description", item.get("name", "Item"))
                    qty = item.get("quantity", "")
                    amt = item.get("amount", item.get("rate", ""))
                    lines.append(f"  • {desc} {f'(Qty: {qty})' if qty else ''} {f'- ₹{amt}' if amt else ''}")
                else:
                    lines.append(f"  • {item}")

        lines.append("\n✅ *Please verify these details are correct.*")

        return "\n".join(lines)


# Singleton instance
_ocr_service = None


def get_ocr_service() -> OCRService:
    """Get or create singleton OCR service instance."""
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService()
    return _ocr_service
