"""
Data Access Object for conversations and messages.
Handles all database operations for the new conversation schema.
"""

from typing import List, Optional
from supabase import Client
from api.config.database import get_db
from api.models.conversation import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
    ConversationSummary,
    ConversationWithMessages,
)


class ConversationDAO:
    """Handles database operations for conversations table."""

    def __init__(self, db_client: Optional[Client] = None):
        """
        Initialize ConversationDAO.

        Args:
            db_client: Optional Supabase client. If not provided, uses default client.
        """
        self.db = db_client or get_db()
        self.table_name = "conversations"

    def create_conversation(self, conversation: ConversationCreate) -> ConversationResponse:
        """
        Create a new conversation record.

        Args:
            conversation: ConversationCreate model with conversation data

        Returns:
            ConversationResponse: The created conversation record

        Raises:
            Exception: If database operation fails
        """
        try:
            data = conversation.model_dump(exclude_none=False)

            response = self.db.table(self.table_name).insert(data).execute()

            if not response.data or len(response.data) == 0:
                raise Exception("Failed to create conversation record")

            return ConversationResponse(**response.data[0])

        except Exception as e:
            raise Exception(f"Database error while creating conversation: {str(e)}")

    def get_conversation_by_id(self, conversation_id: str) -> Optional[ConversationResponse]:
        """
        Retrieve a conversation by its database UUID.

        Args:
            conversation_id: The UUID of the conversation

        Returns:
            ConversationResponse if found, None otherwise

        Raises:
            Exception: If database operation fails
        """
        try:
            response = (
                self.db.table(self.table_name)
                .select("*")
                .eq("id", conversation_id)
                .execute()
            )

            if response.data and len(response.data) > 0:
                return ConversationResponse(**response.data[0])

            return None

        except Exception as e:
            raise Exception(f"Database error while fetching conversation: {str(e)}")

    def get_conversation_by_conversation_id(
        self, conversation_id: str
    ) -> Optional[ConversationResponse]:
        """
        Retrieve a conversation by its frontend conversation_id.

        Args:
            conversation_id: The conversation_id (e.g., "conv_123")

        Returns:
            ConversationResponse if found, None otherwise

        Raises:
            Exception: If database operation fails
        """
        try:
            response = (
                self.db.table(self.table_name)
                .select("*")
                .eq("conversation_id", conversation_id)
                .execute()
            )

            if response.data and len(response.data) > 0:
                return ConversationResponse(**response.data[0])

            return None

        except Exception as e:
            raise Exception(
                f"Database error while fetching conversation by conversation_id: {str(e)}"
            )

    def get_or_create_conversation(
        self, conversation_id: str, user_session_id: Optional[str] = None
    ) -> ConversationResponse:
        """
        Get existing conversation or create new one if it doesn't exist.

        Args:
            conversation_id: The conversation_id (e.g., "conv_123")
            user_session_id: Optional session tracking ID

        Returns:
            ConversationResponse: Existing or newly created conversation

        Raises:
            Exception: If database operation fails
        """
        # Try to get existing conversation
        existing = self.get_conversation_by_conversation_id(conversation_id)
        if existing:
            return existing

        # Create new conversation
        new_conversation = ConversationCreate(
            conversation_id=conversation_id,
            user_session_id=user_session_id,
            status="active",
        )
        return self.create_conversation(new_conversation)

    def update_conversation(
        self, conversation_id: str, update: ConversationUpdate
    ) -> Optional[ConversationResponse]:
        """
        Update a conversation record.

        Args:
            conversation_id: The database UUID or conversation_id
            update: ConversationUpdate model with fields to update

        Returns:
            ConversationResponse if updated, None if not found

        Raises:
            Exception: If database operation fails
        """
        try:
            data = update.model_dump(exclude_none=True)

            # Try updating by conversation_id first (more common in frontend)
            response = (
                self.db.table(self.table_name)
                .update(data)
                .eq("conversation_id", conversation_id)
                .execute()
            )

            # If no match, try by UUID
            if not response.data or len(response.data) == 0:
                response = (
                    self.db.table(self.table_name)
                    .update(data)
                    .eq("id", conversation_id)
                    .execute()
                )

            if response.data and len(response.data) > 0:
                return ConversationResponse(**response.data[0])

            return None

        except Exception as e:
            raise Exception(f"Database error while updating conversation: {str(e)}")

    def get_conversations_by_status(
        self, status: str, limit: int = 50
    ) -> List[ConversationResponse]:
        """
        Get conversations by status.

        Args:
            status: Status to filter by (active, completed, abandoned)
            limit: Maximum number of records to return

        Returns:
            List of ConversationResponse objects

        Raises:
            Exception: If database operation fails
        """
        try:
            response = (
                self.db.table(self.table_name)
                .select("*")
                .eq("status", status)
                .order("last_message_at", desc=True)
                .limit(limit)
                .execute()
            )

            if response.data:
                return [ConversationResponse(**record) for record in response.data]

            return []

        except Exception as e:
            raise Exception(f"Database error while fetching conversations: {str(e)}")

    def link_conversation_to_claim(
        self, conversation_id: str, claim_id: str
    ) -> Optional[ConversationResponse]:
        """
        Link a conversation to a claim when claim is created.

        Args:
            conversation_id: The conversation_id
            claim_id: The claim UUID to link

        Returns:
            Updated ConversationResponse

        Raises:
            Exception: If database operation fails
        """
        update = ConversationUpdate(claim_id=claim_id, status="completed")
        return self.update_conversation(conversation_id, update)


