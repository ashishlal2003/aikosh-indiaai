"""
Data Access Object (DAO) for transcription operations.
Handles all database interactions for transcriptions table.
"""

from typing import List, Optional, Dict, Any
from supabase import Client
from api.config.database import get_db
from api.models.transcription import TranscriptionCreate, TranscriptionResponse


class TranscriptionDAO:
    """Handles database operations for transcriptions."""

    def __init__(self, db_client: Optional[Client] = None):
        """
        Initialize TranscriptionDAO.

        Args:
            db_client: Optional Supabase client. If not provided, uses default client.
        """
        self.db = db_client or get_db()
        self.table_name = "transcriptions"

    def create_transcription(self, transcription: TranscriptionCreate) -> TranscriptionResponse:
        """
        Create a new transcription record in the database.

        Args:
            transcription: TranscriptionCreate model with transcription data

        Returns:
            TranscriptionResponse: The created transcription record

        Raises:
            Exception: If database operation fails
        """
        try:
            # Convert Pydantic model to dict
            data = transcription.model_dump(exclude_none=False)

            # Insert into database
            response = self.db.table(self.table_name).insert(data).execute()

            if not response.data or len(response.data) == 0:
                raise Exception("Failed to create transcription record")

            # Return first record as TranscriptionResponse
            return TranscriptionResponse(**response.data[0])

        except Exception as e:
            raise Exception(f"Database error while creating transcription: {str(e)}")

    def get_transcription_by_id(self, transcription_id: str) -> Optional[TranscriptionResponse]:
        """
        Retrieve a transcription by its ID.

        Args:
            transcription_id: The ID of the transcription to retrieve

        Returns:
            TranscriptionResponse if found, None otherwise

        Raises:
            Exception: If database operation fails
        """
        try:
            response = self.db.table(self.table_name)\
                .select("*")\
                .eq("id", transcription_id)\
                .execute()

            if response.data and len(response.data) > 0:
                return TranscriptionResponse(**response.data[0])

            return None

        except Exception as e:
            raise Exception(f"Database error while fetching transcription: {str(e)}")

    def get_transcriptions_by_claim_id(self, claim_id: str) -> List[TranscriptionResponse]:
        """
        Retrieve all transcriptions for a specific claim.

        Args:
            claim_id: The claim ID to filter transcriptions

        Returns:
            List of TranscriptionResponse objects

        Raises:
            Exception: If database operation fails
        """
        try:
            response = self.db.table(self.table_name)\
                .select("*")\
                .eq("claim_id", claim_id)\
                .order("created_at", desc=True)\
                .execute()

            if response.data:
                return [TranscriptionResponse(**record) for record in response.data]

            return []

        except Exception as e:
            raise Exception(f"Database error while fetching transcriptions for claim: {str(e)}")

    def get_all_transcriptions(self, limit: int = 100, offset: int = 0) -> List[TranscriptionResponse]:
        """
        Retrieve all transcriptions with pagination.

        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of TranscriptionResponse objects

        Raises:
            Exception: If database operation fails
        """
        try:
            response = self.db.table(self.table_name)\
                .select("*")\
                .order("created_at", desc=True)\
                .limit(limit)\
                .offset(offset)\
                .execute()

            if response.data:
                return [TranscriptionResponse(**record) for record in response.data]

            return []

        except Exception as e:
            raise Exception(f"Database error while fetching all transcriptions: {str(e)}")
