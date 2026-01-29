"""
Demo script for AI Negotiation Mediator
Demonstrates settlement suggestion capabilities
"""

import sys
import io
from datetime import datetime, timedelta
import uuid

# Set UTF-8 encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.negotiation.mediator import NegotiationMediator
from src.models.dispute import Dispute, DisputeType, DisputeStatus, Party, Document
from src.models.negotiation import Negotiation, Offer, OfferStatus, NegotiationState
from src.governance.policy_engine import PolicyEngine


def print_section(title: str):
    """Print formatted section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_offer(offer: Offer, label: str = "Offer"):
    """Print offer details"""
    print(f"\n{label} Details:")
    print(f"  Amount: ₹{offer.offered_amount:,.2f} ({offer.offered_percentage:.1f}%)")
    print(f"  Status: {offer.status}")
    print(f"  Offered by: {offer.offered_by}")
    print(f"  AI Confidence: {offer.ai_confidence:.2f}")
    print(f"\n  AI Reasoning:")
    print(f"  {offer.ai_reasoning}")


def demo_initial_offer():
    """Demo 1: Generate initial settlement offer"""
    print_section("Demo 1: Initial Settlement Offer")

    # Create dispute
    dispute = Dispute(
        dispute_id=str(uuid.uuid4()),
        dispute_type=DisputeType.PAYMENT_DELAY,
        status=DisputeStatus.NEGOTIATION_IN_PROGRESS,
        msme_party=Party(
            name="Rajesh Textiles Pvt Ltd",
            gstin="29ABCDE1234F1Z5",
            is_msme=True
        ),
        buyer_party=Party(
            name="Metro Fashion Retail",
            gstin="29XYZAB5678G1Z5",
            is_msme=False
        ),
        dispute_amount=250000.0,
        invoice_amount=250000.0,
        invoice_number="INV-2024-0892",
        invoice_date=datetime.now() - timedelta(days=150),
        payment_due_date=datetime.now() - timedelta(days=120),
        days_delayed=120,
        is_eligible=True,
        description="Payment for 5000 units of cotton fabric delayed by 120 days"
    )

    print("\nDispute Details:")
    print(f"  Type: {dispute.dispute_type}")
    print(f"  Amount: ₹{dispute.dispute_amount:,.2f}")
    print(f"  Days Delayed: {dispute.days_delayed}")
    print(f"  MSME: {dispute.msme_party.name}")
    print(f"  Buyer: {dispute.buyer_party.name}")

    # Create negotiation
    policy_engine = PolicyEngine()
    min_settlement, max_settlement = policy_engine.get_settlement_range(dispute.dispute_amount)

    negotiation = Negotiation(
        negotiation_id=str(uuid.uuid4()),
        dispute_id=dispute.dispute_id,
        state=NegotiationState.NOT_STARTED,
        min_settlement_amount=min_settlement,
        max_settlement_amount=max_settlement
    )

    print(f"\nSettlement Bounds (PolicyEngine):")
    print(f"  Minimum: ₹{min_settlement:,.2f} (50%)")
    print(f"  Maximum: ₹{max_settlement:,.2f} (100%)")

    # Generate initial offer
    mediator = NegotiationMediator(policy_engine=policy_engine)
    offer = mediator.suggest_initial_offer(dispute, negotiation)

    print_offer(offer, "Initial Settlement Offer")

    # Calculate interest
    interest = policy_engine.calculate_interest(
        principal=dispute.dispute_amount,
        start_date=dispute.payment_due_date,
        end_date=datetime.now()
    )
    print(f"\n  MSMED Act Interest (18% annual): ₹{interest:,.2f}")
    print(f"  Total Claim (Principal + Interest): ₹{dispute.dispute_amount + interest:,.2f}")


def demo_negotiation_rounds():
    """Demo 2: Multi-round negotiation with counteroffers"""
    print_section("Demo 2: Multi-Round Negotiation")

    # Setup dispute and negotiation
    dispute = Dispute(
        dispute_id=str(uuid.uuid4()),
        dispute_type=DisputeType.PARTIAL_PAYMENT,
        dispute_amount=500000.0,
        payment_due_date=datetime.now() - timedelta(days=90),
        days_delayed=90,
        is_eligible=True
    )

    policy_engine = PolicyEngine()
    min_settlement, max_settlement = policy_engine.get_settlement_range(dispute.dispute_amount)

    negotiation = Negotiation(
        negotiation_id=str(uuid.uuid4()),
        dispute_id=dispute.dispute_id,
        state=NegotiationState.INITIAL_OFFER_PENDING,
        min_settlement_amount=min_settlement,
        max_settlement_amount=max_settlement
    )

    mediator = NegotiationMediator(policy_engine=policy_engine)

    print("\nScenario: MSME seeks ₹500,000 for partial payment dispute")
    print("=" * 70)

    # Round 1: MSME initial offer
    print("\n[Round 1] MSME makes initial offer")
    offer1 = mediator.suggest_initial_offer(dispute, negotiation)
    print(f"  MSME offers: ₹{offer1.offered_amount:,.2f} ({offer1.offered_percentage:.1f}%)")
    print(f"  Reasoning: {offer1.ai_reasoning[:100]}...")

    # Simulate buyer counteroffer
    print("\n[Round 2] Buyer counters (simulated)")
    buyer_offer = Offer(
        offer_id=str(uuid.uuid4()),
        dispute_id=dispute.dispute_id,
        offered_amount=350000.0,
        offered_percentage=70.0,
        offered_by="buyer",
        status=OfferStatus.SENT,
        created_at=datetime.now() - timedelta(days=1)
    )
    print(f"  Buyer counters: ₹{buyer_offer.offered_amount:,.2f} ({buyer_offer.offered_percentage:.1f}%)")

    negotiation.offers = [offer1, buyer_offer]
    negotiation.current_round = 2

    # MSME counteroffer
    counter1 = mediator.suggest_counter_offer(dispute, negotiation, buyer_offer)
    print(f"\n[Round 3] AI suggests MSME counteroffer")
    print(f"  Suggested counter: ₹{counter1.counter_amount:,.2f} ({counter1.counter_percentage:.1f}%)")
    print(f"  Reasoning: {counter1.ai_reasoning[:100]}...")

    # Analyze probability
    analysis = mediator.analyze_settlement_probability(negotiation)
    print(f"\n[Settlement Analysis]")
    print(f"  Probability: {analysis['probability']:.0%}")
    print(f"  Convergence Rate: {analysis['convergence_rate']:.2f}")
    print(f"  Recommended Action: {analysis['recommended_action']}")
    print(f"  Reasoning: {analysis['reasoning']}")


def demo_settlement_analysis():
    """Demo 3: Settlement probability analysis"""
    print_section("Demo 3: Settlement Probability Analysis")

    policy_engine = PolicyEngine()
    mediator = NegotiationMediator(policy_engine=policy_engine)

    # Scenario: Converging negotiation
    negotiation = Negotiation(
        negotiation_id=str(uuid.uuid4()),
        dispute_id=str(uuid.uuid4()),
        min_settlement_amount=200000.0,
        max_settlement_amount=400000.0,
        current_round=4,
        max_rounds=5
    )

    # Create converging offers: 380k -> 250k -> 340k -> 280k -> 320k
    offers = [
        Offer(
            offer_id=str(uuid.uuid4()),
            dispute_id=negotiation.dispute_id,
            offered_amount=380000.0,
            offered_percentage=95.0,
            offered_by="msme",
            status=OfferStatus.SENT,
            created_at=datetime.now() - timedelta(days=8)
        ),
        Offer(
            offer_id=str(uuid.uuid4()),
            dispute_id=negotiation.dispute_id,
            offered_amount=250000.0,
            offered_percentage=62.5,
            offered_by="buyer",
            status=OfferStatus.SENT,
            created_at=datetime.now() - timedelta(days=6)
        ),
        Offer(
            offer_id=str(uuid.uuid4()),
            dispute_id=negotiation.dispute_id,
            offered_amount=340000.0,
            offered_percentage=85.0,
            offered_by="msme",
            status=OfferStatus.SENT,
            created_at=datetime.now() - timedelta(days=4)
        ),
        Offer(
            offer_id=str(uuid.uuid4()),
            dispute_id=negotiation.dispute_id,
            offered_amount=280000.0,
            offered_percentage=70.0,
            offered_by="buyer",
            status=OfferStatus.SENT,
            created_at=datetime.now() - timedelta(days=2)
        ),
        Offer(
            offer_id=str(uuid.uuid4()),
            dispute_id=negotiation.dispute_id,
            offered_amount=320000.0,
            offered_percentage=80.0,
            offered_by="msme",
            status=OfferStatus.SENT,
            created_at=datetime.now()
        )
    ]

    negotiation.offers = offers

    print("\nNegotiation History:")
    history = negotiation.get_negotiation_history()
    for i, h in enumerate(history, 1):
        print(f"  Round {i}: {h['by'].upper()} offers ₹{h['amount']:,.2f} ({h['amount']/400000*100:.1f}%)")

    analysis = mediator.analyze_settlement_probability(negotiation)

    print(f"\n[AI Analysis]")
    print(f"  Settlement Probability: {analysis['probability']:.0%}")
    print(f"  Convergence Rate: {analysis['convergence_rate']:.2f}")
    print(f"  Recommended Action: {analysis['recommended_action'].upper()}")
    print(f"  Rounds Remaining: {analysis['rounds_remaining']}")
    print(f"  Confidence: {analysis['confidence']:.0%}")
    print(f"\n  Analysis:")
    print(f"  {analysis['reasoning']}")


def demo_policy_compliance():
    """Demo 4: Policy engine integration and bounds enforcement"""
    print_section("Demo 4: Policy Compliance & Bounds Enforcement")

    policy_engine = PolicyEngine()
    mediator = NegotiationMediator(policy_engine=policy_engine)

    print("\nMSMED Act Rules (from policy_rules.yaml):")
    print(f"  Interest Rate: 18% annual")
    print(f"  Settlement Range: 50-100% of original amount")
    print(f"  Max Negotiation Rounds: {policy_engine.get_max_negotiation_rounds()}")

    # Test with various dispute amounts
    test_amounts = [50000, 250000, 1000000]

    print("\nSettlement Bounds for Different Amounts:")
    for amount in test_amounts:
        min_s, max_s = policy_engine.get_settlement_range(amount)
        print(f"  ₹{amount:,}: Min=₹{min_s:,} (50%), Max=₹{max_s:,} (100%)")

    # Generate offer and verify bounds
    dispute = Dispute(
        dispute_id=str(uuid.uuid4()),
        dispute_type=DisputeType.PAYMENT_DELAY,
        dispute_amount=300000.0,
        days_delayed=100
    )

    min_settlement, max_settlement = policy_engine.get_settlement_range(dispute.dispute_amount)
    negotiation = Negotiation(
        negotiation_id=str(uuid.uuid4()),
        dispute_id=dispute.dispute_id,
        min_settlement_amount=min_settlement,
        max_settlement_amount=max_settlement
    )

    offer = mediator.suggest_initial_offer(dispute, negotiation)

    print(f"\n[Bounds Verification]")
    print(f"  Policy Min: ₹{min_settlement:,.2f}")
    print(f"  AI Suggested: ₹{offer.offered_amount:,.2f} ✓")
    print(f"  Policy Max: ₹{max_settlement:,.2f}")
    print(f"  Within bounds: {min_settlement <= offer.offered_amount <= max_settlement}")


def main():
    """Run all demos"""
    print("\n" + "=" * 70)
    print("  AI NEGOTIATION MEDIATOR - DEMONSTRATION")
    print("  MSME Dispute Resolution Platform")
    print("=" * 70)

    try:
        demo_initial_offer()
        print("\n" + "-" * 70)

        demo_negotiation_rounds()
        print("\n" + "-" * 70)

        demo_settlement_analysis()
        print("\n" + "-" * 70)

        demo_policy_compliance()

        print_section("Demo Complete")
        print("\nKey Features Demonstrated:")
        print("  ✓ AI-generated settlement suggestions with reasoning")
        print("  ✓ Multi-round negotiation with convergence analysis")
        print("  ✓ Settlement probability predictions")
        print("  ✓ Policy engine integration (no hardcoded rules)")
        print("  ✓ MSMED Act compliance (interest, bounds, timelines)")
        print("  ✓ Human-approval-first architecture (all suggestions PENDING)")
        print("\nAll suggestions require explicit human approval before being sent.")

    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