class MessageDAO:
    """Handles database operations for messages table."""

    def __init__(self, db_client: Optional[Client] = None):
        """
        Initialize MessageDAO.

        Args:
            db_client: Optional Supabase client. If not provided, uses default client.
        """
        self.db = db_client or get_db()
        self.table_name = "messages"
        self.conversation_dao = ConversationDAO(db_client)

    def create_message(self, message: MessageCreate) -> MessageResponse:
        """
        Create a new message record.

        Args:
            message: MessageCreate model with message data

        Returns:
            MessageResponse: The created message record

        Raises:
            Exception: If database operation fails
        """
        try:
            # Ensure conversation exists and get its UUID
            conversation = self.conversation_dao.get_or_create_conversation(
                message.conversation_id
            )

            # Prepare message data with conversation UUID
            data = message.model_dump(exclude_none=False)
            data["conversation_id"] = conversation.id  # Use UUID for FK

            response = self.db.table(self.table_name).insert(data).execute()

            if not response.data or len(response.data) == 0:
                raise Exception("Failed to create message record")

            return MessageResponse(**response.data[0])

        except Exception as e:
            raise Exception(f"Database error while creating message: {str(e)}")

    def get_message_by_id(self, message_id: str) -> Optional[MessageResponse]:
        """
        Retrieve a message by its ID.

        Args:
            message_id: The UUID of the message

        Returns:
            MessageResponse if found, None otherwise

        Raises:
            Exception: If database operation fails
        """
        try:
            response = (
                self.db.table(self.table_name)
                .select("*")
                .eq("id", message_id)
                .execute()
            )

            if response.data and len(response.data) > 0:
                return MessageResponse(**response.data[0])

            return None

        except Exception as e:
            raise Exception(f"Database error while fetching message: {str(e)}")

    def get_messages_by_conversation(
        self, conversation_id: str, limit: int = 100
    ) -> List[MessageResponse]:
        """
        Retrieve all messages for a conversation.

        Args:
            conversation_id: The conversation_id or UUID
            limit: Maximum number of messages to return

        Returns:
            List of MessageResponse objects ordered by creation time

        Raises:
            Exception: If database operation fails
        """
        try:
            # Get conversation to get its UUID
            conversation = self.conversation_dao.get_conversation_by_conversation_id(
                conversation_id
            )

            if not conversation:
                # Try as UUID
                conversation = self.conversation_dao.get_conversation_by_id(
                    conversation_id
                )

            if not conversation:
                return []

            response = (
                self.db.table(self.table_name)
                .select("*")
                .eq("conversation_id", conversation.id)
                .order("created_at", desc=False)
                .limit(limit)
                .execute()
            )

            if response.data:
                return [MessageResponse(**record) for record in response.data]

            return []

        except Exception as e:
            raise Exception(f"Database error while fetching messages: {str(e)}")

    def get_messages_by_type(
        self, conversation_id: str, message_type: str
    ) -> List[MessageResponse]:
        """
        Get messages of a specific type for a conversation.

        Args:
            conversation_id: The conversation_id or UUID
            message_type: Type of messages to retrieve

        Returns:
            List of MessageResponse objects

        Raises:
            Exception: If database operation fails
        """
        try:
            # Get conversation to get its UUID
            conversation = self.conversation_dao.get_conversation_by_conversation_id(
                conversation_id
            )

            if not conversation:
                conversation = self.conversation_dao.get_conversation_by_id(
                    conversation_id
                )

            if not conversation:
                return []

            response = (
                self.db.table(self.table_name)
                .select("*")
                .eq("conversation_id", conversation.id)
                .eq("message_type", message_type)
                .order("created_at", desc=False)
                .execute()
            )

            if response.data:
                return [MessageResponse(**record) for record in response.data]

            return []

        except Exception as e:
            raise Exception(
                f"Database error while fetching messages by type: {str(e)}"
            )

    def get_conversation_with_messages(
        self, conversation_id: str
    ) -> Optional[ConversationWithMessages]:
        """
        Get a conversation with all its messages.

        Args:
            conversation_id: The conversation_id or UUID

        Returns:
            ConversationWithMessages if found, None otherwise

        Raises:
            Exception: If database operation fails
        """
        try:
            conversation = self.conversation_dao.get_conversation_by_conversation_id(
                conversation_id
            )

            if not conversation:
                conversation = self.conversation_dao.get_conversation_by_id(
                    conversation_id
                )

            if not conversation:
                return None

            messages = self.get_messages_by_conversation(conversation_id)

            return ConversationWithMessages(conversation=conversation, messages=messages)

        except Exception as e:
            raise Exception(
                f"Database error while fetching conversation with messages: {str(e)}"
            )
