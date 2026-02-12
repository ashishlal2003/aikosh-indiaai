"""
Data Access Object for dispute documents.
Handles all database operations for document storage and verification.
"""

from typing import List, Optional
from supabase import Client
from api.config.database import get_db
from api.models.document import (
    DisputeDocumentCreate,
    DisputeDocumentUpdate,
    DisputeDocumentResponse,
    DocumentCompleteness,
    DocumentType,
    VerificationStatus,
    REQUIRED_DOCUMENT_TYPES,
)
from api.daos.conversation_dao import ConversationDAO


class DocumentDAO:
    """Handles database operations for dispute_documents table."""

    def __init__(self, db_client: Optional[Client] = None):
        """Initialize DocumentDAO."""
        self.db = db_client or get_db()
        self.table_name = "dispute_documents"
        self.conversation_dao = ConversationDAO(db_client)

    def create_document(self, document: DisputeDocumentCreate) -> DisputeDocumentResponse:
        """
        Create a new dispute document record.

        Args:
            document: DisputeDocumentCreate model with document data

        Returns:
            DisputeDocumentResponse: The created document record
        """
        try:
            data = document.model_dump(exclude_none=False)

            # Ensure document_type is string for DB
            if isinstance(data.get("document_type"), DocumentType):
                data["document_type"] = data["document_type"].value

            response = self.db.table(self.table_name).insert(data).execute()

            if not response.data or len(response.data) == 0:
                raise Exception("Failed to create document record")

            return DisputeDocumentResponse(**response.data[0])

        except Exception as e:
            raise Exception(f"Database error while creating document: {str(e)}")

    def get_document_by_id(self, document_id: str) -> Optional[DisputeDocumentResponse]:
        """Retrieve a document by its ID."""
        try:
            response = (
                self.db.table(self.table_name)
                .select("*")
                .eq("id", document_id)
                .execute()
            )

            if response.data and len(response.data) > 0:
                return DisputeDocumentResponse(**response.data[0])

            return None

        except Exception as e:
            raise Exception(f"Database error while fetching document: {str(e)}")

    def get_documents_by_conversation(
        self, conversation_id: str
    ) -> List[DisputeDocumentResponse]:
        """
        Get all documents for a conversation.

        Args:
            conversation_id: The conversation_id or UUID

        Returns:
            List of DisputeDocumentResponse ordered by creation time
        """
        try:
            # Get conversation UUID if needed
            conversation = self.conversation_dao.get_conversation_by_conversation_id(
                conversation_id
            )

            if not conversation:
                conversation = self.conversation_dao.get_conversation_by_id(
                    conversation_id
                )

            if not conversation:
                return []

            response = (
                self.db.table(self.table_name)
                .select("*")
                .eq("conversation_id", conversation.id)
                .order("created_at", desc=False)
                .execute()
            )

            if response.data:
                return [DisputeDocumentResponse(**doc) for doc in response.data]

            return []

        except Exception as e:
            raise Exception(f"Database error while fetching documents: {str(e)}")

    def get_documents_by_type(
        self, conversation_id: str, document_type: str
    ) -> List[DisputeDocumentResponse]:
        """Get documents of a specific type for a conversation."""
        try:
            conversation = self.conversation_dao.get_conversation_by_conversation_id(
                conversation_id
            )

            if not conversation:
                conversation = self.conversation_dao.get_conversation_by_id(
                    conversation_id
                )

            if not conversation:
                return []

            response = (
                self.db.table(self.table_name)
                .select("*")
                .eq("conversation_id", conversation.id)
                .eq("document_type", document_type)
                .execute()
            )

            if response.data:
                return [DisputeDocumentResponse(**doc) for doc in response.data]

            return []

        except Exception as e:
            raise Exception(f"Database error while fetching documents by type: {str(e)}")

    def update_document(
        self, document_id: str, update: DisputeDocumentUpdate
    ) -> Optional[DisputeDocumentResponse]:
        """
        Update a document record (for officer review).

        Args:
            document_id: The document UUID
            update: DisputeDocumentUpdate with fields to update

        Returns:
            Updated DisputeDocumentResponse if found
        """
        try:
            data = update.model_dump(exclude_none=True)

            # Add verified_at timestamp if status is being set to verified
            if update.verification_status and update.verification_status.value == "verified":
                from datetime import datetime, timezone
                data["verified_at"] = datetime.now(timezone.utc).isoformat()

            response = (
                self.db.table(self.table_name)
                .update(data)
                .eq("id", document_id)
                .execute()
            )

            if response.data and len(response.data) > 0:
                return DisputeDocumentResponse(**response.data[0])

            return None

        except Exception as e:
            raise Exception(f"Database error while updating document: {str(e)}")

    def verify_document_by_type(
        self,
        conversation_id: str,
        document_type: str,
        verified: bool = True,
        notes: str = "",
    ) -> Optional[DisputeDocumentResponse]:
        """
        Find the most recent document of given type and update its verification status.

        Args:
            conversation_id: Conversation identifier
            document_type: DocumentType value string (e.g. "invoice")
            verified: True to verify, False to reject
            notes: Optional officer notes

        Returns:
            Updated DisputeDocumentResponse if found
        """
        try:
            docs = self.get_documents_by_type(conversation_id, document_type)
            if not docs:
                return None

            latest_doc = sorted(docs, key=lambda d: d.created_at, reverse=True)[0]
            status = VerificationStatus.VERIFIED if verified else VerificationStatus.REJECTED
            update = DisputeDocumentUpdate(
                verification_status=status,
                officer_notes=notes or None,
            )
            return self.update_document(latest_doc.id, update)

        except Exception as e:
            raise Exception(f"Error verifying document by type: {str(e)}")

    def get_completeness(self, conversation_id: str) -> DocumentCompleteness:
        """
        Check document completeness for a conversation.
        Completeness % is based on verified documents only.

        Args:
            conversation_id: The conversation_id or UUID

        Returns:
            DocumentCompleteness with status of required documents
        """
        try:
            documents = self.get_documents_by_conversation(conversation_id)

            # Track best status per doc type (verified > pending > rejected)
            status_priority = {"verified": 3, "needs_clarification": 2, "pending": 1, "rejected": 0}
            type_to_status: dict = {}
            status_summary = {"pending": 0, "verified": 0, "rejected": 0, "needs_clarification": 0}
            uploaded_types = set()
            verified_count = 0

            for doc in documents:
                dt = doc.document_type
                status = doc.verification_status
                uploaded_types.add(dt)
                if status in status_summary:
                    status_summary[status] += 1
                if status == "verified":
                    verified_count += 1
                # Keep the best status per type
                if dt not in type_to_status or status_priority.get(status, 0) > status_priority.get(type_to_status[dt], 0):
                    type_to_status[dt] = status

            # Build per-document status for all 5 required types
            required_type_values = [dt.value for dt in REQUIRED_DOCUMENT_TYPES]
            per_document = {req: type_to_status.get(req, "missing") for req in required_type_values}

            missing_types = [t for t in required_type_values if t not in uploaded_types]
            uploaded_list = [t for t in uploaded_types if t in required_type_values]

            total_required = len(required_type_values)
            uploaded_count = len(uploaded_list)
            # Percentage based on verified required docs only
            verified_required = sum(1 for t in required_type_values if type_to_status.get(t) == "verified")
            completeness_pct = (verified_required / total_required * 100) if total_required > 0 else 0

            return DocumentCompleteness(
                conversation_id=conversation_id,
                total_required=total_required,
                uploaded_count=uploaded_count,
                completeness_percentage=round(completeness_pct, 1),
                uploaded_types=list(uploaded_types),
                missing_types=missing_types,
                verified_count=verified_count,
                status_summary=status_summary,
                per_document=per_document,
            )

        except Exception as e:
            raise Exception(f"Error calculating completeness: {str(e)}")

    def get_pending_documents(self, limit: int = 50) -> List[DisputeDocumentResponse]:
        """
        Get all pending documents for officer review.

        Args:
            limit: Maximum number to return

        Returns:
            List of pending DisputeDocumentResponse
        """
        try:
            response = (
                self.db.table(self.table_name)
                .select("*")
                .eq("verification_status", "pending")
                .order("created_at", desc=False)
                .limit(limit)
                .execute()
            )

            if response.data:
                return [DisputeDocumentResponse(**doc) for doc in response.data]

            return []

        except Exception as e:
            raise Exception(f"Database error while fetching pending documents: {str(e)}")

    def delete_document(self, document_id: str) -> bool:
        """Delete a document by ID."""
        try:
            response = (
                self.db.table(self.table_name)
                .delete()
                .eq("id", document_id)
                .execute()
            )

            return response.data is not None and len(response.data) > 0

        except Exception as e:
            raise Exception(f"Database error while deleting document: {str(e)}")
