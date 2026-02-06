"""
Routes for speech-to-text transcription endpoints.
"""

from fastapi import APIRouter, File, UploadFile, Form
from api.controllers.speech_to_text import SpeechToTextController
from api.models.conversation import VoiceMessageResponse

router = APIRouter()
speech_to_text_controller = SpeechToTextController()


@router.post("/transcribe-chat", response_model=VoiceMessageResponse)
async def transcribe_chat(
    file: UploadFile = File(..., description="Audio file to transcribe"),
    conversation_id: str = Form(..., description="Conversation ID for the chat session"),
) -> VoiceMessageResponse:
    """
    Transcribe an audio file for chat and save to messages table.

    Args:
        file: Audio file (supported formats: WAV, MP3, WEBM, MPEG, MP4, M4A)
        conversation_id: Conversation ID to associate the voice message with

    Returns:
        VoiceMessageResponse containing the transcribed text and message record
    """
    return speech_to_text_controller.transcribe_for_chat(file, conversation_id)
