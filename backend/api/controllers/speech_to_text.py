"""
Speech-to-text controller for handling audio transcription.
Integrates Groq Whisper API with database storage.
"""

from dotenv import load_dotenv
import os
import requests
from typing import Optional
from fastapi import HTTPException, File, UploadFile

from api.daos.transcription_dao import TranscriptionDAO
from api.models.transcription import TranscriptionCreate, TranscriptionWithTextResponse


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
        """Initialize controller with API credentials and DAO."""
        load_dotenv()
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.max_file_size = int(os.getenv("MAX_FILE_SIZE", 10 * 1024 * 1024))
        self.transcription_dao = TranscriptionDAO()

    def transcribe(
        self,
        file: UploadFile = File(...),
        claim_id: Optional[str] = None,
    ) -> TranscriptionWithTextResponse:
        """
        Transcribe audio file and save to database.

        Args:
            file: Uploaded audio file
            claim_id: Optional claim ID to associate with transcription

        Returns:
            TranscriptionWithTextResponse: Contains transcription text and database record

        Raises:
            HTTPException: If file validation fails, transcription fails, or database save fails
        """
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

        # Transcribe with Groq Whisper
        transcription_text = self._call_groq_api(file)

        # Save to database
        try:
            transcription_create = TranscriptionCreate(
                claim_id=claim_id,
                transcription_text=transcription_text,
                audio_file_name=file.filename,
                audio_file_size=file.size,
                audio_content_type=file.content_type,
                model_used="whisper-large-v3-turbo",
            )

            db_record = self.transcription_dao.create_transcription(transcription_create)

            return TranscriptionWithTextResponse(
                text=transcription_text,
                record=db_record,
            )

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save transcription to database: {str(e)}",
            )

    def _call_groq_api(self, file: UploadFile) -> str:
        """
        Call Groq Whisper API for transcription.

        Args:
            file: Audio file to transcribe

        Returns:
            str: Transcribed text

        Raises:
            HTTPException: If API call fails
        """
        url = "https://api.groq.com/openai/v1/audio/transcriptions"

        headers = {"Authorization": f"Bearer {self.groq_api_key}"}

        data = {"model": "whisper-large-v3-turbo"}

        files = {"file": (file.filename, file.file, file.content_type)}

        try:
            response = requests.post(url, headers=headers, data=data, files=files)
            response.raise_for_status()
            result = response.json()

            # Extract text from Groq response
            if "text" not in result:
                raise HTTPException(
                    status_code=500,
                    detail="Invalid response from transcription API",
                )

            return result["text"]

        except requests.exceptions.RequestException as e:
            error_detail = str(e)
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_detail = e.response.json()
                except Exception:
                    error_detail = e.response.text or str(e)

            raise HTTPException(
                status_code=500,
                detail=f"Transcription API failed: {error_detail}",
            )