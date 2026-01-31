"""
Pydantic models for transcription request and response.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TranscriptionCreate(BaseModel):
    """Model for creating a new transcription record."""

    claim_id: Optional[str] = Field(None, description="Associated claim ID")
    transcription_text: str = Field(..., description="The transcribed text")
    audio_file_name: str = Field(..., description="Original audio file name")
    audio_file_size: int = Field(..., description="Audio file size in bytes")
    audio_content_type: str = Field(..., description="Audio file content type")
    language: Optional[str] = Field("en", description="Detected language code")
    duration: Optional[float] = Field(None, description="Audio duration in seconds")
    model_used: str = Field(default="whisper-large-v3-turbo", description="Transcription model used")


class TranscriptionResponse(BaseModel):
    """Model for transcription response."""

    id: str = Field(..., description="Transcription record ID")
    claim_id: Optional[str] = Field(None, description="Associated claim ID")
    transcription_text: str = Field(..., description="The transcribed text")
    audio_file_name: str = Field(..., description="Original audio file name")
    audio_file_size: int = Field(..., description="Audio file size in bytes")
    audio_content_type: str = Field(..., description="Audio file content type")
    language: Optional[str] = Field(None, description="Detected language code")
    duration: Optional[float] = Field(None, description="Audio duration in seconds")
    model_used: str = Field(..., description="Transcription model used")
    created_at: datetime = Field(..., description="Timestamp of creation")

    class Config:
        from_attributes = True


class TranscriptionWithTextResponse(BaseModel):
    """Combined response with transcription text and database record."""

    text: str = Field(..., description="Transcribed text")
    record: TranscriptionResponse = Field(..., description="Database record")
