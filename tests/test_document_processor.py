"""
Tests for Document OCR and Entity Extraction
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import numpy as np

from src.intake.document_processor import DocumentProcessor
from src.models.dispute import Document


class TestDocumentProcessor:
    """Test cases for DocumentProcessor"""

    @pytest.fixture
    def processor(self):
        """Create a DocumentProcessor instance for testing"""
        # Mock the EasyOCR reader to avoid downloading models during tests
        with patch('src.intake.document_processor.easyocr.Reader') as mock_reader:
            mock_reader.return_value = Mock()
            proc = DocumentProcessor(languages=['en', 'hi'])
            return proc

    def test_initialization(self, processor):
        """Test processor initializes correctly"""
        assert processor is not None
        assert processor.languages == ['en', 'hi']
        assert processor.reader is not None

    def test_validate_gstin_valid(self, processor):
        """Test GSTIN validation with valid formats"""
        # Valid GSTIN format: 22AAAAA0000A1Z5
        valid_gstins = [
            '22AAAAA0000A1Z5',
            '29ABCDE1234F1Z8',
            '09XYZAB5678G2ZA',
        ]

        for gstin in valid_gstins:
            assert processor.validate_gstin(gstin), f"Valid GSTIN failed: {gstin}"

    def test_validate_gstin_invalid(self, processor):
        """Test GSTIN validation with invalid formats"""
        invalid_gstins = [
            '',                      # Empty
            '22AAAAA0000A1Z',       # Too short
            '22AAAAA0000A1Z5X',     # Too long
            '22aaaaa0000A1Z5',      # Lowercase
            '22AAAAA0000A1X5',      # Invalid 14th char (should be Z)
            'INVALID_GSTIN',        # Completely wrong format
        ]

        for gstin in invalid_gstins:
            assert not processor.validate_gstin(gstin), f"Invalid GSTIN passed: {gstin}"

    def test_validate_amount_indian_format(self, processor):
        """Test amount parsing with Indian number formats"""
        test_cases = [
            ('10,00,000', 1000000.0),       # 10 lakhs
            ('1,00,000.50', 100000.50),     # 1 lakh with decimals
            ('50,000', 50000.0),            # 50 thousand
            ('123.45', 123.45),             # Simple decimal
            ('₹10,000', 10000.0),           # With rupee symbol
            ('Rs. 5,000', 5000.0),          # With Rs.
        ]

        for amount_str, expected in test_cases:
            result = processor.validate_amount(amount_str)
            assert result == expected, f"Amount parsing failed for {amount_str}"

    def test_validate_amount_invalid(self, processor):
        """Test amount parsing with invalid inputs"""
        invalid_amounts = [
            '',
            'invalid',
            'Rs.',
            '₹',
            '-1000',  # This will parse but return None due to negative check
        ]

        for amount_str in invalid_amounts:
            result = processor.validate_amount(amount_str)
            # Empty or invalid strings should return None
            assert result is None or result <= 0, f"Invalid amount should fail: {amount_str}"

    def test_validate_date_indian_formats(self, processor):
        """Test date parsing with Indian date formats"""
        test_cases = [
            ('15/01/2024', datetime(2024, 1, 15)),
            ('31-12-2023', datetime(2023, 12, 31)),
            ('01.06.2024', datetime(2024, 6, 1)),
        ]

        for date_str, expected in test_cases:
            result = processor.validate_date(date_str)
            assert result is not None, f"Date parsing failed for {date_str}"
            assert result.date() == expected.date()

    def test_validate_date_invalid(self, processor):
        """Test date parsing with invalid dates"""
        invalid_dates = [
            '',
            'invalid',
            '32/13/2024',  # Invalid day/month
            '2024-01-15',  # Wrong format
        ]

        for date_str in invalid_dates:
            result = processor.validate_date(date_str)
            assert result is None, f"Invalid date should fail: {date_str}"

    def test_extract_invoice_number(self, processor):
        """Test invoice number extraction"""
        test_texts = [
            ("Invoice No: INV-2024-001", "INV-2024-001"),
            ("Bill Number: BILL/123/2024", "BILL/123/2024"),
            ("Inv #: ABC123", "ABC123"),
        ]

        for text, expected in test_texts:
            result = processor._extract_invoice_number(text)
            assert result == expected, f"Failed to extract from: {text}"

    def test_extract_date(self, processor):
        """Test date extraction from text"""
        text = "Invoice Date: 15/01/2024"
        result = processor._extract_date(text)

        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_extract_amount(self, processor):
        """Test amount extraction from text"""
        test_texts = [
            ("Total: ₹10,00,000", 1000000.0),
            ("Amount: Rs. 50,000", 50000.0),
            ("TOTAL AMOUNT: 1,23,456.78", 123456.78),
        ]

        for text, expected in test_texts:
            result = processor._extract_amount(text)
            assert result == expected, f"Failed to extract amount from: {text}"

    def test_extract_gstin(self, processor):
        """Test GSTIN extraction from text"""
        text = """
        INVOICE
        From: ABC Company
        Seller GSTIN: 29ABCDE1234F1Z8

        Bill To: XYZ Corporation
        Buyer GSTIN: 22AAAAA0000A1Z5
        """

        buyer_gstin = processor._extract_gstin(text, 'buyer')
        seller_gstin = processor._extract_gstin(text, 'seller')

        assert buyer_gstin == '22AAAAA0000A1Z5'
        assert seller_gstin == '29ABCDE1234F1Z8'

    def test_extract_entities_complete_invoice(self, processor):
        """Test entity extraction from a complete invoice text"""
        invoice_text = """
        TAX INVOICE
        Invoice No: INV-2024-001
        Date: 15/01/2024

        From: ABC Suppliers Pvt Ltd
        GSTIN: 29ABCDE1234F1Z8

        To: XYZ Industries
        GSTIN: 22AAAAA0000A1Z5

        Total Amount: ₹1,50,000.00
        """

        entities = processor.extract_entities(invoice_text, 'invoice')

        assert entities['invoice_number'] == 'INV-2024-001'
        assert entities['invoice_date'] is not None
        assert entities['total_amount'] == 150000.0
        assert entities['seller_gstin'] == '29ABCDE1234F1Z8'
        assert entities['buyer_gstin'] == '22AAAAA0000A1Z5'

    def test_validate_entities_success(self, processor):
        """Test entity validation with valid data"""
        entities = {
            'invoice_number': 'INV-2024-001',
            'invoice_date': datetime.now() - timedelta(days=30),
            'total_amount': 100000.0,
            'buyer_gstin': '22AAAAA0000A1Z5',
            'seller_gstin': '29ABCDE1234F1Z8',
        }

        errors = processor._validate_entities(entities)
        assert len(errors) == 0, f"Valid entities should not have errors: {errors}"

    def test_validate_entities_missing_fields(self, processor):
        """Test entity validation with missing required fields"""
        entities = {
            # Missing invoice_number, invoice_date, total_amount
            'buyer_gstin': '22AAAAA0000A1Z5',
        }

        errors = processor._validate_entities(entities)
        assert len(errors) >= 3  # Should have errors for missing fields
        assert any('invoice number' in err.lower() for err in errors)
        assert any('invoice date' in err.lower() for err in errors)
        assert any('amount' in err.lower() for err in errors)

    def test_validate_entities_invalid_gstin(self, processor):
        """Test entity validation with invalid GSTIN"""
        entities = {
            'invoice_number': 'INV-2024-001',
            'invoice_date': datetime.now(),
            'total_amount': 100000.0,
            'buyer_gstin': 'INVALID_GSTIN',
            'seller_gstin': '29ABCDE1234F1Z8',
        }

        errors = processor._validate_entities(entities)
        assert any('buyer GSTIN' in err for err in errors)

    def test_validate_entities_future_date(self, processor):
        """Test entity validation rejects future dates"""
        entities = {
            'invoice_number': 'INV-2024-001',
            'invoice_date': datetime.now() + timedelta(days=10),  # Future date
            'total_amount': 100000.0,
        }

        errors = processor._validate_entities(entities)
        assert any('future' in err.lower() for err in errors)

    def test_validate_entities_old_invoice(self, processor):
        """Test entity validation warns about old invoices"""
        entities = {
            'invoice_number': 'INV-2020-001',
            'invoice_date': datetime.now() - timedelta(days=1200),  # > 3 years
            'total_amount': 100000.0,
        }

        errors = processor._validate_entities(entities)
        assert any('3 years' in err for err in errors)

    def test_validate_entities_high_amount(self, processor):
        """Test entity validation warns about unusually high amounts"""
        entities = {
            'invoice_number': 'INV-2024-001',
            'invoice_date': datetime.now(),
            'total_amount': 150000000.0,  # 15 crores (above threshold)
        }

        errors = processor._validate_entities(entities)
        assert any('unusually high' in err.lower() for err in errors)

    def test_extract_text_mock(self, processor):
        """Test OCR text extraction with mocked reader"""
        # Create a mock image
        mock_image = np.zeros((100, 100), dtype=np.uint8)

        # Mock OCR results
        processor.reader.readtext = Mock(return_value=[
            ([(0, 0), (50, 0), (50, 20), (0, 20)], "INVOICE", 0.95),
            ([(0, 25), (100, 25), (100, 45), (0, 45)], "Invoice No: INV-001", 0.92),
            ([(0, 50), (80, 50), (80, 70), (0, 70)], "Total: ₹10,000", 0.88),
        ])

        text, confidence = processor.extract_text(mock_image)

        assert "INVOICE" in text
        assert "Invoice No: INV-001" in text
        assert "Total: ₹10,000" in text
        assert 0.85 < confidence < 1.0  # Average of confidences

    @patch('src.intake.document_processor.cv2.imread')
    @patch('src.intake.document_processor.cv2.cvtColor')
    @patch('src.intake.document_processor.cv2.adaptiveThreshold')
    def test_load_image_success(self, mock_threshold, mock_cvtcolor, mock_imread, processor):
        """Test successful image loading and preprocessing"""
        # Mock successful image loading
        mock_image = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_imread.return_value = mock_image
        mock_cvtcolor.return_value = np.zeros((100, 100), dtype=np.uint8)
        mock_threshold.return_value = np.zeros((100, 100), dtype=np.uint8)

        # Create a temporary file path (doesn't need to exist due to mocking)
        with patch('pathlib.Path.exists', return_value=True):
            result = processor._load_image('test_invoice.jpg')

        assert result is not None
        mock_imread.assert_called_once()
        mock_cvtcolor.assert_called_once()
        mock_threshold.assert_called_once()

    def test_load_image_not_found(self, processor):
        """Test error handling for missing file"""
        with pytest.raises(FileNotFoundError):
            processor._load_image('nonexistent_file.jpg')

    def test_load_image_unsupported_format(self, processor):
        """Test error handling for unsupported file format"""
        with patch('pathlib.Path.exists', return_value=True):
            with pytest.raises(ValueError, match="Unsupported file format"):
                processor._load_image('document.txt')

    def test_load_image_pdf_format(self, processor):
        """Test error message for PDF files"""
        with patch('pathlib.Path.exists', return_value=True):
            with pytest.raises(ValueError, match="PDF support"):
                processor._load_image('invoice.pdf')

    @patch('src.intake.document_processor.cv2.imread')
    def test_process_document_integration(self, mock_imread, processor):
        """Test complete document processing flow"""
        # Mock image loading
        mock_image = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_imread.return_value = mock_image

        # Mock OCR extraction
        invoice_text = """
        TAX INVOICE
        Invoice No: INV-2024-001
        Date: 15/01/2024
        From: ABC Suppliers
        GSTIN: 29ABCDE1234F1Z8
        To: XYZ Industries
        GSTIN: 22AAAAA0000A1Z5
        Total Amount: ₹1,50,000.00
        """

        processor.reader.readtext = Mock(return_value=[
            ([], line, 0.90) for line in invoice_text.split('\n')
        ])

        with patch('pathlib.Path.exists', return_value=True):
            with patch('src.intake.document_processor.cv2.cvtColor'):
                with patch('src.intake.document_processor.cv2.adaptiveThreshold'):
                    document = processor.process_document(
                        file_path='test_invoice.jpg',
                        document_type='invoice'
                    )

        assert document is not None
        assert document.name == 'invoice'
        assert document.is_mandatory is True
        assert document.ocr_text is not None
        assert len(document.extracted_entities) > 0
        assert document.extracted_entities.get('invoice_number') == 'INV-2024-001'
        assert document.extracted_entities.get('total_amount') == 150000.0

    @patch('src.intake.document_processor.cv2.imread')
    def test_process_document_with_errors(self, mock_imread, processor):
        """Test document processing handles errors gracefully"""
        # Mock image loading
        mock_image = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_imread.return_value = mock_image

        # Mock OCR with incomplete data
        incomplete_text = """
        Some random text
        No structured invoice data
        """

        processor.reader.readtext = Mock(return_value=[
            ([], line, 0.70) for line in incomplete_text.split('\n')
        ])

        with patch('pathlib.Path.exists', return_value=True):
            with patch('src.intake.document_processor.cv2.cvtColor'):
                with patch('src.intake.document_processor.cv2.adaptiveThreshold'):
                    document = processor.process_document(
                        file_path='bad_invoice.jpg',
                        document_type='invoice'
                    )

        assert document is not None
        assert document.is_verified is False  # Should fail validation
        assert len(document.validation_errors) > 0  # Should have errors


class TestDocumentProcessorEdgeCases:
    """Test edge cases and error handling"""

    @pytest.fixture
    def processor(self):
        """Create a DocumentProcessor instance for testing"""
        with patch('src.intake.document_processor.easyocr.Reader') as mock_reader:
            mock_reader.return_value = Mock()
            proc = DocumentProcessor()
            return proc

    def test_extract_entities_empty_text(self, processor):
        """Test entity extraction with empty text"""
        entities = processor.extract_entities("", 'invoice')
        assert isinstance(entities, dict)
        assert entities['invoice_number'] is None
        assert entities['total_amount'] is None

    def test_extract_invoice_number_multiple_patterns(self, processor):
        """Test invoice number extraction with various formats"""
        test_cases = [
            "Invoice #: ABC/2024/001",
            "Bill No: BILL-123-2024",
            "Inv No: 12345",
            "INVOICE NUMBER: INV2024001",
        ]

        for text in test_cases:
            result = processor._extract_invoice_number(text)
            assert result is not None, f"Failed to extract from: {text}"

    def test_gstin_extraction_single_gstin(self, processor):
        """Test GSTIN extraction when only one is present"""
        text = "Company GSTIN: 29ABCDE1234F1Z8"

        buyer_gstin = processor._extract_gstin(text, 'buyer')
        seller_gstin = processor._extract_gstin(text, 'seller')

        # Should return the same GSTIN for both
        assert buyer_gstin == '29ABCDE1234F1Z8'
        assert seller_gstin == '29ABCDE1234F1Z8'

    def test_confidence_scoring(self, processor):
        """Test OCR confidence scoring calculation"""
        mock_image = np.zeros((100, 100), dtype=np.uint8)

        # Mock varying confidence levels
        processor.reader.readtext = Mock(return_value=[
            ([], "Line 1", 0.95),
            ([], "Line 2", 0.85),
            ([], "Line 3", 0.90),
        ])

        text, confidence = processor.extract_text(mock_image)

        # Average confidence should be (0.95 + 0.85 + 0.90) / 3 = 0.90
        assert abs(confidence - 0.90) < 0.01
