"""
Negotiation data models
Represents the negotiation state and offers/counteroffers
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator


class NegotiationState(str, Enum):
    """Current state of negotiation"""
    NOT_STARTED = "not_started"
    INITIAL_OFFER_PENDING = "initial_offer_pending"  # MSME offer awaiting buyer response
    BUYER_RESPONSE_PENDING = "buyer_response_pending"  # Buyer counteroffer awaiting MSME response
    MSME_RESPONSE_PENDING = "msme_response_pending"  # MSME counteroffer awaiting buyer response
    SETTLEMENT_REACHED = "settlement_reached"  # Both parties agreed
    NEGOTIATION_FAILED = "negotiation_failed"  # No agreement reached
    EXPIRED = "expired"  # Time limit exceeded


class OfferStatus(str, Enum):
    """Status of an individual offer"""
    PENDING_APPROVAL = "pending_approval"  # AI suggestion, awaiting human approval
    APPROVED = "approved"  # Human approved, sent to other party
    REJECTED = "rejected"  # Human rejected the suggestion
    SENT = "sent"  # Sent to other party
    ACCEPTED = "accepted"  # Other party accepted
    REJECTED_BY_OTHER = "rejected_by_other"  # Other party rejected
    EXPIRED = "expired"  # Time limit exceeded


class Offer(BaseModel):
    """
    Represents a settlement offer
    All offers require explicit human approval before being sent
    """
    offer_id: str = Field(..., description="Unique offer identifier")
    dispute_id: str = Field(..., description="Associated dispute ID")
    created_at: datetime = Field(default_factory=datetime.now)
    
    # Offer details
    offered_amount: float = Field(..., ge=0, description="Settlement amount offered (INR)")
    offered_percentage: float = Field(..., ge=0, le=100, description="Percentage of original amount")
    payment_terms: Optional[str] = Field(None, description="Proposed payment terms (e.g., '30 days')")
    
    # Offer metadata
    offered_by: str = Field(..., description="Party making offer: 'msme' or 'buyer'")
    status: OfferStatus = Field(default=OfferStatus.PENDING_APPROVAL)
    
    # AI-generated suggestion metadata
    is_ai_suggested: bool = Field(default=True, description="Whether this is an AI suggestion")
    ai_reasoning: Optional[str] = Field(None, description="AI's explanation for this suggestion")
    ai_confidence: Optional[float] = Field(None, ge=0, le=1, description="AI confidence score")
    
    # Human approval
    approved_by: Optional[str] = Field(None, description="User ID who approved this")
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = Field(None, description="Reason if rejected")
    
    # Response tracking
    responded_at: Optional[datetime] = None
    response_notes: Optional[str] = None
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CounterOffer(BaseModel):
    """
    Represents a counteroffer in response to an offer
    """
    counteroffer_id: str = Field(..., description="Unique counteroffer identifier")
    original_offer_id: str = Field(..., description="ID of offer being countered")
    created_at: datetime = Field(default_factory=datetime.now)
    
    # Counteroffer details
    counter_amount: float = Field(..., ge=0, description="Counteroffer amount (INR)")
    counter_percentage: float = Field(..., ge=0, le=100, description="Percentage of original amount")
    payment_terms: Optional[str] = None
    
    # Metadata
    offered_by: str = Field(..., description="Party making counteroffer")
    status: OfferStatus = Field(default=OfferStatus.PENDING_APPROVAL)
    
    # AI suggestion metadata
    is_ai_suggested: bool = Field(default=True)
    ai_reasoning: Optional[str] = None
    ai_confidence: Optional[float] = None
    
    # Human approval
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    
    # Response tracking
    responded_at: Optional[datetime] = None
    response_notes: Optional[str] = None


class Negotiation(BaseModel):
    """
    Complete negotiation state for a dispute
    Tracks all offers, counteroffers, and negotiation progress
    """
    negotiation_id: str = Field(..., description="Unique negotiation identifier")
    dispute_id: str = Field(..., description="Associated dispute ID")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # Negotiation state
    state: NegotiationState = Field(default=NegotiationState.NOT_STARTED)
    current_round: int = Field(default=0, ge=0, description="Current negotiation round")
    max_rounds: int = Field(default=5, description="Maximum allowed rounds")
    
    # Offers and counteroffers
    offers: List[Offer] = Field(default_factory=list)
    counteroffers: List[CounterOffer] = Field(default_factory=list)
    
    # Settlement details (if reached)
    final_settlement_amount: Optional[float] = None
    final_settlement_percentage: Optional[float] = None
    settlement_agreed_at: Optional[datetime] = None
    settlement_terms: Optional[str] = None
    
    # Legal bounds
    min_settlement_amount: float = Field(..., ge=0, description="Minimum acceptable settlement")
    max_settlement_amount: float = Field(..., ge=0, description="Maximum possible settlement (original amount)")
    min_settlement_percentage: float = Field(default=50.0, ge=0, le=100)
    max_settlement_percentage: float = Field(default=100.0, ge=0, le=100)
    
    # Timeline tracking
    last_activity_at: Optional[datetime] = None
    msme_last_response_at: Optional[datetime] = None
    buyer_last_response_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    # AI mediation metadata
    ai_suggestions_count: int = Field(default=0, description="Total AI suggestions made")
    ai_suggestions_accepted: int = Field(default=0, description="AI suggestions accepted by humans")
    ai_suggestions_rejected: int = Field(default=0, description="AI suggestions rejected by humans")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def get_current_offer(self) -> Optional[Offer]:
        """Get the most recent offer that's pending response"""
        if not self.offers:
            return None
        # Return the most recent offer that's not yet responded to
        for offer in reversed(self.offers):
            if offer.status in [OfferStatus.SENT, OfferStatus.PENDING_APPROVAL]:
                return offer
        return None
    
    def can_make_new_offer(self) -> bool:
        """Check if a new offer can be made"""
        if self.state == NegotiationState.SETTLEMENT_REACHED:
            return False
        if self.state == NegotiationState.NEGOTIATION_FAILED:
            return False
        if self.current_round >= self.max_rounds:
            return False
        return True
    
    def get_negotiation_history(self) -> List[Dict[str, Any]]:
        """Get chronological history of all offers and counteroffers"""
        history = []
        for offer in sorted(self.offers, key=lambda x: x.created_at):
            history.append({
                "type": "offer",
                "id": offer.offer_id,
                "amount": offer.offered_amount,
                "by": offer.offered_by,
                "status": offer.status,
                "timestamp": offer.created_at,
                "is_ai_suggested": offer.is_ai_suggested,
            })
        for counter in sorted(self.counteroffers, key=lambda x: x.created_at):
            history.append({
                "type": "counteroffer",
                "id": counter.counteroffer_id,
                "amount": counter.counter_amount,
                "by": counter.offered_by,
                "status": counter.status,
                "timestamp": counter.created_at,
                "is_ai_suggested": counter.is_ai_suggested,
            })
        return sorted(history, key=lambda x: x["timestamp"])

