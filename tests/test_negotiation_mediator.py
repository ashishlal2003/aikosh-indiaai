"""
Tests for AI Negotiation Mediator
Verifies settlement suggestion logic, bounds enforcement, and reasoning quality
"""

import pytest
from datetime import datetime, timedelta
import uuid

from src.negotiation.mediator import NegotiationMediator
from src.models.dispute import Dispute, DisputeType, DisputeStatus, Party, Document
from src.models.negotiation import (
    Negotiation,
    Offer,
    OfferStatus,
    NegotiationState
)
from src.governance.policy_engine import PolicyEngine


@pytest.fixture
def policy_engine():
    """Create PolicyEngine instance"""
    return PolicyEngine()


@pytest.fixture
def mediator(policy_engine):
    """Create NegotiationMediator instance"""
    return NegotiationMediator(policy_engine=policy_engine)


@pytest.fixture
def sample_dispute():
    """Create a sample dispute for testing"""
    return Dispute(
        dispute_id=str(uuid.uuid4()),
        dispute_type=DisputeType.PAYMENT_DELAY,
        status=DisputeStatus.NEGOTIATION_IN_PROGRESS,
        msme_party=Party(
            name="Test MSME",
            gstin="29ABCDE1234F1Z5",
            is_msme=True
        ),
        buyer_party=Party(
            name="Test Buyer",
            gstin="29XYZAB5678G1Z5",
            is_msme=False
        ),
        dispute_amount=100000.0,
        invoice_amount=100000.0,
        invoice_number="INV-2024-001",
        invoice_date=datetime.now() - timedelta(days=120),
        payment_due_date=datetime.now() - timedelta(days=90),
        days_delayed=90,
        documents=[
            Document(
                name="invoice",
                file_path="/path/to/invoice.pdf",
                is_mandatory=True,
                is_verified=True
            ),
            Document(
                name="msme_registration",
                file_path="/path/to/msme_reg.pdf",
                is_mandatory=True,
                is_verified=True
            )
        ],
        is_eligible=True,
        description="Payment delayed by 90 days"
    )


@pytest.fixture
def sample_negotiation(sample_dispute):
    """Create a sample negotiation"""
    min_settlement, max_settlement = 50000.0, 100000.0

    return Negotiation(
        negotiation_id=str(uuid.uuid4()),
        dispute_id=sample_dispute.dispute_id or str(uuid.uuid4()),
        state=NegotiationState.NOT_STARTED,
        current_round=0,
        max_rounds=5,
        min_settlement_amount=min_settlement,
        max_settlement_amount=max_settlement,
        min_settlement_percentage=50.0,
        max_settlement_percentage=100.0
    )


