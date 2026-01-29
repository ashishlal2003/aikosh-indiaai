"""
Integration example: Using DocumentProcessor with Dispute workflow
Shows end-to-end flow from document upload to dispute validation
"""

from datetime import datetime
from src.intake.document_processor import DocumentProcessor
from src.models.dispute import Dispute, DisputeType, Party, Document
from src.governance.policy_engine import PolicyEngine


def example_dispute_with_ocr():
    """
    Example: Complete dispute flow with OCR document processing
    This demonstrates how an MSME would submit a dispute with invoice scanning
    """
    print("=" * 80)
    print("INTEGRATION EXAMPLE: Dispute Submission with OCR")
    print("=" * 80)
    print()

    # Step 1: Initialize components
    print("Step 1: Initialize components")
    processor = DocumentProcessor(languages=['en', 'hi'])
    policy_engine = PolicyEngine()
    print("✓ Components initialized")
    print()

    # Step 2: Simulate invoice OCR (in production, this would be from uploaded image)
    print("Step 2: Process uploaded invoice document")
    sample_invoice_text = """
    TAX INVOICE

    Invoice No: INV-2024-001
    Invoice Date: 15/01/2024

    From:
    ABC Manufacturing Pvt Ltd
    Seller GSTIN: 29ABCDE1234F1Z8
    Address: 123 Industrial Area, Bangalore

    Bill To:
    Government Department XYZ
    Buyer GSTIN: 22AAAAA0000A1Z5
    Address: Secretariat, New Delhi

    Description: Industrial Equipment Supply

    Total Amount: ₹8,50,000.00
    Payment Terms: 45 days from invoice date
    """

    # Extract entities from invoice
    entities = processor.extract_entities(sample_invoice_text, 'invoice')
    print("✓ Invoice entities extracted")
    print(f"  - Invoice Number: {entities.get('invoice_number')}")
    print(f"  - Invoice Date: {entities.get('invoice_date')}")
    print(f"  - Amount: ₹{entities.get('total_amount'):,.2f}" if entities.get('total_amount') else "  - Amount: Not found")
    print(f"  - Buyer GSTIN: {entities.get('buyer_gstin')}")
    print(f"  - Seller GSTIN: {entities.get('seller_gstin')}")
    print()

    # Step 3: Create Document model
    print("Step 3: Create Document model from OCR results")
    invoice_doc = Document(
        name="invoice",
        file_path="uploads/invoice_001.jpg",  # In production, this would be actual path
        is_mandatory=True,
        ocr_text=sample_invoice_text,
        extracted_entities=entities,
        is_verified=True
    )
    print("✓ Document model created")
    print()

    # Step 4: Create party information from extracted data
    print("Step 4: Create party information")
    msme_party = Party(
        name=entities.get('seller_name', 'ABC Manufacturing Pvt Ltd'),
        gstin=entities.get('seller_gstin'),
        is_msme=True,
        contact_email="contact@abcmfg.com",
        contact_phone="+91-9876543210"
    )

    buyer_party = Party(
        name=entities.get('buyer_name', 'Government Department XYZ'),
        gstin=entities.get('buyer_gstin'),
        is_msme=False,
        contact_email="dept@gov.in"
    )
    print("✓ Parties created")
    print(f"  - MSME: {msme_party.name}")
    print(f"  - Buyer: {buyer_party.name}")
    print()

    # Step 5: Create Dispute with extracted information
    print("Step 5: Create Dispute with extracted data")
    dispute = Dispute(
        dispute_type=DisputeType.PAYMENT_DELAY,
        msme_party=msme_party,
        buyer_party=buyer_party,
        dispute_amount=entities.get('total_amount'),
        invoice_amount=entities.get('total_amount'),
        invoice_number=entities.get('invoice_number'),
        invoice_date=entities.get('invoice_date'),
        payment_due_date=datetime(2024, 3, 1),  # 45 days from invoice
        days_delayed=45,  # Assuming current date is April 15, 2024
        documents=[invoice_doc],
        description="Payment not received despite completion of delivery and 45 days past due date.",
        language="en"
    )
    print("✓ Dispute created")
    print()

    # Step 6: Check eligibility using PolicyEngine
    print("Step 6: Check eligibility using PolicyEngine")
    is_eligible, eligibility_errors = policy_engine.check_eligibility(
        dispute_amount=dispute.dispute_amount,
        invoice_date=dispute.invoice_date,
        has_msme_registration=True,
        registration_type="Udyam Registration"
    )

    dispute.is_eligible = is_eligible
    dispute.eligibility_errors = eligibility_errors

    if is_eligible:
        print("✓ Dispute is eligible under MSMED Act")
    else:
        print("✗ Dispute is NOT eligible:")
        for error in eligibility_errors:
            print(f"  - {error}")
    print()

    # Step 7: Check if dispute can be submitted
    print("Step 7: Validate dispute for submission")
    can_submit, blocking_errors = dispute.can_submit()

    if can_submit:
        print("✓ Dispute is ready for submission!")
        print()

        # Calculate interest (additional feature)
        if dispute.payment_due_date and dispute.dispute_amount:
            interest = policy_engine.calculate_interest(
                principal=dispute.dispute_amount,
                start_date=dispute.payment_due_date,
                end_date=datetime.now()
            )
            print(f"Additional Information:")
            print(f"  - Interest accrued (MSMED Act): ₹{interest:,.2f}")
            print(f"  - Total claim amount: ₹{dispute.dispute_amount + interest:,.2f}")
    else:
        print("✗ Dispute cannot be submitted. Blocking errors:")
        for error in blocking_errors:
            print(f"  - {error}")
    print()

    # Step 8: Show dispute summary
    print("=" * 80)
    print("DISPUTE SUMMARY")
    print("=" * 80)
    print(f"Dispute ID: {dispute.dispute_id or '[To be assigned]'}")
    print(f"Type: {dispute.dispute_type}")
    print(f"Status: {dispute.status}")
    print(f"MSME: {dispute.msme_party.name}")
    print(f"Buyer: {dispute.buyer_party.name}")
    print(f"Invoice: {dispute.invoice_number}")
    print(f"Amount: ₹{dispute.dispute_amount:,.2f}")
    print(f"Days Delayed: {dispute.days_delayed}")
    print(f"Documents: {len(dispute.documents)} uploaded")
    print(f"Eligible: {'Yes' if dispute.is_eligible else 'No'}")
    print(f"Can Submit: {'Yes' if can_submit else 'No'}")
    print("=" * 80)
    print()

    return dispute


