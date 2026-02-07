"""
OCR Service for document text extraction and structured data parsing.
Uses Tesseract OCR for English, Hindi, and Kannada text extraction.
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

# Lazy load Tesseract to verify availability
_ocr_available = None


def get_ocr_system():
    """Check if Tesseract OCR is available."""
    global _ocr_available
    if _ocr_available is None:
        try:
            import pytesseract
            # Verify tesseract is installed
            version = pytesseract.get_tesseract_version()
            logger.info(f"[OCR] Tesseract v{version} initialized successfully")
            _ocr_available = True
        except Exception as e:
            logger.warning(f"[OCR] Tesseract not available: {e}")
            _ocr_available = False
    return _ocr_available


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

    # Language code mapping for Tesseract
    LANG_MAP = {
        "en": "eng",
        "hi": "hin",
        "kn": "kan",
        "kan": "kan",
        "hin": "hin",
        "eng": "eng",
        "english": "eng",
        "hindi": "hin",
        "kannada": "kan",
    }

    def extract_text_from_image(self, image_path: str, language: str = "eng+hin+kan") -> str:
        """
        Extract text from image using Tesseract OCR.

        Args:
            image_path: Path to image file
            language: Language code(s) - can be "eng", "hin", "kan" or combined "eng+hin+kan"

        Returns:
            Extracted text string
        """
        if not get_ocr_system():
            logger.warning("[OCR] Tesseract not available")
            return "[OCR not available - please install tesseract-ocr]"

        try:
            import pytesseract
            from PIL import Image

            logger.info(f"[OCR] Extracting text from: {image_path}")

            # Open and preprocess image
            img = Image.open(image_path)

            # Convert to RGB if necessary (handles RGBA, grayscale, etc.)
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')

            # Map language codes to Tesseract format
            lang_codes = []
            for lang in language.split('+'):
                mapped = self.LANG_MAP.get(lang.lower(), lang)
                if mapped not in lang_codes:
                    lang_codes.append(mapped)
            tesseract_lang = '+'.join(lang_codes)

            logger.info(f"[OCR] Using languages: {tesseract_lang}")

            # Run Tesseract OCR
            text = pytesseract.image_to_string(img, lang=tesseract_lang)

            # Clean up text
            full_text = text.strip()
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

    def _ocr_scanned_pdf(self, pdf_path: str, language: str = "eng+hin+kan") -> str:
        """
        Convert scanned PDF to images and OCR each page.

        Args:
            pdf_path: Path to PDF file
            language: Language code(s) for OCR

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
                    page_text = self.extract_text_from_image(tmp.name, language=language)
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
        elif document_type == "msme_certificate":
            prompt = self._build_msme_certificate_extraction_prompt(raw_text)
        elif document_type == "delivery_proof":
            prompt = self._build_delivery_proof_extraction_prompt(raw_text)
        elif document_type == "communication":
            prompt = self._build_communication_extraction_prompt(raw_text)
        elif document_type == "bank_statement":
            prompt = self._build_bank_statement_extraction_prompt(raw_text)
        elif document_type == "legal_notice":
            prompt = self._build_legal_notice_extraction_prompt(raw_text)
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

## TBD - so manyy functions and prompts - need to refactor
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

IMPORTANT: If a field is not clearly visible in the text, set it to null. DO NOT make up or guess values.

Return ONLY valid JSON, no explanations.

Document Text:
---
{raw_text}
---

JSON:"""

    def _build_msme_certificate_extraction_prompt(self, raw_text: str) -> str:
        """Build prompt for MSME/Udyam certificate extraction."""
        return f"""Extract the following information from this MSME/Udyam Registration Certificate and return as JSON:

Required fields:
- udyam_registration_number: The Udyam Registration Number (format: UDYAM-XX-00-0000000)
- enterprise_name: Name of the enterprise/business
- enterprise_type: Type (Micro/Small/Medium)
- owner_name: Name of the owner/proprietor
- date_of_registration: Registration date (format: YYYY-MM-DD)
- date_of_incorporation: Incorporation date if mentioned
- major_activity: NIC code or activity description
- address: Registered address
- district: District name
- state: State name
- mobile: Mobile number if present
- email: Email if present