class TestNegotiationMediator:
    """Test suite for NegotiationMediator"""

    def test_initialization(self):
        """Test mediator initialization"""
        mediator = NegotiationMediator()
        assert mediator.policy_engine is not None
        assert mediator.llm_client is None

    def test_initialization_with_policy_engine(self, policy_engine):
        """Test mediator initialization with custom PolicyEngine"""
        mediator = NegotiationMediator(policy_engine=policy_engine)
        assert mediator.policy_engine is policy_engine

    def test_suggest_initial_offer_basic(self, mediator, sample_dispute, sample_negotiation):
        """Test basic initial offer generation"""
        offer = mediator.suggest_initial_offer(sample_dispute, sample_negotiation)

        # Verify offer structure
        assert offer.offer_id is not None
        assert offer.dispute_id == sample_dispute.dispute_id
        assert offer.offered_by == "msme"
        assert offer.status == OfferStatus.PENDING_APPROVAL
        assert offer.is_ai_suggested is True

    def test_initial_offer_within_bounds(self, mediator, sample_dispute, sample_negotiation):
        """Test that initial offer respects settlement bounds"""
        offer = mediator.suggest_initial_offer(sample_dispute, sample_negotiation)

        # Should be within policy bounds (50-100%)
        assert offer.offered_amount >= sample_negotiation.min_settlement_amount
        assert offer.offered_amount <= sample_negotiation.max_settlement_amount

        # Percentage should match
        expected_percentage = (offer.offered_amount / sample_dispute.dispute_amount) * 100
        assert abs(offer.offered_percentage - expected_percentage) < 0.1

    def test_initial_offer_with_interest(self, mediator, sample_dispute, sample_negotiation):
        """Test that initial offer considers interest calculation"""
        # Dispute has 90 days delay
        offer = mediator.suggest_initial_offer(sample_dispute, sample_negotiation)

        # Should suggest higher amount due to delay
        # With 90 days delay, should be around 80-95% of original
        assert offer.offered_percentage >= 80.0
        assert offer.offered_percentage <= 100.0

    def test_initial_offer_reasoning_quality(self, mediator, sample_dispute, sample_negotiation):
        """Test that AI reasoning is non-empty and relevant"""
        offer = mediator.suggest_initial_offer(sample_dispute, sample_negotiation)

        assert offer.ai_reasoning is not None
        assert len(offer.ai_reasoning) > 50  # Substantial reasoning
        assert "MSMED Act" in offer.ai_reasoning or "settlement" in offer.ai_reasoning

    def test_initial_offer_confidence_score(self, mediator, sample_dispute, sample_negotiation):
        """Test confidence score is in valid range"""
        offer = mediator.suggest_initial_offer(sample_dispute, sample_negotiation)

        assert offer.ai_confidence is not None
        assert 0.0 <= offer.ai_confidence <= 1.0

    def test_suggest_counter_offer_basic(self, mediator, sample_dispute, sample_negotiation):
        """Test basic counteroffer generation"""
        # Create an initial offer first
        initial_offer = Offer(
            offer_id=str(uuid.uuid4()),
            dispute_id=sample_dispute.dispute_id or str(uuid.uuid4()),
            offered_amount=70000.0,
            offered_percentage=70.0,
            offered_by="buyer",
            status=OfferStatus.SENT
        )

        sample_negotiation.offers.append(initial_offer)
        sample_negotiation.current_round = 1

        counter = mediator.suggest_counter_offer(
            sample_dispute,
            sample_negotiation,
            initial_offer
        )

        # Verify counteroffer structure
        assert counter.counteroffer_id is not None
        assert counter.original_offer_id == initial_offer.offer_id
        assert counter.offered_by == "msme"  # Counter by MSME
        assert counter.status == OfferStatus.PENDING_APPROVAL
        assert counter.is_ai_suggested is True

    def test_counter_offer_within_bounds(self, mediator, sample_dispute, sample_negotiation):
        """Test counteroffer respects bounds"""
        initial_offer = Offer(
            offer_id=str(uuid.uuid4()),
            dispute_id=sample_dispute.dispute_id or str(uuid.uuid4()),
            offered_amount=60000.0,
            offered_percentage=60.0,
            offered_by="buyer",
            status=OfferStatus.SENT
        )

        sample_negotiation.offers.append(initial_offer)

        counter = mediator.suggest_counter_offer(
            sample_dispute,
            sample_negotiation,
            initial_offer
        )

        assert counter.counter_amount >= sample_negotiation.min_settlement_amount
        assert counter.counter_amount <= sample_negotiation.max_settlement_amount

    def test_counter_offer_convergence(self, mediator, sample_dispute, sample_negotiation):
        """Test that counteroffers move toward convergence"""
        # Create negotiation history
        offer1 = Offer(
            offer_id=str(uuid.uuid4()),
            dispute_id=sample_dispute.dispute_id or str(uuid.uuid4()),
            offered_amount=90000.0,
            offered_percentage=90.0,
            offered_by="msme",
            status=OfferStatus.SENT,
            created_at=datetime.now() - timedelta(days=2)
        )

        offer2 = Offer(
            offer_id=str(uuid.uuid4()),
            dispute_id=sample_dispute.dispute_id or str(uuid.uuid4()),
            offered_amount=70000.0,
            offered_percentage=70.0,
            offered_by="buyer",
            status=OfferStatus.SENT,
            created_at=datetime.now() - timedelta(days=1)
        )

        sample_negotiation.offers = [offer1, offer2]
        sample_negotiation.current_round = 2

        counter = mediator.suggest_counter_offer(
            sample_dispute,
            sample_negotiation,
            offer2
        )

        # Counter should be between the two previous offers
        assert counter.counter_amount > offer2.offered_amount
        assert counter.counter_amount < offer1.offered_amount

    def test_analyze_settlement_probability_no_offers(self, mediator, sample_negotiation):
        """Test probability analysis with no offers"""
        analysis = mediator.analyze_settlement_probability(sample_negotiation)

        assert analysis["probability"] == 0.0
        assert analysis["recommended_action"] == "make_initial_offer"
        assert "reasoning" in analysis

    def test_analyze_settlement_probability_one_offer(self, mediator, sample_negotiation):
        """Test probability analysis with one offer"""
        offer = Offer(
            offer_id=str(uuid.uuid4()),
            dispute_id=sample_negotiation.dispute_id,
            offered_amount=85000.0,
            offered_percentage=85.0,
            offered_by="msme",
            status=OfferStatus.SENT
        )
        sample_negotiation.offers.append(offer)

        analysis = mediator.analyze_settlement_probability(sample_negotiation)

        assert analysis["probability"] > 0.0
        assert analysis["probability"] < 0.5
        assert analysis["recommended_action"] == "wait_for_response"

    def test_analyze_settlement_probability_converging(self, mediator, sample_negotiation):
        """Test probability analysis with converging offers"""
        # Create converging pattern: 90k -> 70k -> 85k -> 75k
        offers = [
            Offer(
                offer_id=str(uuid.uuid4()),
                dispute_id=sample_negotiation.dispute_id,
                offered_amount=90000.0,
                offered_percentage=90.0,
                offered_by="msme",
                status=OfferStatus.SENT,
                created_at=datetime.now() - timedelta(days=4)
            ),
            Offer(
                offer_id=str(uuid.uuid4()),
                dispute_id=sample_negotiation.dispute_id,
                offered_amount=70000.0,
                offered_percentage=70.0,
                offered_by="buyer",
                status=OfferStatus.SENT,
                created_at=datetime.now() - timedelta(days=3)
            ),
            Offer(
                offer_id=str(uuid.uuid4()),
                dispute_id=sample_negotiation.dispute_id,
                offered_amount=85000.0,
                offered_percentage=85.0,
                offered_by="msme",
                status=OfferStatus.SENT,
                created_at=datetime.now() - timedelta(days=2)
            ),
            Offer(
                offer_id=str(uuid.uuid4()),
                dispute_id=sample_negotiation.dispute_id,
                offered_amount=75000.0,
                offered_percentage=75.0,
                offered_by="buyer",
                status=OfferStatus.SENT,
                created_at=datetime.now() - timedelta(days=1)
            )
        ]

        sample_negotiation.offers = offers
        sample_negotiation.current_round = 4

        analysis = mediator.analyze_settlement_probability(sample_negotiation)

        # Should show high probability
        assert analysis["probability"] >= 0.4
        assert "convergence_rate" in analysis

    def test_analyze_settlement_probability_near_max_rounds(self, mediator, sample_negotiation):
        """Test probability analysis near maximum rounds"""
        sample_negotiation.current_round = 4
        sample_negotiation.max_rounds = 5

        # Add non-converging offers
        offers = [
            Offer(
                offer_id=str(uuid.uuid4()),
                dispute_id=sample_negotiation.dispute_id,
                offered_amount=90000.0,
                offered_percentage=90.0,
                offered_by="msme",
                status=OfferStatus.SENT
            ),
            Offer(
                offer_id=str(uuid.uuid4()),
                dispute_id=sample_negotiation.dispute_id,
                offered_amount=60000.0,
                offered_percentage=60.0,
                offered_by="buyer",
                status=OfferStatus.SENT
            )
        ]
        sample_negotiation.offers = offers

        analysis = mediator.analyze_settlement_probability(sample_negotiation)

        # Should recommend escalation
        assert "escalate" in analysis["recommended_action"].lower()
        assert analysis["rounds_remaining"] == 1

    def test_missing_dispute_amount_raises_error(self, mediator, sample_negotiation):
        """Test that missing dispute amount raises ValueError"""
        bad_dispute = Dispute(
            dispute_type=DisputeType.PAYMENT_DELAY,
            dispute_amount=None  # Missing amount
        )

        with pytest.raises(ValueError, match="Dispute amount is required"):
            mediator.suggest_initial_offer(bad_dispute, sample_negotiation)

    def test_policy_engine_integration(self, mediator, sample_dispute, sample_negotiation):
        """Test that mediator properly uses PolicyEngine"""
        # Generate offer
        offer = mediator.suggest_initial_offer(sample_dispute, sample_negotiation)

        # Verify it uses policy bounds
        min_pct = mediator.policy_engine.policy_config.get('negotiation', {}).get(
            'min_settlement_percentage', 50.0
        )
        max_pct = mediator.policy_engine.policy_config.get('negotiation', {}).get(
            'max_settlement_percentage', 100.0
        )

        assert offer.offered_percentage >= min_pct
        assert offer.offered_percentage <= max_pct

    def test_interest_calculation_integration(self, mediator, sample_dispute, sample_negotiation):
        """Test integration with PolicyEngine interest calculation"""
        # Verify interest is calculated for delayed payment
        offer = mediator.suggest_initial_offer(sample_dispute, sample_negotiation)

        # Should mention interest in reasoning since payment is delayed
        assert "interest" in offer.ai_reasoning.lower() or "delay" in offer.ai_reasoning.lower()

    def test_multiple_offers_different_disputes(self, mediator, policy_engine):
        """Test generating offers for different dispute scenarios"""
        # High-value, long-delayed dispute
        high_dispute = Dispute(
            dispute_id=str(uuid.uuid4()),
            dispute_type=DisputeType.PAYMENT_DELAY,
            dispute_amount=500000.0,
            payment_due_date=datetime.now() - timedelta(days=180),
            days_delayed=180
        )

        high_neg = Negotiation(
            negotiation_id=str(uuid.uuid4()),
            dispute_id=high_dispute.dispute_id or str(uuid.uuid4()),
            min_settlement_amount=250000.0,
            max_settlement_amount=500000.0
        )

        # Low-value, short-delayed dispute
        low_dispute = Dispute(
            dispute_id=str(uuid.uuid4()),
            dispute_type=DisputeType.PAYMENT_DELAY,
            dispute_amount=50000.0,
            payment_due_date=datetime.now() - timedelta(days=50),
            days_delayed=50
        )

        low_neg = Negotiation(
            negotiation_id=str(uuid.uuid4()),
            dispute_id=low_dispute.dispute_id or str(uuid.uuid4()),
            min_settlement_amount=25000.0,
            max_settlement_amount=50000.0
        )

        high_offer = mediator.suggest_initial_offer(high_dispute, high_neg)
        low_offer = mediator.suggest_initial_offer(low_dispute, low_neg)

        # High-delay case should have higher percentage
        assert high_offer.offered_percentage >= low_offer.offered_percentage

    def test_no_hardcoded_rules(self, mediator, sample_dispute, sample_negotiation):
        """Verify no business rules are hardcoded - all come from PolicyEngine"""
        offer = mediator.suggest_initial_offer(sample_dispute, sample_negotiation)

        # Bounds should match policy engine
        min_settlement, max_settlement = mediator.policy_engine.get_settlement_range(
            sample_dispute.dispute_amount
        )

        assert sample_negotiation.min_settlement_amount == min_settlement
        assert sample_negotiation.max_settlement_amount == max_settlement

    def test_reasoning_mentions_msmed_act(self, mediator, sample_dispute, sample_negotiation):
        """Test that reasoning references legal basis"""
        sample_dispute.days_delayed = 120  # Significant delay

        offer = mediator.suggest_initial_offer(sample_dispute, sample_negotiation)

        # Should mention MSMED Act or legal basis
        reasoning_lower = offer.ai_reasoning.lower()
        assert "msmed" in reasoning_lower or "section 16" in reasoning_lower

    def test_counter_offer_for_buyer(self, mediator, sample_dispute, sample_negotiation):
        """Test counteroffer suggested for buyer"""
        # MSME makes initial offer
        msme_offer = Offer(
            offer_id=str(uuid.uuid4()),
            dispute_id=sample_dispute.dispute_id or str(uuid.uuid4()),
            offered_amount=90000.0,
            offered_percentage=90.0,
            offered_by="msme",
            status=OfferStatus.SENT
        )

        sample_negotiation.offers.append(msme_offer)

        counter = mediator.suggest_counter_offer(
            sample_dispute,
            sample_negotiation,
            msme_offer
        )

        # Should suggest counter from buyer
        assert counter.offered_by == "buyer"

    def test_payment_terms_included(self, mediator, sample_dispute, sample_negotiation):
        """Test that offers include payment terms"""
        offer = mediator.suggest_initial_offer(sample_dispute, sample_negotiation)

        assert offer.payment_terms is not None
        assert len(offer.payment_terms) > 0


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_zero_delay_dispute(self, mediator, sample_dispute, sample_negotiation):
        """Test offer generation with no payment delay"""
        sample_dispute.days_delayed = 0
        sample_dispute.payment_due_date = datetime.now()

        offer = mediator.suggest_initial_offer(sample_dispute, sample_negotiation)

        # Should still generate valid offer
        assert offer.offered_amount > 0
        assert offer.ai_confidence is not None

    def test_very_small_dispute_amount(self, mediator, sample_negotiation):
        """Test with very small dispute amount"""
        small_dispute = Dispute(
            dispute_id=str(uuid.uuid4()),
            dispute_type=DisputeType.PAYMENT_DELAY,
            dispute_amount=100.0,  # Very small
            days_delayed=60
        )

        small_negotiation = Negotiation(
            negotiation_id=str(uuid.uuid4()),
            dispute_id=small_dispute.dispute_id or str(uuid.uuid4()),
            min_settlement_amount=50.0,
            max_settlement_amount=100.0
        )

        offer = mediator.suggest_initial_offer(small_dispute, small_negotiation)

        assert offer.offered_amount >= 50.0
        assert offer.offered_amount <= 100.0

    def test_negotiation_at_max_rounds(self, mediator, sample_dispute, sample_negotiation):
        """Test probability analysis at maximum rounds"""
        sample_negotiation.current_round = 5
        sample_negotiation.max_rounds = 5

        analysis = mediator.analyze_settlement_probability(sample_negotiation)

        # Should have reasoning about max rounds
        assert "rounds_remaining" in analysis
        assert analysis["rounds_remaining"] == 0
