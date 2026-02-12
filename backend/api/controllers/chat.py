"""
Chat controller for handling conversational AI interactions.
Now integrated with the new conversations/messages schema.
Uses Tesseract OCR for document text extraction.
Supports agentic tool calling (email drafting, interest calculation).
"""

import logging
import os
import tempfile
import json
from typing import List, Dict, Optional, Any, AsyncGenerator
from fastapi import HTTPException, File, UploadFile
from pydantic import BaseModel

from api.services.conversation_service import ConversationService
from api.services.email_service import send_email
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

logger = logging.getLogger(__name__)


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
    email_draft: Optional[Dict[str, Any]] = None
    completeness: Optional[Dict[str, Any]] = None


class SendEmailRequest(BaseModel):
    """Request model for sending a drafted email."""
    conversation_id: str
    to_email: str
    subject: str
    body_html: str


class SendEmailResponse(BaseModel):
    """Response model for email send endpoint."""
    status: str
    message: str
    timestamp: Optional[str] = None


class DocumentUploadResponse(BaseModel):
    """Response model for document upload."""
    extracted_data: str
    file_name: str
    conversation_id: str
    completeness: Optional[Dict[str, Any]] = None


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

            # Build metadata for the saved message
            ai_metadata: Dict[str, Any] = {"actions": result["actions"]}
            if result.get("email_draft"):
                ai_metadata["email_draft"] = result["email_draft"]

            # Save AI response to database
            ai_message = MessageCreate(
                conversation_id=request.conversation_id,
                message_type=MessageType.AI_RESPONSE,
                role=MessageRole.ASSISTANT,
                content=result["response"],
                metadata=ai_metadata,
            )
            self.message_dao.create_message(ai_message)

            return ChatResponse(
                response=result["response"],
                actions=result["actions"],
                conversation_id=result["conversation_id"],
                email_draft=result.get("email_draft"),
                completeness=result.get("completeness"),
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

            # Fetch current completeness for progress bar update
            try:
                completeness = self.document_dao.get_completeness(conversation_id)
                completeness_data = completeness.model_dump()
            except Exception:
                completeness_data = None

            return DocumentUploadResponse(
                extracted_data=extracted_data,
                file_name=file.filename,
                conversation_id=conversation_id,
                completeness=completeness_data,
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

    def send_email_to_buyer(self, request: SendEmailRequest) -> SendEmailResponse:
        """
        Send a previously drafted email to the buyer.

        Called when the user clicks 'Send Email' after reviewing a draft.
        Logs the sent email as a message in the conversation.

        Args:
            request: SendEmailRequest with email details.

        Returns:
            SendEmailResponse with status.

        Raises:
            HTTPException: If sending fails.
        """
        try:
            self.conversation_dao.get_or_create_conversation(request.conversation_id)

            result = send_email(
                to_email=request.to_email,
                subject=request.subject,
                body_html=request.body_html,
                cc_user=True,
            )

            if result["status"] == "sent":
                # Log sent email as a message in the conversation
                email_message = MessageCreate(
                    conversation_id=request.conversation_id,
                    message_type=MessageType.ACTION,
                    role=MessageRole.SYSTEM,
                    content=f"[Email sent to {request.to_email}] Subject: {request.subject}",
                    metadata={
                        "action": "email_sent",
                        "to_email": request.to_email,
                        "subject": request.subject,
                        "timestamp": result["timestamp"],
                    },
                )
                self.message_dao.create_message(email_message)

                return SendEmailResponse(
                    status="sent",
                    message=f"Email sent successfully to {request.to_email}",
                    timestamp=result["timestamp"],
                )

            logger.error(f"Email send failed: {result.get('error')}")
            raise HTTPException(
                status_code=502,
                detail=result.get("error", "Failed to send email"),
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error sending email: {str(e)}",
            )

    async def process_chat_message_stream(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        """
        Process chat message and stream AI response token-by-token.

        Emits Server-Sent Events (SSE) in the following format:
        - event: tool_start, data: {"tool": "calculate_msme_interest", "args": {...}}
        - event: tool_end, data: {"tool": "calculate_msme_interest", "result": {...}}
        - event: message, data: {"content": "token"}
        - event: done, data: {"actions": [...], "email_draft": {...}, "completeness": {...}}

        Args:
            request: ChatRequest with conversation history

        Yields:
            SSE-formatted strings for streaming to client

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

            # Stream AI response
            full_response = ""
            email_draft = None
            completeness = None
            actions = []

            async for event in self.conversation_service.get_ai_response_stream(
                messages=messages_dict,
                conversation_id=request.conversation_id,
                message_type=request.message_type
            ):
                event_type = event.get("type")

                if event_type == "tool_start":
                    # Emit tool execution start
                    yield f"event: tool_start\ndata: {json.dumps(event['data'])}\n\n"

                elif event_type == "tool_end":
                    # Emit tool execution end
                    yield f"event: tool_end\ndata: {json.dumps(event['data'])}\n\n"

                    # Capture email draft if available
                    if event['data'].get('tool') == 'draft_demand_notice_email':
                        result = event['data'].get('result', {})
                        if isinstance(result, str):
                            try:
                                result = json.loads(result)
                            except:
                                pass
                        if isinstance(result, dict) and result.get('status') == 'drafted':
                            email_draft = result

                    # Capture completeness if available
                    if event['data'].get('tool') == 'verify_document':
                        result = event['data'].get('result', {})
                        if isinstance(result, str):
                            try:
                                result = json.loads(result)
                            except:
                                pass
                        if isinstance(result, dict):
                            completeness = result

                elif event_type == "content":
                    # Stream content token
                    token = event.get("content", "")
                    full_response += token
                    yield f"event: message\ndata: {json.dumps({'content': token})}\n\n"

                elif event_type == "done":
                    # Final event with metadata
                    actions = event.get("actions", [])

                    # If email was drafted, add send_email action
                    if email_draft and email_draft.get("status") == "drafted":
                        actions.append({"type": "send_email", "label": "Send Email"})

                    done_data = {
                        "actions": actions,
                        "conversation_id": request.conversation_id,
                    }
                    if email_draft:
                        done_data["email_draft"] = email_draft
                    if completeness:
                        done_data["completeness"] = completeness

                    yield f"event: done\ndata: {json.dumps(done_data)}\n\n"

            # Save AI response to database
            ai_metadata: Dict[str, Any] = {"actions": actions}
            if email_draft:
                ai_metadata["email_draft"] = email_draft

            ai_message = MessageCreate(
                conversation_id=request.conversation_id,
                message_type=MessageType.AI_RESPONSE,
                role=MessageRole.ASSISTANT,
                content=full_response,
                metadata=ai_metadata,
            )
            self.message_dao.create_message(ai_message)

        except Exception as e:
            logger.exception("Error in streaming chat")
            error_data = {"error": str(e)}
            yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