CRITICAL: If a field is not clearly visible in the text, set it to null. DO NOT guess or make up values.
If the text appears to be garbage/unreadable, set all fields to null and add "extraction_quality": "poor".

Return ONLY valid JSON, no explanations.

Certificate Text:
---
{raw_text}
---

JSON:"""

    def _build_delivery_proof_extraction_prompt(self, raw_text: str) -> str:
        """Build prompt for delivery receipt/proof extraction."""
        return f"""Extract the following information from this delivery receipt/proof and return as JSON:

Required fields:
- delivery_date: Date of delivery (format: YYYY-MM-DD)
- delivery_challan_number: Challan/receipt number
- receiver_name: Name of person who received
- receiver_signature: Whether signature is present (true/false)
- sender_name: Sender/supplier company name
- recipient_company: Receiving company name
- items_delivered: List of items with quantities
- vehicle_number: Vehicle/transport details if present
- remarks: Any remarks or notes

CRITICAL: If a field is not clearly visible in the text, set it to null. DO NOT guess or make up values.

Return ONLY valid JSON, no explanations.

Delivery Proof Text:
---
{raw_text}
---

JSON:"""

    def _build_communication_extraction_prompt(self, raw_text: str) -> str:
        """Build prompt for email/communication extraction."""
        return f"""Extract the following information from this email/communication and return as JSON:

Required fields:
- date: Date of communication (format: YYYY-MM-DD)
- from: Sender name/email
- to: Recipient name/email
- subject: Subject line
- key_points: List of main points discussed
- payment_mentioned: Whether payment/amount is discussed (true/false)
- amount_mentioned: Any specific amount mentioned
- deadline_mentioned: Any deadline or due date mentioned
- tone: Overall tone (formal/informal/threatening/reminder)

CRITICAL: If a field is not clearly visible in the text, set it to null. DO NOT guess or make up values.

Return ONLY valid JSON, no explanations.

Communication Text:
---
{raw_text}
---

JSON:"""

    def _build_bank_statement_extraction_prompt(self, raw_text: str) -> str:
        """Build prompt for bank statement extraction."""
        return f"""Extract the following information from this bank statement and return as JSON:

Required fields:
- account_holder_name: Name on the account
- account_number: Bank account number (may be partially masked)
- bank_name: Name of the bank
- statement_period: Start and end date of statement
- transactions: List of transactions with date, description, amount, type (credit/debit)
- opening_balance: Opening balance
- closing_balance: Closing balance
- payment_received_from: Any payments received from the buyer in dispute

CRITICAL: If a field is not clearly visible in the text, set it to null. DO NOT guess or make up values.

Return ONLY valid JSON, no explanations.

Bank Statement Text:
---
{raw_text}
---

JSON:"""

    def _build_legal_notice_extraction_prompt(self, raw_text: str) -> str:
        """Build prompt for legal notice extraction."""
        return f"""Extract the following information from this legal notice and return as JSON:

Required fields:
- notice_date: Date of notice (format: YYYY-MM-DD)
- from_party: Who is sending the notice
- to_party: Who is receiving the notice
- lawyer_name: Lawyer/advocate name if mentioned
- subject_matter: What the notice is about
- amount_claimed: Amount being claimed
- deadline_given: Response deadline
- legal_sections_cited: Any laws/sections mentioned
- relief_sought: What action is demanded

CRITICAL: If a field is not clearly visible in the text, set it to null. DO NOT guess or make up values.

Return ONLY valid JSON, no explanations.

