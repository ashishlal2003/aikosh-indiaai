"""Date/time utilities for legal document formatting."""

from datetime import datetime
from zoneinfo import ZoneInfo

def get_current_date() -> str:
    """Return today's date formatted for legal notices (e.g., '07 February 2026') with timestamp in IST."""
    return datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d %B %Y")