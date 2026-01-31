"""
Routes for speech-to-text transcription endpoints.
"""

from typing import Optional
from fastapi import APIRouter, File, UploadFile, Form
from api.controllers.speech_to_text import SpeechToTextController
from api.models.transcription import TranscriptionWithTextResponse

router = APIRouter()
speech_to_text_controller = SpeechToTextController()


@router.post("/transcribe", response_model=TranscriptionWithTextResponse)
async def transcribe(
    file: UploadFile = File(..., description="Audio file to transcribe"),
    claim_id: Optional[str] = Form(None, description="Optional claim ID to associate with transcription"),
) -> TranscriptionWithTextResponse:
    """
    Transcribe an audio file using Groq Whisper and save to database.

    Args:
        file: Audio file (supported formats: WAV, MP3, WEBM, MPEG, MP4, M4A)
        claim_id: Optional claim ID to link transcription to a specific claim

    Returns:
        TranscriptionWithTextResponse containing the transcribed text and database record
    """
    return speech_to_text_controller.transcribe(file, claim_id)