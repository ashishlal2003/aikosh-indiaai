"""
Audit logging models
Full audit trail for all AI actions and system decisions
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class AuditLevel(str, Enum):
    """Severity/importance level of audit event"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditAction(str, Enum):
    """Types of actions that are audited"""
    # Dispute lifecycle
    DISPUTE_CREATED = "dispute_created"
    DISPUTE_UPDATED = "dispute_updated"
    DISPUTE_SUBMITTED = "dispute_submitted"
    DISPUTE_VALIDATED = "dispute_validated"
    DISPUTE_REJECTED = "dispute_rejected"
    
    # Document operations
    DOCUMENT_UPLOADED = "document_uploaded"
    DOCUMENT_VERIFIED = "document_verified"
    DOCUMENT_REJECTED = "document_rejected"
    OCR_PERFORMED = "ocr_performed"
    ENTITY_EXTRACTED = "entity_extracted"
    
    # AI operations
    AI_SUGGESTION_GENERATED = "ai_suggestion_generated"
    AI_SUGGESTION_APPROVED = "ai_suggestion_approved"
    AI_SUGGESTION_REJECTED = "ai_suggestion_rejected"
    AI_CLASSIFICATION_MADE = "ai_classification_made"
    AI_VALIDATION_PERFORMED = "ai_validation_performed"
    
    # Negotiation operations
    OFFER_CREATED = "offer_created"
    OFFER_APPROVED = "offer_approved"
    OFFER_REJECTED = "offer_rejected"
    OFFER_SENT = "offer_sent"
    OFFER_ACCEPTED = "offer_accepted"
    OFFER_REJECTED_BY_PARTY = "offer_rejected_by_party"
    COUNTEROFFER_CREATED = "counteroffer_created"
    SETTLEMENT_REACHED = "settlement_reached"
    
    # Policy operations
    POLICY_LOADED = "policy_loaded"
    POLICY_UPDATED = "policy_updated"
    POLICY_VALIDATION = "policy_validation"
    
    # Human overrides
    HUMAN_OVERRIDE = "human_override"
    MANUAL_APPROVAL = "manual_approval"
    MANUAL_REJECTION = "manual_rejection"
    
    # System operations
    ELIGIBILITY_CHECKED = "eligibility_checked"
    VALIDATION_PERFORMED = "validation_performed"
    ERROR_OCCURRED = "error_occurred"


class AuditLog(BaseModel):
    """
    Individual audit log entry
    Every AI action, system decision, and human action is logged
    """
    log_id: str = Field(..., description="Unique log identifier")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Action details
    action: AuditAction
    level: AuditLevel = Field(default=AuditLevel.INFO)
    
    # Context
    dispute_id: Optional[str] = None
    negotiation_id: Optional[str] = None
    user_id: Optional[str] = Field(None, description="User who performed action (if applicable)")
    session_id: Optional[str] = Field(None, description="Session identifier")
    
    # Action details
    description: str = Field(..., description="Human-readable description of action")
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured details about the action"
    )
    
    # AI-specific fields
    is_ai_action: bool = Field(default=False, description="Whether this was an AI-generated action")
    ai_model: Optional[str] = Field(None, description="AI model used (if applicable)")
    ai_reasoning: Optional[str] = Field(None, description="AI's reasoning for the action")
    ai_confidence: Optional[float] = Field(None, ge=0, le=1, description="AI confidence score")
    ai_inputs: Optional[Dict[str, Any]] = Field(None, description="Inputs provided to AI")
    ai_outputs: Optional[Dict[str, Any]] = Field(None, description="Outputs from AI")
    
    # Human approval/override
    requires_approval: bool = Field(default=False, description="Whether this action required approval")
    approved_by: Optional[str] = Field(None, description="User who approved (if applicable)")
    approved_at: Optional[datetime] = None
    override_reason: Optional[str] = Field(None, description="Reason for human override")
    
    # Policy context
    policy_version: Optional[str] = Field(None, description="Policy version in effect")
    policy_rules_applied: List[str] = Field(
        default_factory=list,
        description="List of policy rules that were applied"
    )
    
    # Error tracking
    error_message: Optional[str] = None
    error_stack: Optional[str] = None
    
    # Compliance
    dpdp_compliant: bool = Field(default=True, description="Whether action complies with DPDP")
    data_retention_required: bool = Field(default=True, description="Whether data must be retained")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ExplainabilityArtifact(BaseModel):
    """
    Explainability artifact for AI decisions
    Provides "why did AI suggest this?" information
    """
    artifact_id: str = Field(..., description="Unique artifact identifier")
    created_at: datetime = Field(default_factory=datetime.now)
    
    # Associated entities
    dispute_id: Optional[str] = None
    negotiation_id: Optional[str] = None
    offer_id: Optional[str] = None
    audit_log_id: Optional[str] = None
    
    # Explanation
    decision_type: str = Field(..., description="Type of decision (e.g., 'settlement_suggestion')")
    decision_summary: str = Field(..., description="Brief summary of the decision")
    detailed_reasoning: str = Field(..., description="Detailed explanation of why this decision was made")
    
    # Factors considered
    factors_considered: List[str] = Field(
        default_factory=list,
        description="List of factors that influenced the decision"
    )
    factor_weights: Dict[str, float] = Field(
        default_factory=dict,
        description="Relative importance of each factor"
    )
    
    # Data sources
    data_sources: List[str] = Field(
        default_factory=list,
        description="Data sources used in decision making"
    )
    
    # Confidence and uncertainty
    confidence_score: float = Field(..., ge=0, le=1)
    uncertainty_factors: List[str] = Field(
        default_factory=list,
        description="Factors that introduce uncertainty"
    )
    
    # Alternatives considered
    alternatives_considered: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Alternative decisions that were considered"
    )
    
    # Policy alignment
    policy_rules_applied: List[str] = Field(
        default_factory=list,
        description="Policy rules that guided this decision"
    )
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

