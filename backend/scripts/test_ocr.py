#!/usr/bin/env python3
"""
Quick test script to verify OCR service is working.
Run from backend directory: python -m scripts.test_ocr

Usage:
    python -m scripts.test_ocr                    # Basic test
    python -m scripts.test_ocr path/to/image.jpg  # Test with specific image
"""

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services.ocr_service import get_ocr_service, get_ocr_system


def test_ocr_availability():
    """Test if OCR system is available."""
    print("=== OCR System Availability Test ===\n")

    ocr = get_ocr_system()

    if ocr == "fallback":
        print("❌ IndicPhotoOCR NOT available")
        print("   Install with: pip install indicphotoocr")
        return False
    else:
        print("✅ IndicPhotoOCR is available!")
        return True


def test_ocr_service():
    """Test the OCR service."""
    print("\n=== OCR Service Test ===\n")

    service = get_ocr_service()
    print(f"OCR Service initialized: {service is not None}")
    print(f"Groq client available: {service.groq_client is not None}")

    return service


def test_with_image(image_path: str):
    """Test OCR with a specific image."""
    print(f"\n=== Testing OCR with: {image_path} ===\n")

    if not Path(image_path).exists():
        print(f"❌ File not found: {image_path}")
        return

    service = get_ocr_service()

    # Test raw text extraction
    print("1. Extracting raw text...")
    raw_text = service.extract_text_from_image(image_path)
    print(f"   Extracted {len(raw_text)} characters")
    print(f"   Preview: {raw_text[:200]}..." if len(raw_text) > 200 else f"   Text: {raw_text}")

    # Test full document processing
    print("\n2. Full document processing (OCR + LLM extraction)...")
    result = service.process_document(
        file_path=image_path,
        file_type="image/jpeg",
        document_type="invoice"
    )

    print(f"   Extraction status: {result.get('extraction_status', 'unknown')}")

    # Show extracted fields
    for key, value in result.items():
        if key not in ['raw_text', 'llm_response'] and value:
            print(f"   {key}: {value}")

    # Test chat formatting
    print("\n3. Chat-formatted output:")
    formatted = service.format_for_chat(result)
    print(formatted)


def create_test_image():
    """Create a simple test image with text (requires PIL)."""
    try:
        from PIL import Image, ImageDraw, ImageFont

        # Create a simple invoice-like image
        img = Image.new('RGB', (400, 300), color='white')
        draw = ImageDraw.Draw(img)

        # Add text
        text_lines = [
            "INVOICE",
            "Invoice No: INV-2024-001",
            "Date: 15-01-2024",
            "",
            "From: ABC Traders",
            "GSTIN: 29ABCDE1234F1Z5",
            "",
            "To: XYZ Enterprises",
            "",
            "Amount: Rs. 50,000",
            "GST (18%): Rs. 9,000",
            "Total: Rs. 59,000",
        ]

        y = 20
        for line in text_lines:
            draw.text((20, y), line, fill='black')
            y += 22

        # Save
        test_path = Path(__file__).parent.parent / "data" / "test_invoice.png"
        test_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(test_path)
        print(f"✅ Created test image: {test_path}")
        return str(test_path)

    except ImportError:
        print("PIL not available for creating test image")
        return None


def main():
    print("=" * 60)
    print("        IndicPhotoOCR (Bhashini) Test Script")
    print("=" * 60)

    # Test 1: Check availability
    available = test_ocr_availability()

    # Test 2: Initialize service
    service = test_ocr_service()

    # Test 3: Test with image
    if len(sys.argv) > 1:
        # Use provided image path
        test_with_image(sys.argv[1])
    elif available:
        # Try to create and test with a sample image
        print("\n=== Creating Test Image ===")
        test_path = create_test_image()
        if test_path:
            test_with_image(test_path)
        else:
            print("\nTo test with an image, run:")
            print("  python -m scripts.test_ocr path/to/invoice.jpg")

    print("\n" + "=" * 60)
    print("Test complete!")


if __name__ == "__main__":
    main()
