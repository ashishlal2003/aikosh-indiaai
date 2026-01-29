"""
AI Negotiation Mediator
Generates settlement suggestions with reasoning for MSME disputes
AI suggests ONLY - all suggestions require explicit human approval
"""

from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
import uuid

from src.models.dispute import Dispute
from src.models.negotiation import (
    Negotiation,
    Offer,
    CounterOffer,
    OfferStatus,
    NegotiationState
)
from src.governance.policy_engine import PolicyEngine


class NegotiationMediator:
    """
    AI-powered negotiation mediator that suggests settlements
    Uses PolicyEngine for all rules - no hardcoded business logic
    """

    def __init__(
        self,
        policy_engine: Optional[PolicyEngine] = None,
        llm_client: Optional[Any] = None
    ):
        """
        Initialize negotiation mediator

        Args:
            policy_engine: PolicyEngine instance for rules (creates new if None)
            llm_client: Optional LLM client (OpenAI/Anthropic). Falls back to rule-based if None
        """
        self.policy_engine = policy_engine or PolicyEngine()
        self.llm_client = llm_client

    def suggest_initial_offer(
        self,
        dispute: Dispute,
        negotiation: Negotiation
    ) -> Offer:
        """
        Generate AI-suggested initial settlement offer for MSME

        Args:
            dispute: Dispute object with details
            negotiation: Negotiation object with bounds

        Returns:
            Offer with status=PENDING_APPROVAL requiring human approval
        """
        if not dispute.dispute_amount:
            raise ValueError("Dispute amount is required for offer generation")

        # Calculate interest if applicable
        interest_amount = 0.0
        if dispute.payment_due_date:
            interest_amount = self.policy_engine.calculate_interest(
                principal=dispute.dispute_amount,
                start_date=dispute.payment_due_date,
                end_date=datetime.now()
            )

        # Calculate fair settlement using rules
        suggested_amount, confidence = self._calculate_fair_settlement(
            dispute_amount=dispute.dispute_amount,
            days_delayed=dispute.days_delayed or 0,
            interest_amount=interest_amount,
            negotiation=negotiation
        )

        # Generate reasoning
        reasoning = self._generate_reasoning(
            dispute=dispute,
            suggested_amount=suggested_amount,
            interest_amount=interest_amount,
            is_initial=True
        )

        # Create offer with PENDING_APPROVAL status
        offer = Offer(
            offer_id=str(uuid.uuid4()),
            dispute_id=dispute.dispute_id or str(uuid.uuid4()),
            offered_amount=suggested_amount,
            offered_percentage=round((suggested_amount / dispute.dispute_amount) * 100, 2),
            offered_by="msme",
            status=OfferStatus.PENDING_APPROVAL,
            is_ai_suggested=True,
            ai_reasoning=reasoning,
            ai_confidence=confidence,
            payment_terms="30 days from acceptance"
        )

        return offer

    def suggest_counter_offer(
        self,
        dispute: Dispute,
        negotiation: Negotiation,
        current_offer: Offer
    ) -> CounterOffer:
        """
        Generate AI-suggested counteroffer based on negotiation history

        Args:
            dispute: Dispute object
            negotiation: Current negotiation state
            current_offer: Offer being countered

        Returns:
            CounterOffer with status=PENDING_APPROVAL
        """
        if not dispute.dispute_amount:
            raise ValueError("Dispute amount is required")

        # Analyze convergence patterns
        history = negotiation.get_negotiation_history()

        # Calculate strategic counteroffer
        counter_amount, confidence = self._calculate_counter_offer(
            dispute_amount=dispute.dispute_amount,
            current_offer_amount=current_offer.offered_amount,
            negotiation_history=history,
            negotiation=negotiation
        )

        # Generate reasoning
        reasoning = self._generate_counter_reasoning(
            dispute=dispute,
            current_offer=current_offer,
            counter_amount=counter_amount,
            history=history
        )

        # Determine who is countering
        counter_by = "msme" if current_offer.offered_by == "buyer" else "buyer"

        counteroffer = CounterOffer(
            counteroffer_id=str(uuid.uuid4()),
            original_offer_id=current_offer.offer_id,
            counter_amount=counter_amount,
            counter_percentage=round((counter_amount / dispute.dispute_amount) * 100, 2),
            offered_by=counter_by,
            status=OfferStatus.PENDING_APPROVAL,
            is_ai_suggested=True,
            ai_reasoning=reasoning,
            ai_confidence=confidence,
            payment_terms="30 days from acceptance"
        )

        return counteroffer

    def analyze_settlement_probability(
        self,
        negotiation: Negotiation
    ) -> Dict[str, Any]:
        """
        Analyze likelihood of settlement based on current state

        Args:
            negotiation: Current negotiation state

        Returns:
            Dictionary with probability, reasoning, and recommended action
        """
        history = negotiation.get_negotiation_history()
        rounds_remaining = negotiation.max_rounds - negotiation.current_round

        # No offers yet
        if len(history) == 0:
            return {
                "probability": 0.0,
                "reasoning": "No offers have been made yet",
                "recommended_action": "make_initial_offer",
                "confidence": 1.0,
                "convergence_rate": 0.0,
                "rounds_remaining": rounds_remaining
            }

        # Only one offer
        if len(history) == 1:
            return {
                "probability": 0.3,
                "reasoning": "Initial offer made, awaiting response",
                "recommended_action": "wait_for_response",
                "confidence": 0.8,
                "convergence_rate": 0.0,
                "rounds_remaining": rounds_remaining
            }

        # Analyze convergence
        amounts = [h["amount"] for h in history]
        if len(amounts) < 2:
            convergence_rate = 0.0
        else:
            # Check if offers are getting closer
            diffs = [abs(amounts[i+1] - amounts[i]) for i in range(len(amounts)-1)]
            if len(diffs) > 1:
                convergence_rate = (diffs[-2] - diffs[-1]) / diffs[-2] if diffs[-2] > 0 else 0.0
            else:
                convergence_rate = 0.0

        # Calculate probability based on convergence
        if convergence_rate > 0.5:
            probability = 0.85
            reasoning = "Offers are converging rapidly. Settlement highly likely."
            action = "accept" if len(history) >= 3 else "counter"
        elif convergence_rate > 0.2:
            probability = 0.65
            reasoning = "Offers are converging steadily. Continue negotiation."
            action = "counter"
        elif convergence_rate > 0:
            probability = 0.45
            reasoning = "Offers are converging slowly. More rounds may be needed."
            action = "counter"
        else:
            probability = 0.25
            reasoning = "Offers are not converging. Consider escalation."
            action = "escalate" if negotiation.current_round >= 4 else "counter"

        # Check if near max rounds
        if negotiation.current_round >= negotiation.max_rounds - 1:
            if probability < 0.6:
                action = "escalate"
                reasoning += " Maximum rounds approaching."

        return {
            "probability": round(probability, 2),
            "reasoning": reasoning,
            "recommended_action": action,
            "confidence": 0.75,
            "convergence_rate": round(convergence_rate, 2),
            "rounds_remaining": negotiation.max_rounds - negotiation.current_round
        }

    def _calculate_fair_settlement(
        self,
        dispute_amount: float,
        days_delayed: int,
        interest_amount: float,
        negotiation: Negotiation
    ) -> Tuple[float, float]:
        """
        Calculate fair settlement amount and confidence score
        Uses rule-based heuristics aligned with MSMED Act

        Returns:
            (suggested_amount, confidence_score)
        """
        # Base calculation: principal + interest
        total_claim = dispute_amount + interest_amount

        # Get settlement bounds from policy
        min_amount = negotiation.min_settlement_amount
        max_amount = negotiation.max_settlement_amount

        # Strategic starting point: 85-95% depending on case strength
        # Stronger case (more delay, clear documentation) = higher starting point

        # Delay factor: more delay = stronger case
        delay_factor = min(days_delayed / 180.0, 1.0)  # Cap at 180 days

        # Interest factor: higher interest = stronger case
        interest_ratio = interest_amount / dispute_amount if dispute_amount > 0 else 0
        interest_factor = min(interest_ratio / 0.2, 1.0)  # Cap at 20% interest

        # Calculate strength score (0.0 to 1.0)
        strength_score = (delay_factor * 0.6) + (interest_factor * 0.4)

        # Starting offer: 80% + (strength * 15%) = 80-95%
        starting_percentage = 80.0 + (strength_score * 15.0)
        suggested_amount = dispute_amount * (starting_percentage / 100.0)

        # Ensure within bounds
        suggested_amount = max(min_amount, min(suggested_amount, max_amount))

        # Confidence based on case clarity
        confidence = 0.7 + (strength_score * 0.2)  # 0.7 to 0.9

        return round(suggested_amount, 2), round(confidence, 2)

    def _calculate_counter_offer(
        self,
        dispute_amount: float,
        current_offer_amount: float,
        negotiation_history: List[Dict[str, Any]],
        negotiation: Negotiation
    ) -> Tuple[float, float]:
        """
        Calculate strategic counteroffer amount

        Returns:
            (counter_amount, confidence_score)
        """
        min_amount = negotiation.min_settlement_amount
        max_amount = negotiation.max_settlement_amount

        # Get previous amounts
        amounts = [h["amount"] for h in negotiation_history]

        if len(amounts) < 2:
            # First counteroffer: split the difference slightly
            midpoint = (current_offer_amount + max_amount) / 2
            counter_amount = midpoint * 0.95  # Slightly below midpoint
            confidence = 0.65
        else:
            # Get the last offer from the party making the counteroffer
            # Find the most recent offer from the same party as would be making the counter
            current_party = negotiation_history[-1]["by"]
            counter_party = "msme" if current_party == "buyer" else "buyer"

            # Find last offer from counter party
            last_counter_party_amount = None
            for h in reversed(negotiation_history):
                if h["by"] == counter_party:
                    last_counter_party_amount = h["amount"]
                    break

            if last_counter_party_amount is None:
                # No previous offer from counter party, use midpoint approach
                midpoint = (current_offer_amount + max_amount) / 2
                counter_amount = midpoint * 0.95
            else:
                # Move toward current offer from last position
                gap = abs(current_offer_amount - last_counter_party_amount)
                move_factor = 0.5  # Move halfway

                if last_counter_party_amount > current_offer_amount:
                    # Counter party was higher, move down
                    counter_amount = last_counter_party_amount - (gap * move_factor)
                else:
                    # Counter party was lower, move up
                    counter_amount = last_counter_party_amount + (gap * move_factor)

            confidence = 0.7 + (0.1 * min(len(amounts) / 5, 1.0))  # Higher confidence with more history

        # Ensure within bounds
        counter_amount = max(min_amount, min(counter_amount, max_amount))

        return round(counter_amount, 2), round(confidence, 2)

    def _generate_reasoning(
        self,
        dispute: Dispute,
        suggested_amount: float,
        interest_amount: float,
        is_initial: bool
    ) -> str:
        """
        Generate plain-language reasoning for settlement suggestion

        Returns:
            Human-readable explanation
        """
        if not dispute.dispute_amount:
            return "Unable to generate reasoning without dispute amount"

        percentage = (suggested_amount / dispute.dispute_amount) * 100

        reasoning_parts = []

        # Opening
        if is_initial:
            reasoning_parts.append(
                f"I recommend starting with a settlement offer of ₹{suggested_amount:,.2f} "
                f"({percentage:.1f}% of the original amount)."
            )

        # Interest component
        if interest_amount > 0:
            reasoning_parts.append(
                f"Under Section 16 of the MSMED Act, interest of ₹{interest_amount:,.2f} "
                f"has accrued due to the {dispute.days_delayed or 0} days of payment delay."
            )

        # Case strength
        if dispute.days_delayed and dispute.days_delayed > 90:
            reasoning_parts.append(
                "The extended payment delay strengthens your case for a higher settlement."
            )
        elif dispute.days_delayed and dispute.days_delayed > 45:
            reasoning_parts.append(
                "The payment delay exceeds the MSMED Act threshold, supporting your claim."
            )

        # Documentation
        if dispute.has_all_mandatory_documents():
            reasoning_parts.append(
                "Your documentation is complete, which strengthens your negotiating position."
            )

        # Strategic advice
        reasoning_parts.append(
            "This starting point allows room for negotiation while maintaining a strong position. "
            "The buyer may counter, but we can work toward a fair settlement."
        )

        return " ".join(reasoning_parts)

    def _generate_counter_reasoning(
        self,
        dispute: Dispute,
        current_offer: Offer,
        counter_amount: float,
        history: List[Dict[str, Any]]
    ) -> str:
        """
        Generate reasoning for counteroffer

        Returns:
            Human-readable explanation
        """
        if not dispute.dispute_amount:
            return "Unable to generate reasoning without dispute amount"

        counter_percentage = (counter_amount / dispute.dispute_amount) * 100
        current_percentage = (current_offer.offered_amount / dispute.dispute_amount) * 100

        reasoning_parts = []

        # Analysis of current offer
        if current_percentage < 70:
            reasoning_parts.append(
                f"The current offer of ₹{current_offer.offered_amount:,.2f} "
                f"({current_percentage:.1f}%) is below a fair settlement range."
            )
        elif current_percentage < 85:
            reasoning_parts.append(
                f"The current offer of ₹{current_offer.offered_amount:,.2f} "
                f"({current_percentage:.1f}%) is in the negotiable range."
            )
        else:
            reasoning_parts.append(
                f"The current offer of ₹{current_offer.offered_amount:,.2f} "
                f"({current_percentage:.1f}%) is approaching a fair settlement."
            )

        # Counteroffer recommendation
        reasoning_parts.append(
            f"I recommend countering with ₹{counter_amount:,.2f} ({counter_percentage:.1f}%). "
        )

        # Progress assessment
        if len(history) >= 3:
            reasoning_parts.append(
                "The negotiation is progressing. This counteroffer moves toward a mutually acceptable settlement."
            )
        else:
            reasoning_parts.append(
                "This counteroffer balances your interests while showing willingness to negotiate."
            )

        # Convergence note
        gap = abs(counter_amount - current_offer.offered_amount)
        gap_percentage = (gap / dispute.dispute_amount) * 100

        if gap_percentage < 10:
            reasoning_parts.append(
                f"The remaining gap is only {gap_percentage:.1f}% - settlement is within reach."
            )

        return " ".join(reasoning_parts)
