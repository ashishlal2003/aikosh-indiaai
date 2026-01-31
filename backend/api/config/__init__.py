"""Configuration module for database and other settings."""

from api.config.database import get_db, DatabaseConfig

__all__ = ["get_db", "DatabaseConfig"]
