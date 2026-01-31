"""
Database configuration module.
Provides a singleton Supabase client for database operations.
"""

import os
from typing import Optional
from supabase import Client, create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class DatabaseConfig:
    """Singleton class for managing Supabase database connection."""

    _instance: Optional[Client] = None

    @classmethod
    def get_client(cls) -> Client:
        """
        Get or create Supabase client instance.

        Returns:
            Client: Supabase client instance

        Raises:
            ValueError: If SUPABASE_URL or SUPABASE_KEY are not set
        """
        if cls._instance is None:
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_KEY")

            if not supabase_url or not supabase_key:
                raise ValueError(
                    "SUPABASE_URL and SUPABASE_KEY must be set in environment variables"
                )

            cls._instance = create_client(supabase_url, supabase_key)

        return cls._instance


# Convenience function for getting database client
def get_db() -> Client:
    """
    Get Supabase database client.

    Returns:
        Client: Supabase client instance
    """
    return DatabaseConfig.get_client()
