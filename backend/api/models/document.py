"""
Pydantic models for dispute documents.
Used for officer review workflow and document verification.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class DocumentType(str, Enum):
    """Types of documents required for MSME dispute claims."""
    INVOICE = "invoice"
    PURCHASE_ORDER = "purchase_order"
    DELIVERY_PROOF = "delivery_proof"
    MSME_CERTIFICATE = "msme_certificate"
    COMMUNICATION = "communication"
    BANK_STATEMENT = "bank_statement"
    LEGAL_NOTICE = "legal_notice"
    OTHER = "other"


class VerificationStatus(str, Enum):
    """Document verification status for officer review."""
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    NEEDS_CLARIFICATION = "needs_clarification"


class DisputeDocumentCreate(BaseModel):
    """Model for creating a new dispute document record."""
    conversation_id: str = Field(..., description="Conversation UUID")
    document_type: DocumentType = Field(
        default=DocumentType.OTHER,
        description="Type of document"
    )
    original_filename: str = Field(..., description="Original uploaded filename")
    file_url: Optional[str] = Field(None, description="Storage URL if uploaded")
    file_size_bytes: Optional[int] = Field(None, description="File size in bytes")
    content_type: Optional[str] = Field(None, description="MIME type")
    extracted_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured data from LLM extraction"
    )
    raw_ocr_text: Optional[str] = Field(None, description="Raw OCR text")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional metadata"
    )


class DisputeDocumentUpdate(BaseModel):
    """Model for updating a dispute document (officer review)."""
    verification_status: Optional[VerificationStatus] = None
    officer_notes: Optional[str] = None
    verified_by: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class DisputeDocumentResponse(BaseModel):
    """Response model for dispute document."""
    id: str = Field(..., description="Document UUID")
    conversation_id: str = Field(..., description="Linked conversation UUID")
    document_type: str = Field(..., description="Type of document")
    original_filename: str = Field(..., description="Original filename")
    file_url: Optional[str] = Field(None, description="Storage URL")
    file_size_bytes: Optional[int] = Field(None, description="File size")
    content_type: Optional[str] = Field(None, description="MIME type")
    extracted_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extracted structured data"
    )
    raw_ocr_text: Optional[str] = Field(None, description="Raw OCR text")
    verification_status: str = Field(
        default="pending",
        description="Verification status"
    )
    officer_notes: Optional[str] = Field(None, description="Officer notes")
    verified_by: Optional[str] = Field(None, description="Verifying officer")
    verified_at: Optional[datetime] = Field(None, description="Verification time")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(..., description="Upload timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class DocumentCompleteness(BaseModel):
    """Model for document completeness check result."""
    conversation_id: str
    total_required: int = Field(default=4, description="Total required doc types")
    uploaded_count: int = Field(default=0, description="Number uploaded")
    completeness_percentage: float = Field(default=0.0, description="Completion % based on verified docs")
    uploaded_types: list[str] = Field(default_factory=list)
    missing_types: list[str] = Field(default_factory=list)
    verified_count: int = Field(default=0, description="Verified documents")
    status_summary: Dict[str, int] = Field(
        default_factory=dict,
        description="Count by verification status"
    )
    per_document: Dict[str, str] = Field(
        default_factory=dict,
        description="Status per required document type: verified/pending/rejected/missing"
    )


# Document requirements for MSME disputes
REQUIRED_DOCUMENT_TYPES = [
    DocumentType.INVOICE,
    DocumentType.PURCHASE_ORDER,
    DocumentType.DELIVERY_PROOF,
    DocumentType.MSME_CERTIFICATE,
]

OPTIONAL_DOCUMENT_TYPES = [
    DocumentType.COMMUNICATION,  # Helpful but not mandatory
    DocumentType.BANK_STATEMENT,
    DocumentType.LEGAL_NOTICE,
    DocumentType.OTHER,
]
