"""
Routes for speech-to-text transcription endpoints.
"""

from typing import Optional
from fastapi import APIRouter, File, UploadFile, Form
from api.controllers.speech_to_text import SpeechToTextController
from api.models.transcription import TranscriptionWithTextResponse
from api.models.conversation import VoiceMessageResponse

router = APIRouter()
speech_to_text_controller = SpeechToTextController()


@router.post("/transcribe", response_model=TranscriptionWithTextResponse)
async def transcribe(
    file: UploadFile = File(..., description="Audio file to transcribe"),
    claim_id: Optional[str] = Form(None, description="Optional claim ID to associate with transcription"),
) -> TranscriptionWithTextResponse:
    """
    Transcribe an audio file using Groq Whisper and save to database (legacy endpoint).

    Args:
        file: Audio file (supported formats: WAV, MP3, WEBM, MPEG, MP4, M4A)
        claim_id: Optional claim ID to link transcription to a specific claim

    Returns:
        TranscriptionWithTextResponse containing the transcribed text and database record
    """
    return speech_to_text_controller.transcribe(file, claim_id)


@router.post("/transcribe-chat", response_model=VoiceMessageResponse)
async def transcribe_chat(
    file: UploadFile = File(..., description="Audio file to transcribe"),
    conversation_id: str = Form(..., description="Conversation ID for the chat session"),
) -> VoiceMessageResponse:
    """
    Transcribe an audio file for chat and save to messages table (new schema).
    This endpoint supports conversation IDs like "conv_1769865449664_icv7di7ih".

    Args:
        file: Audio file (supported formats: WAV, MP3, WEBM, MPEG, MP4, M4A)
        conversation_id: Conversation ID to associate the voice message with

    Returns:
        VoiceMessageResponse containing the transcribed text and message record
    """
    return speech_to_text_controller.transcribe_for_chat(file, conversation_id)