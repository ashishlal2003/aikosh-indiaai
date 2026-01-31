"""
Chat routes for conversational AI interface.
"""

from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from typing import Optional, List

from api.controllers.chat import (
    ChatController,
    ChatRequest,
    ChatResponse,
    DocumentUploadResponse
)
from api.models.conversation import (
    ConversationResponse,
    MessageResponse,
    ConversationWithMessages,
)
from api.daos.conversation_dao import ConversationDAO, MessageDAO

router = APIRouter()
chat_controller = ChatController()
conversation_dao = ConversationDAO()
message_dao = MessageDAO()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process chat message and get AI response.

    Args:
        request: ChatRequest with conversation history

    Returns:
        ChatResponse with AI's response and actions
    """
    return chat_controller.process_chat_message(request)


@router.post("/chat/upload-document", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    conversation_id: str = Form(...)
):
    """
    Upload and process document during chat.

    Args:
        file: Document file to upload
        conversation_id: Conversation identifier

    Returns:
        DocumentUploadResponse with extracted data
    """
    return chat_controller.upload_document(file, conversation_id)


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str):
    """
    Get conversation details by conversation_id.

    Args:
        conversation_id: The conversation identifier

    Returns:
        ConversationResponse with conversation details
    """
    conversation = conversation_dao.get_conversation_by_conversation_id(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(conversation_id: str):
    """
    Get all messages for a conversation.

    Args:
        conversation_id: The conversation identifier

    Returns:
        List of MessageResponse objects ordered by creation time
    """
    messages = message_dao.get_messages_by_conversation(conversation_id)
    return messages


@router.get("/conversations/{conversation_id}/full", response_model=ConversationWithMessages)
async def get_conversation_with_messages(conversation_id: str):
    """
    Get conversation with all its messages.

    Args:
        conversation_id: The conversation identifier

    Returns:
        ConversationWithMessages containing conversation and all messages
    """
    result = message_dao.get_conversation_with_messages(conversation_id)
    if not result:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return result