def example_missing_documents():
    """
    Example: Demonstrate hard blocking when mandatory documents are missing
    """
    print("=" * 80)
    print("EXAMPLE: Hard Blocking with Missing Documents")
    print("=" * 80)
    print()

    print("Creating dispute with missing mandatory documents...")

    dispute = Dispute(
        dispute_type=DisputeType.PAYMENT_DELAY,
        msme_party=Party(
            name="ABC Suppliers",
            gstin="29ABCDE1234F1Z8",
            is_msme=True
        ),
        buyer_party=Party(
            name="XYZ Corp",
            gstin="22AAAAA0000A1Z5",
            is_msme=False
        ),
        dispute_amount=100000.0,
        invoice_number="INV-001",
        invoice_date=datetime(2024, 1, 15),
        documents=[]  # No documents uploaded
    )

    can_submit, blocking_errors = dispute.can_submit()

    print(f"Can submit: {can_submit}")
    print(f"Blocking errors: {len(blocking_errors)}")
    print()

    if not can_submit:
        print("Submission BLOCKED due to:")
        for error in blocking_errors:
            print(f"  ✗ {error}")
    print()

    # Show what documents are needed
    policy_engine = PolicyEngine()
    required_docs = policy_engine.get_mandatory_documents(dispute.dispute_type)
    print(f"Required documents for {dispute.dispute_type}:")
    for doc in required_docs:
        print(f"  - {doc}")
    print()


if __name__ == "__main__":
    print()
    print("=" * 80)
    print(" " * 10 + "MSME VIRTUAL NEGOTIATION ASSISTANT - INTEGRATION DEMO")
    print("=" * 80)
    print()

    try:
        # Example 1: Complete flow with OCR
        dispute = example_dispute_with_ocr()

        # Example 2: Hard blocking demonstration
        example_missing_documents()

        print("=" * 80)
        print("Integration examples completed!")
        print("=" * 80)
        print()
        print("Key Features Demonstrated:")
        print("  ✓ OCR extraction from invoice text")
        print("  ✓ Automatic entity extraction (invoice #, dates, amounts, GSTIN)")
        print("  ✓ Integration with Dispute model")
        print("  ✓ PolicyEngine eligibility checking")
        print("  ✓ Hard blocking for incomplete submissions")
        print("  ✓ Interest calculation per MSMED Act")
        print()

    except Exception as e:
        print(f"Error running integration example: {e}")
        import traceback
        traceback.print_exc()
        print()
        print("Make sure all dependencies are installed:")
        print("  venv\\Scripts\\pip install -r requirements.txt")
        print()
