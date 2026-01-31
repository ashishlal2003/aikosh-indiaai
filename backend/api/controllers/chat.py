"""
Chat controller for handling conversational AI interactions.
Now integrated with the new conversations/messages schema.
"""

from typing import List, Dict, Optional
from fastapi import HTTPException, File, UploadFile
from pydantic import BaseModel

from api.services.conversation_service import ConversationService
from api.daos.conversation_dao import ConversationDAO, MessageDAO
from api.models.conversation import (
    MessageCreate,
    MessageType,
    MessageRole,
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
        """Initialize controller with conversation service and DAOs."""
        self.conversation_service = ConversationService()
        self.conversation_dao = ConversationDAO()
        self.message_dao = MessageDAO()

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

            # For MVP, return placeholder extraction
            # TODO: Implement actual OCR/document processing
            extracted_data = self._extract_document_data(file)

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

    def _extract_document_data(self, file: UploadFile) -> str:
        """
        Extract data from uploaded document.
        Placeholder implementation for MVP.

        Args:
            file: Uploaded file

        Returns:
            Extracted data as string
        """
        # Placeholder for OCR/document processing
        # In production, this would use PaddleOCR or similar

        file_type = file.content_type
        file_name = file.filename

        # Return mock extraction based on file type
        if "pdf" in file_type.lower():
            return f"""Document: {file_name}
Type: Invoice/Document (PDF)
Status: Uploaded successfully

Note: OCR processing will be implemented to extract:
- Invoice number
- Date
- Amount
- Party details
- Payment terms"""

        elif "image" in file_type.lower():
            return f"""Document: {file_name}
Type: Image/Scan
Status: Uploaded successfully

Note: Image processing will extract text and key details."""

        else:
            return f"""Document: {file_name}
Status: Uploaded successfully

Note: Document processing in progress."""

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
