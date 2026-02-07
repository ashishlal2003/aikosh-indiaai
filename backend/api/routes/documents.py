"""
Document routes for officer review and document management.
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional

from api.daos.document_dao import DocumentDAO
from api.models.document import (
    DisputeDocumentResponse,
    DisputeDocumentUpdate,
    DocumentCompleteness,
    VerificationStatus,
)

router = APIRouter()
document_dao = DocumentDAO()


@router.get("/documents/conversation/{conversation_id}", response_model=List[DisputeDocumentResponse])
async def get_documents_by_conversation(conversation_id: str):
    """
    Get all documents for a conversation.

    Args:
        conversation_id: The conversation identifier

    Returns:
        List of DisputeDocumentResponse objects
    """
    documents = document_dao.get_documents_by_conversation(conversation_id)
    return documents


@router.get("/documents/conversation/{conversation_id}/completeness", response_model=DocumentCompleteness)
async def get_document_completeness(conversation_id: str):
    """
    Check document completeness for a conversation.

    Args:
        conversation_id: The conversation identifier

    Returns:
        DocumentCompleteness with status of required documents
    """
    return document_dao.get_completeness(conversation_id)


@router.get("/documents/{document_id}", response_model=DisputeDocumentResponse)
async def get_document(document_id: str):
    """
    Get a specific document by ID.

    Args:
        document_id: The document UUID

    Returns:
        DisputeDocumentResponse if found
    """
    document = document_dao.get_document_by_id(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.patch("/documents/{document_id}", response_model=DisputeDocumentResponse)
async def update_document(document_id: str, update: DisputeDocumentUpdate):
    """
    Update a document (for officer review).

    Args:
        document_id: The document UUID
        update: Fields to update (verification_status, officer_notes, etc.)

    Returns:
        Updated DisputeDocumentResponse
    """
    document = document_dao.update_document(document_id, update)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.post("/documents/{document_id}/verify", response_model=DisputeDocumentResponse)
async def verify_document(
    document_id: str,
    officer_id: str,
    notes: Optional[str] = None
):
    """
    Quick verify a document.

    Args:
        document_id: The document UUID
        officer_id: ID of the reviewing officer
        notes: Optional verification notes

    Returns:
        Updated DisputeDocumentResponse
    """
    update = DisputeDocumentUpdate(
        verification_status=VerificationStatus.VERIFIED,
        verified_by=officer_id,
        officer_notes=notes,
    )
    document = document_dao.update_document(document_id, update)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.post("/documents/{document_id}/reject", response_model=DisputeDocumentResponse)
async def reject_document(
    document_id: str,
    officer_id: str,
    notes: str
):
    """
    Reject a document with reason.

    Args:
        document_id: The document UUID
        officer_id: ID of the reviewing officer
        notes: Rejection reason (required)

    Returns:
        Updated DisputeDocumentResponse
    """
    if not notes:
        raise HTTPException(status_code=400, detail="Rejection notes are required")

    update = DisputeDocumentUpdate(
        verification_status=VerificationStatus.REJECTED,
        verified_by=officer_id,
        officer_notes=notes,
    )
    document = document_dao.update_document(document_id, update)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.get("/documents/pending", response_model=List[DisputeDocumentResponse])
async def get_pending_documents(limit: int = 50):
    """
    Get all pending documents for officer review.

    Args:
        limit: Maximum number to return (default 50)

    Returns:
        List of pending DisputeDocumentResponse
    """
    return document_dao.get_pending_documents(limit)


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """
    Delete a document.

    Args:
        document_id: The document UUID

    Returns:
        Success message
    """
    success = document_dao.delete_document(document_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"message": "Document deleted successfully"}
