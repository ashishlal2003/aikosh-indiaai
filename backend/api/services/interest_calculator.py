"""
Interest calculator per MSMED Act Section 15/16.
Computes compound interest on delayed payments to MSMEs.
"""

import logging
import math
from typing import Dict, Any

logger = logging.getLogger(__name__)

# RBI bank rate (as of 2024-25). Update when RBI changes it.
RBI_BANK_RATE = 6.5
# Section 16: rate = 3x the bank rate
INTEREST_RATE = RBI_BANK_RATE * 3  # 19.5%


def calculate_section15_interest(
    principal_amount: float,
    days_overdue: int,
) -> Dict[str, Any]:
    """
    Calculate compound interest per MSMED Act Section 15/16.

    Section 16 specifies:
    - Interest rate = 3x the RBI bank rate
    - Compounded monthly with monthly rests

    Args:
        principal_amount: Outstanding payment amount in INR.
        days_overdue: Number of days past the agreed payment date.

    Returns:
        Dict with principal, days_overdue, interest_rate, interest_amount, total_due.
    """
    if principal_amount <= 0:
        logger.warning(f"Invalid principal amount: {principal_amount}")
        return {
            "principal": principal_amount,
            "days_overdue": days_overdue,
            "interest_rate": INTEREST_RATE,
            "interest_amount": 0.0,
            "total_due": principal_amount,
            "note": "Principal must be a positive number.",
        }

    if days_overdue <= 0:
        return {
            "principal": principal_amount,
            "days_overdue": 0,
            "interest_rate": INTEREST_RATE,
            "interest_amount": 0.0,
            "total_due": principal_amount,
            "note": "No interest applicable - payment is not overdue.",
        }

    # Monthly rate from annual rate
    monthly_rate = INTEREST_RATE / (12 * 100)

    # Full months and remaining days
    full_months = days_overdue // 30
    remaining_days = days_overdue % 30

    # Compound interest for full months: P * (1 + r)^n - P
    compound_factor = math.pow(1 + monthly_rate, full_months)
    amount_after_months = principal_amount * compound_factor

    # Simple interest for remaining partial month
    daily_rate = monthly_rate / 30
    amount_after_remaining = amount_after_months * (1 + daily_rate * remaining_days)

    interest_amount = round(amount_after_remaining - principal_amount, 2)
    total_due = round(principal_amount + interest_amount, 2)

    logger.info(
        f"Interest calculated: principal={principal_amount}, days={days_overdue}, "
        f"interest={interest_amount}, total={total_due}"
    )

    return {
        "principal": principal_amount,
        "days_overdue": days_overdue,
        "interest_rate": INTEREST_RATE,
        "interest_amount": interest_amount,
        "total_due": total_due,
    }
