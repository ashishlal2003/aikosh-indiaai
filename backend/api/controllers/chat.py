"""
Chat controller for handling conversational AI interactions.
Now integrated with the new conversations/messages schema.
Uses Tesseract OCR for document text extraction.
"""

import os
import tempfile
from typing import List, Dict, Optional
from fastapi import HTTPException, File, UploadFile
from pydantic import BaseModel

from api.services.conversation_service import ConversationService
from api.services.ocr_service import get_ocr_service
from api.daos.conversation_dao import ConversationDAO, MessageDAO
from api.daos.document_dao import DocumentDAO
from api.models.conversation import (
    MessageCreate,
    MessageType,
    MessageRole,
)
from api.models.document import (
    DisputeDocumentCreate,
    DocumentType,
)


class ChatMessage(BaseModel):
    """Chat message model."""
    role: str
    content: str


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    conversation_id: str
    messages: List[ChatMessage]
    message_type: Optional[str] = "text"


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str
    actions: List[Dict[str, str]] = []
    conversation_id: str


class DocumentUploadResponse(BaseModel):
    """Response model for document upload."""
    extracted_data: str
    file_name: str
    conversation_id: str


class ChatController:
    """Controller for chat operations."""

    def __init__(self):
        """Initialize controller with conversation service, OCR service, and DAOs."""
        self.conversation_service = ConversationService()
        self.ocr_service = get_ocr_service()
        self.conversation_dao = ConversationDAO()
        self.message_dao = MessageDAO()
        self.document_dao = DocumentDAO()

    def process_chat_message(self, request: ChatRequest) -> ChatResponse:
        """
        Process chat message and get AI response.
        Saves both user message and AI response to the database.

        Args:
            request: ChatRequest with conversation history

        Returns:
            ChatResponse with AI's response and actions

        Raises:
            HTTPException: If processing fails
        """
        try:
            # Ensure conversation exists (get or create)
            self.conversation_dao.get_or_create_conversation(request.conversation_id)

            # Convert Pydantic models to dicts
            messages_dict = [
                {"role": msg.role, "content": msg.content}
                for msg in request.messages
            ]

            # Save the latest user message to database (if it's a text message)
            if request.message_type == "text" and len(request.messages) > 0:
                latest_message = request.messages[-1]
                if latest_message.role == "user":
                    user_message = MessageCreate(
                        conversation_id=request.conversation_id,
                        message_type=MessageType.USER_TEXT,
                        role=MessageRole.USER,
                        content=latest_message.content,
                    )
                    self.message_dao.create_message(user_message)

            # Get AI response
            result = self.conversation_service.get_ai_response(
                messages=messages_dict,
                conversation_id=request.conversation_id,
                message_type=request.message_type
            )

            # Save AI response to database
            ai_message = MessageCreate(
                conversation_id=request.conversation_id,
                message_type=MessageType.AI_RESPONSE,
                role=MessageRole.ASSISTANT,
                content=result["response"],
                metadata={"actions": result["actions"]},
            )
            self.message_dao.create_message(ai_message)

            return ChatResponse(
                response=result["response"],
                actions=result["actions"],
                conversation_id=result["conversation_id"]
            )

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error processing chat message: {str(e)}"
            )

    def upload_document(
        self,
        file: UploadFile,
        conversation_id: str
    ) -> DocumentUploadResponse:
        """
        Upload and process document in chat context.
        Uses Tesseract OCR for text extraction.

        Args:
            file: Uploaded file
            conversation_id: Conversation identifier

        Returns:
            DocumentUploadResponse with extracted data

        Raises:
            HTTPException: If upload/processing fails
        """
        try:
            # Validate file type
            allowed_types = [
                "application/pdf",
                "image/jpeg",
                "image/jpg",
                "image/png",
                "application/msword",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ]

            if file.content_type not in allowed_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type: {file.content_type}"
                )

            # Ensure conversation exists
            self.conversation_dao.get_or_create_conversation(conversation_id)

            # Save file temporarily for OCR processing
            suffix = os.path.splitext(file.filename)[1] if file.filename else ".tmp"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                content = file.file.read()
                tmp_file.write(content)
                tmp_path = tmp_file.name

            try:
                # TBD make this better rather than just filename matching
                # Detect document type from filename
                filename_lower = file.filename.lower() if file.filename else ""
                if "invoice" in filename_lower or "bill" in filename_lower:
                    doc_type = DocumentType.INVOICE
                elif "po" in filename_lower or "purchase" in filename_lower:
                    doc_type = DocumentType.PURCHASE_ORDER
                elif "delivery" in filename_lower or "receipt" in filename_lower:
                    doc_type = DocumentType.DELIVERY_PROOF
                elif "udyam" in filename_lower or "msme" in filename_lower or "certificate" in filename_lower:
                    doc_type = DocumentType.MSME_CERTIFICATE
                elif "email" in filename_lower or "communication" in filename_lower:
                    doc_type = DocumentType.COMMUNICATION
                elif "bank" in filename_lower or "statement" in filename_lower:
                    doc_type = DocumentType.BANK_STATEMENT
                elif "notice" in filename_lower or "legal" in filename_lower:
                    doc_type = DocumentType.LEGAL_NOTICE
                else:
                    doc_type = DocumentType.INVOICE  # Default to invoice for MSME use case

                # Process document with OCR service
                extracted_result = self.ocr_service.process_document(
                    file_path=tmp_path,
                    file_type=file.content_type,
                    document_type=doc_type.value
                )

                # Get raw OCR text if available
                raw_ocr_text = extracted_result.get("raw_text", "")

                # Format for chat display
                extracted_data = self.ocr_service.format_for_chat(extracted_result)

                # Get conversation UUID for foreign key
                conversation = self.conversation_dao.get_or_create_conversation(conversation_id)

                # Save to dispute_documents table for officer review
                dispute_doc = DisputeDocumentCreate(
                    conversation_id=conversation.id,
                    document_type=doc_type,
                    original_filename=file.filename or "unknown",
                    file_size_bytes=len(content),
                    content_type=file.content_type,
                    extracted_data=extracted_result,
                    raw_ocr_text=raw_ocr_text,
                    metadata={"source": "chat_upload"},
                )
                self.document_dao.create_document(dispute_doc)

                # Save document upload as a message (for chat history)
                doc_message = MessageCreate(
                    conversation_id=conversation_id,
                    message_type=MessageType.DOCUMENT,
                    role=MessageRole.USER,
                    content=f"[Uploaded document: {file.filename}]",
                    document_filename=file.filename,
                    document_type=doc_type.value,
                    metadata={
                        "file_type": file.content_type,
                        "extracted_data": extracted_result
                    },
                )
                self.message_dao.create_message(doc_message)

            finally:
                # Clean up temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

            return DocumentUploadResponse(
                extracted_data=extracted_data,
                file_name=file.filename,
                conversation_id=conversation_id
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error uploading document: {str(e)}"
            )

    def summarize_conversation(
        self,
        conversation_id: str,
        messages: List[ChatMessage]
    ) -> Dict[str, any]:
        """
        Summarize conversation and extract claim details.

        Args:
            conversation_id: Conversation identifier
            messages: List of conversation messages

        Returns:
            Summary dictionary

        Raises:
            HTTPException: If summarization fails
        """
        try:
            messages_dict = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]

            result = self.conversation_service.summarize_conversation(messages_dict)

            return {
                "conversation_id": conversation_id,
                **result
            }

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error summarizing conversation: {str(e)}"
            )
