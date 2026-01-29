"""
Demo script for Document OCR functionality
Shows how to use the DocumentProcessor to extract invoice data
"""

from datetime import datetime
from src.intake.document_processor import DocumentProcessor
from src.models.dispute import Document


def demo_entity_extraction():
    """Demonstrate entity extraction from sample invoice text"""
    print("=" * 80)
    print("MSME Document Processor - Demo")
    print("=" * 80)
    print()

    # Initialize processor
    print("Initializing DocumentProcessor...")
    processor = DocumentProcessor(languages=['en', 'hi'])
    print(f"✓ Processor initialized with languages: {processor.languages}")
    print()

    # Sample invoice text (simulating OCR output)
    sample_invoice_text = """
    TAX INVOICE

    Invoice No: INV-2024-001
    Invoice Date: 15/01/2024

    From:
    ABC Manufacturing Pvt Ltd
    Seller GSTIN: 29ABCDE1234F1Z8

    Bill To:
    XYZ Industries Limited
    Buyer GSTIN: 22AAAAA0000A1Z5

    Description: Manufacturing Equipment

    Total Amount: ₹10,50,000.00
    """

    print("Sample Invoice Text:")
    print("-" * 80)
    print(sample_invoice_text)
    print("-" * 80)
    print()

    # Extract entities
    print("Extracting entities...")
    entities = processor.extract_entities(sample_invoice_text, 'invoice')
    print()

    # Display extracted entities
    print("Extracted Entities:")
    print("-" * 80)
    for key, value in entities.items():
        if value is not None:
            if isinstance(value, datetime):
                print(f"  {key:20}: {value.strftime('%d/%m/%Y')}")
            elif isinstance(value, float):
                print(f"  {key:20}: ₹{value:,.2f}")
            else:
                print(f"  {key:20}: {value}")
        else:
            print(f"  {key:20}: [NOT FOUND]")
    print("-" * 80)
    print()

    # Validate entities
    print("Validating extracted entities...")
    validation_errors = processor._validate_entities(entities)

    if len(validation_errors) == 0:
        print("✓ All validations passed! Document is ready for submission.")
    else:
        print(f"✗ Found {len(validation_errors)} validation error(s):")
        for error in validation_errors:
            print(f"  - {error}")
    print()


def demo_gstin_validation():
    """Demonstrate GSTIN validation"""
    print("=" * 80)
    print("GSTIN Validation Demo")
    print("=" * 80)
    print()

    processor = DocumentProcessor()

    test_gstins = [
        ("29ABCDE1234F1Z8", "Valid GSTIN"),
        ("22AAAAA0000A1Z5", "Valid GSTIN"),
        ("INVALID_GSTIN", "Invalid format"),
        ("22AAAAA0000A1Z", "Too short"),
        ("22aaaaa0000A1Z5", "Lowercase letters"),
    ]

    for gstin, description in test_gstins:
        is_valid = processor.validate_gstin(gstin)
        status = "✓ VALID" if is_valid else "✗ INVALID"
        print(f"{status:12} | {gstin:20} | {description}")
    print()


def demo_amount_parsing():
    """Demonstrate Indian currency amount parsing"""
    print("=" * 80)
    print("Indian Currency Amount Parsing Demo")
    print("=" * 80)
    print()

    processor = DocumentProcessor()

    test_amounts = [
        "₹10,00,000",           # 10 lakhs
        "Rs. 1,50,000.50",      # 1.5 lakhs with decimals
        "50,000",               # 50 thousand
        "1,00,00,000",          # 1 crore
        "Total: ₹2,50,000",     # With label
    ]

    print("Amount String               →  Parsed Value")
    print("-" * 80)
    for amount_str in test_amounts:
        parsed = processor.validate_amount(amount_str)
        if parsed:
            print(f"{amount_str:25} →  ₹{parsed:,.2f}")
        else:
            print(f"{amount_str:25} →  [FAILED TO PARSE]")
    print()


def demo_date_parsing():
    """Demonstrate Indian date format parsing"""
    print("=" * 80)
    print("Indian Date Format Parsing Demo")
    print("=" * 80)
    print()

    processor = DocumentProcessor()

    test_dates = [
        "15/01/2024",
        "31-12-2023",
        "01.06.2024",
        "25/12/23",
    ]

    print("Date String     →  Parsed Date")
    print("-" * 80)
    for date_str in test_dates:
        parsed = processor.validate_date(date_str)
        if parsed:
            print(f"{date_str:15} →  {parsed.strftime('%d %B %Y')}")
        else:
            print(f"{date_str:15} →  [FAILED TO PARSE]")
    print()


if __name__ == "__main__":
    print()
    print("=" * 80)
    print(" " * 15 + "MSME VIRTUAL NEGOTIATION ASSISTANT")
    print(" " * 20 + "Document OCR & Extraction Demo")
    print("=" * 80)
    print()

    try:
        demo_entity_extraction()
        demo_gstin_validation()
        demo_amount_parsing()
        demo_date_parsing()

        print("=" * 80)
        print("Demo completed successfully!")
        print("=" * 80)
        print()
        print("Next Steps:")
        print("  1. Install dependencies: venv\\Scripts\\pip install -r requirements.txt")
        print("  2. Run tests: venv\\Scripts\\python -m pytest tests/test_document_processor.py -v")
        print("  3. Process real invoice images using DocumentProcessor.process_document()")
        print()

    except Exception as e:
        print(f"Error running demo: {e}")
        print()
        print("If you see import errors, make sure to install dependencies:")
        print("  venv\\Scripts\\pip install -r requirements.txt")
        print()
