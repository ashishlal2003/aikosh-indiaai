"""
Pydantic models for conversations and messages.
Supports text, voice, and document messages in a unified schema.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class ConversationStatus(str, Enum):
    """Conversation status values."""
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class MessageType(str, Enum):
    """Message type values."""
    USER_TEXT = "user_text"
    USER_VOICE = "user_voice"
    AI_RESPONSE = "ai_response"
    DOCUMENT = "document"
    ACTION = "action"
    SYSTEM = "system"


class MessageRole(str, Enum):
    """Message role values."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


# ============================================================================
# CONVERSATION MODELS
# ============================================================================

class ConversationCreate(BaseModel):
    """Model for creating a new conversation."""
    conversation_id: str = Field(..., description="Frontend-friendly conversation ID")
    user_session_id: Optional[str] = Field(None, description="Optional session tracking ID")
    status: ConversationStatus = Field(
        default=ConversationStatus.ACTIVE,
        description="Conversation status"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional metadata"
    )


class ConversationUpdate(BaseModel):
    """Model for updating a conversation."""
    status: Optional[ConversationStatus] = None
    claim_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ConversationResponse(BaseModel):
    """Model for conversation response."""
    id: str = Field(..., description="Database UUID")
    conversation_id: str = Field(..., description="Frontend-friendly ID")
    user_session_id: Optional[str] = Field(None, description="Session tracking ID")
    status: str = Field(..., description="Conversation status")
    claim_id: Optional[str] = Field(None, description="Linked claim ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_message_at: datetime = Field(..., description="Last message timestamp")

    class Config:
        from_attributes = True


# ============================================================================
# MESSAGE MODELS
# ============================================================================

class MessageCreate(BaseModel):
    """Model for creating a new message."""
    conversation_id: str = Field(..., description="Conversation UUID or conversation_id")
    message_type: MessageType = Field(..., description="Type of message")
    content: Optional[str] = Field(None, description="Message content")
    role: MessageRole = Field(..., description="Message role")

    # Voice message fields
    audio_file_url: Optional[str] = Field(None, description="URL to audio file")
    transcription_text: Optional[str] = Field(None, description="Transcribed text")
    detected_language: Optional[str] = Field(None, description="Detected language code")
    audio_duration_seconds: Optional[int] = Field(None, description="Audio duration")
    audio_filename: Optional[str] = Field(None, description="Audio filename")
    audio_file_size_bytes: Optional[int] = Field(None, description="Audio file size")
    audio_content_type: Optional[str] = Field(None, description="Audio MIME type")
    transcription_model: Optional[str] = Field(None, description="Transcription model used")

    # Document message fields
    document_id: Optional[str] = Field(None, description="Document UUID")
    document_filename: Optional[str] = Field(None, description="Document filename")
    document_type: Optional[str] = Field(None, description="Document type")

    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional metadata"
    )


class MessageResponse(BaseModel):
    """Model for message response."""
    id: str = Field(..., description="Message UUID")
    conversation_id: str = Field(..., description="Conversation UUID")
    message_type: str = Field(..., description="Type of message")
    content: Optional[str] = Field(None, description="Message content")
    role: str = Field(..., description="Message role")

    # Voice message fields
    audio_file_url: Optional[str] = Field(None, description="URL to audio file")
    transcription_text: Optional[str] = Field(None, description="Transcribed text")
    detected_language: Optional[str] = Field(None, description="Detected language code")
    audio_duration_seconds: Optional[int] = Field(None, description="Audio duration")
    audio_filename: Optional[str] = Field(None, description="Audio filename")
    audio_file_size_bytes: Optional[int] = Field(None, description="Audio file size")
    audio_content_type: Optional[str] = Field(None, description="Audio MIME type")
    transcription_model: Optional[str] = Field(None, description="Transcription model used")

    # Document message fields
    document_id: Optional[str] = Field(None, description="Document UUID")
    document_filename: Optional[str] = Field(None, description="Document filename")
    document_type: Optional[str] = Field(None, description="Document type")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    processed_at: Optional[datetime] = Field(None, description="Processing timestamp")

    class Config:
        from_attributes = True


# ============================================================================
# VOICE MESSAGE SPECIFIC MODELS
# ============================================================================

class VoiceMessageCreate(BaseModel):
    """Specialized model for creating voice messages."""
    conversation_id: str = Field(..., description="Conversation ID")
    transcription_text: str = Field(..., description="Transcribed text")
    audio_filename: str = Field(..., description="Audio filename")
    audio_file_size_bytes: int = Field(..., description="Audio file size")
    audio_content_type: str = Field(..., description="Audio MIME type")
    audio_file_url: Optional[str] = Field(None, description="URL to stored audio")
    detected_language: Optional[str] = Field("en", description="Detected language")
    audio_duration_seconds: Optional[int] = Field(None, description="Audio duration")
    transcription_model: str = Field(
        default="whisper-large-v3-turbo",
        description="Transcription model"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional metadata"
    )


class VoiceMessageResponse(BaseModel):
    """Response model for voice message with transcription."""
    text: str = Field(..., description="Transcribed text")
    message: MessageResponse = Field(..., description="Full message record")


# ============================================================================
# CONVERSATION SUMMARY MODELS
# ============================================================================

class ConversationSummary(BaseModel):
    """Summary of a conversation with message count."""
    conversation: ConversationResponse
    message_count: int
    first_message_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None


class ConversationWithMessages(BaseModel):
    """Conversation with all its messages."""
    conversation: ConversationResponse
    messages: list[MessageResponse]
