"""
Dispute data model
Represents a MSME dispute case with all required information
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator


class DisputeType(str, Enum):
    """Types of disputes supported"""
    PAYMENT_DELAY = "payment_delay"
    PARTIAL_PAYMENT = "partial_payment"
    QUALITY_DISPUTE = "quality_dispute"


class DisputeStatus(str, Enum):
    """Current status of the dispute"""
    DRAFT = "draft"  # Being filled out
    PENDING_VALIDATION = "pending_validation"  # Submitted, awaiting validation
    VALIDATED = "validated"  # Passed validation, ready for officer review
    REJECTED = "rejected"  # Failed validation or eligibility
    UNDER_REVIEW = "under_review"  # Officer reviewing
    NEGOTIATION_IN_PROGRESS = "negotiation_in_progress"  # In negotiation phase
    SETTLED = "settled"  # Resolved through negotiation
    ESCALATED = "escalated"  # Moved to formal resolution
    CLOSED = "closed"  # Case closed


class Document(BaseModel):
    """Represents a document uploaded for the dispute"""
    name: str = Field(..., description="Document name/type")
    file_path: str = Field(..., description="Path to stored document")
    upload_date: datetime = Field(default_factory=datetime.now)
    is_mandatory: bool = Field(default=False, description="Whether this document is mandatory")
    is_verified: bool = Field(default=False, description="Whether document has been verified")
    extracted_entities: Dict[str, Any] = Field(
        default_factory=dict,
        description="Entities extracted from document (amounts, dates, etc.)"
    )
    ocr_text: Optional[str] = Field(None, description="OCR extracted text")
    validation_errors: List[str] = Field(
        default_factory=list,
        description="Any validation errors found in this document"
    )


class Party(BaseModel):
    """Represents a party in the dispute (MSME or Buyer)"""
    name: str
    gstin: Optional[str] = None
    registration_number: Optional[str] = None
    address: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    is_msme: bool = Field(default=False, description="Whether this party is the MSME")


class Dispute(BaseModel):
    """
    Complete dispute object
    All mandatory fields must be present before submission
    """
    # Basic identification
    dispute_id: Optional[str] = Field(None, description="Unique dispute identifier")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # Dispute classification
    dispute_type: Optional[DisputeType] = None
    status: DisputeStatus = Field(default=DisputeStatus.DRAFT)
    
    # Parties
    msme_party: Optional[Party] = None
    buyer_party: Optional[Party] = None
    
    # Financial details
    dispute_amount: Optional[float] = Field(None, ge=0, description="Amount in dispute (INR)")
    invoice_amount: Optional[float] = Field(None, ge=0, description="Original invoice amount")
    invoice_number: Optional[str] = None
    invoice_date: Optional[datetime] = None
    payment_due_date: Optional[datetime] = None
    days_delayed: Optional[int] = Field(None, ge=0, description="Days since payment was due")
    
    # Documents
    documents: List[Document] = Field(default_factory=list)
    
    # Eligibility and validation
    is_eligible: Optional[bool] = None
    eligibility_errors: List[str] = Field(default_factory=list)
    validation_errors: List[str] = Field(default_factory=list)
    readiness_score: Optional[float] = Field(None, ge=0, le=100, description="Completeness score 0-100")
    
    # Legal context
    legal_basis: Optional[str] = Field(None, description="Plain-language explanation of legal position")
    applicable_rules: List[str] = Field(default_factory=list, description="MSMED Act rules applicable")
    
    # Additional context
    description: Optional[str] = Field(None, description="MSME's description of the dispute")
    language: str = Field(default="en", description="Language used for intake")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @validator('dispute_amount', 'invoice_amount', always=True)
    def validate_amounts(cls, v, values):
        """Ensure amounts are positive if provided"""
        if v is not None and v < 0:
            raise ValueError("Amounts must be non-negative")
        return v
    
    def get_mandatory_documents(self) -> List[str]:
        """Get list of mandatory document names based on dispute type"""
        # This will be populated from policy configuration
        # For now, return common mandatory docs
        mandatory = ["invoice", "msme_registration"]
        if self.dispute_type == DisputeType.PAYMENT_DELAY:
            mandatory.append("delivery_proof")
        elif self.dispute_type == DisputeType.PARTIAL_PAYMENT:
            mandatory.extend(["delivery_proof", "payment_proof"])
        elif self.dispute_type == DisputeType.QUALITY_DISPUTE:
            mandatory.extend(["delivery_proof", "purchase_order"])
        return mandatory
    
    def has_all_mandatory_documents(self) -> bool:
        """Check if all mandatory documents are present"""
        required = self.get_mandatory_documents()
        provided = {doc.name for doc in self.documents if doc.is_verified}
        return set(required).issubset(provided)
    
    def can_submit(self) -> tuple[bool, List[str]]:
        """
        Check if dispute can be submitted
        Returns (can_submit, list_of_blocking_errors)
        """
        errors = []
        
        # Check basic required fields
        if not self.dispute_type:
            errors.append("Dispute type must be selected")
        if not self.msme_party:
            errors.append("MSME party information is required")
        if not self.buyer_party:
            errors.append("Buyer party information is required")
        if not self.dispute_amount or self.dispute_amount <= 0:
            errors.append("Valid dispute amount is required")
        if not self.invoice_number:
            errors.append("Invoice number is required")
        if not self.invoice_date:
            errors.append("Invoice date is required")
        
        # Check mandatory documents
        if not self.has_all_mandatory_documents():
            missing = set(self.get_mandatory_documents()) - {doc.name for doc in self.documents if doc.is_verified}
            errors.append(f"Missing mandatory documents: {', '.join(missing)}")
        
        # Check eligibility
        if self.is_eligible is False:
            errors.extend(self.eligibility_errors)
        
        return len(errors) == 0, errors

