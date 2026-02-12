"""
Speech-to-text controller for handling audio transcription.
Integrates OpenAI Whisper API with database storage.
Uses the conversations/messages schema for chat integration.
"""

from dotenv import load_dotenv
import os
from openai import OpenAI
from fastapi import HTTPException, File, UploadFile

from api.daos.conversation_dao import MessageDAO
from api.models.conversation import (
    MessageCreate,
    MessageType,
    MessageRole,
    VoiceMessageResponse,
)


class SpeechToTextController:
    """Controller for speech-to-text transcription operations."""

    ALLOWED_CONTENT_TYPES = [
        "audio/wav",
        "audio/mp3",
        "audio/webm",
        "audio/mpeg",
        "audio/mp4",
        "audio/m4a",
    ]

    def __init__(self):
        """Initialize controller with API credentials and DAOs."""
        load_dotenv()
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.max_file_size = int(os.getenv("MAX_FILE_SIZE", 10 * 1024 * 1024))
        self.message_dao = MessageDAO()

    def transcribe_for_chat(
        self,
        file: UploadFile = File(...),
        conversation_id: str = None,
        language: str = None,
    ) -> VoiceMessageResponse:
        """
        Transcribe audio file and save to messages table.
        This is the main method for chat-based voice messages.

        Args:
            file: Uploaded audio file
            conversation_id: Conversation ID (e.g., "conv_1769865449664_icv7di7ih")
            language: Language hint for Whisper (e.g., "en", "hi", "kn")

        Returns:
            VoiceMessageResponse: Contains transcription text and message record

        Raises:
            HTTPException: If file validation fails, transcription fails, or database save fails
        """
        if not conversation_id:
            raise HTTPException(
                status_code=400,
                detail="conversation_id is required for chat transcription",
            )

        # Validate file type
        if file.content_type not in self.ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file.content_type}. "
                f"Allowed types: {', '.join(self.ALLOWED_CONTENT_TYPES)}",
            )

        # Validate file size
        if file.size > self.max_file_size:
            max_size_mb = self.max_file_size / (1024 * 1024)
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {max_size_mb}MB",
            )

        # Transcribe with OpenAI Whisper
        transcription_result = self._call_openai_whisper(file, language)

        # Save to messages table
        try:
            message_create = MessageCreate(
                conversation_id=conversation_id,
                message_type=MessageType.USER_VOICE,
                role=MessageRole.USER,
                content=transcription_result["text"],
                transcription_text=transcription_result["text"],
                audio_filename=file.filename,
                audio_file_size_bytes=file.size,
                audio_content_type=file.content_type,
                transcription_model="whisper-1",
                detected_language=transcription_result.get("language", language or "en"),
            )

            message_record = self.message_dao.create_message(message_create)

            return VoiceMessageResponse(
                text=transcription_result["text"],
                message=message_record,
            )

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save voice message to database: {str(e)}",
            )

    def _call_openai_whisper(self, file: UploadFile, language: str = None) -> dict:
        """
        Call OpenAI Whisper API for transcription.

        Args:
            file: Audio file to transcribe
            language: Optional language hint (ISO 639-1 code: en, hi, kn, ta)

        Returns:
            dict: Response containing "text" and optionally "language"

        Raises:
            HTTPException: If API call fails
        """
        try:
            # Reset file pointer to beginning
            file.file.seek(0)

            # Prepare transcription parameters
            transcribe_params = {
                "model": "whisper-1",
                "file": (file.filename, file.file, file.content_type),
            }

            # Add language hint if provided
            if language:
                transcribe_params["language"] = language

                # Add script prompt to guide Whisper to use correct script
                # This helps prevent Kannada being transcribed in Devanagari
                if language == "kn":
                    transcribe_params["prompt"] = "ನನಗೆ ಕನ್ನಡ ಗೊತ್ತಿದೆ"  # "I know Kannada" in Kannada script
                elif language == "hi":
                    transcribe_params["prompt"] = "मुझे हिंदी आती है"  # "I know Hindi" in Devanagari

            # Call OpenAI Whisper
            transcript = self.openai_client.audio.transcriptions.create(**transcribe_params)

            return {
                "text": transcript.text,
                "language": language  # OpenAI doesn't return detected language, use provided
            }

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"OpenAI Whisper transcription failed: {str(e)}",
            )