Legal Notice Text:
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

    def _count_extracted_fields(self, data: Dict[str, Any]) -> int:
        """Count how many fields were successfully extracted (non-null, non-empty)."""
        excluded_keys = {'raw_text', 'extraction_status', 'file_path', 'file_type',
                         'document_type', 'error', 'llm_response', 'extraction_quality'}
        count = 0
        for key, value in data.items():
            if key in excluded_keys:
                continue
            if value is not None and value != "" and value != []:
                count += 1
        return count

    def format_for_chat(self, extracted_data: Dict[str, Any]) -> str:
        """
        Format extracted data as a readable string for chat display.

        Args:
            extracted_data: Dictionary with extracted document data

        Returns:
            Formatted string for display
        """
        doc_type = extracted_data.get("document_type", "unknown")

        # Check extraction quality
        if extracted_data.get("extraction_status") == "failed":
            return self._format_failed_extraction(extracted_data)

        if extracted_data.get("extraction_quality") == "poor":
            return self._format_poor_extraction(extracted_data)

        # Count how many fields were extracted
        field_count = self._count_extracted_fields(extracted_data)

        if field_count < 2:
            return self._format_insufficient_extraction(extracted_data)

        # Route to document-specific formatters
        if doc_type == "invoice":
            return self._format_invoice(extracted_data)
        elif doc_type == "purchase_order":
            return self._format_purchase_order(extracted_data)
        elif doc_type == "msme_certificate":
            return self._format_msme_certificate(extracted_data)
        elif doc_type == "delivery_proof":
            return self._format_delivery_proof(extracted_data)
        elif doc_type == "communication":
            return self._format_communication(extracted_data)
        elif doc_type == "bank_statement":
            return self._format_bank_statement(extracted_data)
        elif doc_type == "legal_notice":
            return self._format_legal_notice(extracted_data)
        else:
            return self._format_generic(extracted_data)

    def _format_failed_extraction(self, data: Dict[str, Any]) -> str:
        """Format message for failed extraction."""
        raw_preview = data.get('raw_text', 'No text extracted')[:300]
        return f"""📄 **Document Uploaded**

⚠️ **Could not extract document details.**

Raw text preview:
```
{raw_preview}...
```

The document may be unclear, rotated, or in an unsupported format.
Please upload a clearer image or manually tell me the key details."""

    def _format_poor_extraction(self, data: Dict[str, Any]) -> str:
        """Format message for poor quality extraction."""
        return f"""📄 **Document Uploaded**

⚠️ **Low quality extraction** - The text in this document was difficult to read.

I could not reliably extract the details. Please:
1. Upload a clearer/higher resolution image, OR
2. Tell me the key details from this document manually

What information does this document contain?"""

    def _format_insufficient_extraction(self, data: Dict[str, Any]) -> str:
        """Format message when too few fields were extracted."""
        doc_type = data.get("document_type", "document")
        raw_preview = data.get('raw_text', '')[:200]
        return f"""📄 **Document Uploaded** ({doc_type})

⚠️ **Incomplete extraction** - I could only extract limited information from this document.

Raw text I found:
```
{raw_preview}...
```

Please tell me the key details from this {doc_type} so I can proceed with your case."""

    def _format_invoice(self, data: Dict[str, Any]) -> str:
        """Format invoice extraction."""
        lines = ["📄 **Invoice Extracted**\n"]

        if data.get("invoice_number"):
            lines.append(f"**Invoice Number:** {data['invoice_number']}")
        if data.get("invoice_date"):
            lines.append(f"**Invoice Date:** {data['invoice_date']}")
        if data.get("seller_name"):
            lines.append(f"**Seller:** {data['seller_name']}")
        if data.get("seller_gstin"):
            lines.append(f"**Seller GSTIN:** {data['seller_gstin']}")
        if data.get("buyer_name"):
            lines.append(f"**Buyer:** {data['buyer_name']}")
        if data.get("buyer_gstin"):
            lines.append(f"**Buyer GSTIN:** {data['buyer_gstin']}")
        if data.get("total_amount"):
            lines.append(f"**Total Amount:** ₹{data['total_amount']}")
        if data.get("tax_amount"):
            lines.append(f"**Tax/GST:** ₹{data['tax_amount']}")
        if data.get("due_date"):
            lines.append(f"**Due Date:** {data['due_date']}")
        if data.get("payment_terms"):
            lines.append(f"**Payment Terms:** {data['payment_terms']}")

        items = data.get("items", [])
        if items and isinstance(items, list):
            lines.append("\n**Items:**")
            for item in items[:5]:
                if isinstance(item, dict):
                    desc = item.get("description", item.get("name", "Item"))
                    qty = item.get("quantity", "")
                    amt = item.get("amount", item.get("rate", ""))
                    lines.append(f"  • {desc} {f'(Qty: {qty})' if qty else ''} {f'- ₹{amt}' if amt else ''}")
                else:
                    lines.append(f"  • {item}")

        lines.append("\n✅ *Please verify these details are correct.*")
        return "\n".join(lines)

    def _format_purchase_order(self, data: Dict[str, Any]) -> str:
        """Format purchase order extraction."""
        lines = ["📄 **Purchase Order Extracted**\n"]

        if data.get("po_number"):
            lines.append(f"**PO Number:** {data['po_number']}")
        if data.get("po_date"):
            lines.append(f"**PO Date:** {data['po_date']}")
        if data.get("buyer_name"):
            lines.append(f"**Buyer:** {data['buyer_name']}")
        if data.get("seller_name"):
            lines.append(f"**Supplier:** {data['seller_name']}")
        if data.get("total_amount"):
            lines.append(f"**Total Value:** ₹{data['total_amount']}")
        if data.get("delivery_date"):
            lines.append(f"**Delivery Date:** {data['delivery_date']}")
        if data.get("payment_terms"):
            lines.append(f"**Payment Terms:** {data['payment_terms']}")

        lines.append("\n✅ *Please verify these details are correct.*")
        return "\n".join(lines)

    def _format_msme_certificate(self, data: Dict[str, Any]) -> str:
        """Format MSME/Udyam certificate extraction."""
        lines = ["📄 **MSME/Udyam Certificate Extracted**\n"]

        if data.get("udyam_registration_number"):
            lines.append(f"**Udyam Number:** {data['udyam_registration_number']}")
        if data.get("enterprise_name"):
            lines.append(f"**Enterprise Name:** {data['enterprise_name']}")
        if data.get("enterprise_type"):
            lines.append(f"**Category:** {data['enterprise_type']}")
        if data.get("owner_name"):
            lines.append(f"**Owner:** {data['owner_name']}")
        if data.get("date_of_registration"):
            lines.append(f"**Registration Date:** {data['date_of_registration']}")
        if data.get("major_activity"):
            lines.append(f"**Activity:** {data['major_activity']}")
        if data.get("state"):
            lines.append(f"**State:** {data['state']}")
        if data.get("district"):
            lines.append(f"**District:** {data['district']}")

        lines.append("\n✅ *Please verify these details are correct.*")
        return "\n".join(lines)

    def _format_delivery_proof(self, data: Dict[str, Any]) -> str:
        """Format delivery receipt extraction."""
        lines = ["📄 **Delivery Proof Extracted**\n"]

        if data.get("delivery_date"):
            lines.append(f"**Delivery Date:** {data['delivery_date']}")
        if data.get("delivery_challan_number"):
            lines.append(f"**Challan Number:** {data['delivery_challan_number']}")
        if data.get("sender_name"):
            lines.append(f"**Sender:** {data['sender_name']}")
        if data.get("recipient_company"):
            lines.append(f"**Recipient:** {data['recipient_company']}")
        if data.get("receiver_name"):
            lines.append(f"**Received By:** {data['receiver_name']}")
        if data.get("receiver_signature"):
            lines.append(f"**Signature Present:** {'Yes' if data['receiver_signature'] else 'No'}")
        if data.get("vehicle_number"):
            lines.append(f"**Vehicle:** {data['vehicle_number']}")

        items = data.get("items_delivered", [])
        if items:
            lines.append("\n**Items Delivered:**")
            for item in items[:5]:
                lines.append(f"  • {item}")

        lines.append("\n✅ *Please verify these details are correct.*")
        return "\n".join(lines)

    def _format_communication(self, data: Dict[str, Any]) -> str:
        """Format email/communication extraction."""
        lines = ["📄 **Communication Record Extracted**\n"]

        if data.get("date"):
            lines.append(f"**Date:** {data['date']}")
        if data.get("from"):
            lines.append(f"**From:** {data['from']}")
        if data.get("to"):
            lines.append(f"**To:** {data['to']}")
        if data.get("subject"):
            lines.append(f"**Subject:** {data['subject']}")
        if data.get("amount_mentioned"):
            lines.append(f"**Amount Mentioned:** ₹{data['amount_mentioned']}")
        if data.get("deadline_mentioned"):
            lines.append(f"**Deadline:** {data['deadline_mentioned']}")
        if data.get("tone"):
            lines.append(f"**Tone:** {data['tone']}")

        key_points = data.get("key_points", [])
        if key_points:
            lines.append("\n**Key Points:**")
            for point in key_points[:5]:
                lines.append(f"  • {point}")

        lines.append("\n✅ *Please verify these details are correct.*")
        return "\n".join(lines)

    def _format_bank_statement(self, data: Dict[str, Any]) -> str:
        """Format bank statement extraction."""
        lines = ["📄 **Bank Statement Extracted**\n"]

        if data.get("bank_name"):
            lines.append(f"**Bank:** {data['bank_name']}")
        if data.get("account_holder_name"):
            lines.append(f"**Account Holder:** {data['account_holder_name']}")
        if data.get("account_number"):
            lines.append(f"**Account Number:** {data['account_number']}")
        if data.get("statement_period"):
            lines.append(f"**Period:** {data['statement_period']}")
        if data.get("opening_balance"):
            lines.append(f"**Opening Balance:** ₹{data['opening_balance']}")
        if data.get("closing_balance"):
            lines.append(f"**Closing Balance:** ₹{data['closing_balance']}")

        lines.append("\n✅ *Please verify these details are correct.*")
        return "\n".join(lines)

    def _format_legal_notice(self, data: Dict[str, Any]) -> str:
        """Format legal notice extraction."""
        lines = ["📄 **Legal Notice Extracted**\n"]

        if data.get("notice_date"):
            lines.append(f"**Notice Date:** {data['notice_date']}")
        if data.get("from_party"):
            lines.append(f"**From:** {data['from_party']}")
        if data.get("to_party"):
            lines.append(f"**To:** {data['to_party']}")
        if data.get("lawyer_name"):
            lines.append(f"**Advocate:** {data['lawyer_name']}")
        if data.get("amount_claimed"):
            lines.append(f"**Amount Claimed:** ₹{data['amount_claimed']}")
        if data.get("deadline_given"):
            lines.append(f"**Response Deadline:** {data['deadline_given']}")
        if data.get("subject_matter"):
            lines.append(f"**Subject:** {data['subject_matter']}")

        sections = data.get("legal_sections_cited", [])
        if sections:
            lines.append(f"**Sections Cited:** {', '.join(sections) if isinstance(sections, list) else sections}")

        lines.append("\n✅ *Please verify these details are correct.*")
        return "\n".join(lines)

    def _format_generic(self, data: Dict[str, Any]) -> str:
        """Format generic document extraction."""
        lines = ["📄 **Document Extracted**\n"]

        if data.get("document_type"):
            lines.append(f"**Type:** {data['document_type']}")
        if data.get("date"):
            lines.append(f"**Date:** {data['date']}")
        if data.get("parties"):
            parties = data['parties']
            if isinstance(parties, list):
                lines.append(f"**Parties:** {', '.join(parties)}")
            else:
                lines.append(f"**Parties:** {parties}")
        if data.get("amounts"):
            lines.append(f"**Amounts:** {data['amounts']}")
        if data.get("reference_numbers"):
            lines.append(f"**References:** {data['reference_numbers']}")
        if data.get("key_details"):
            lines.append(f"**Details:** {data['key_details']}")

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
