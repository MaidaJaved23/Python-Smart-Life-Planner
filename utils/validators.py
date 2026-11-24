"""Input validation utilities and error handling."""

from collections import namedtuple
from datetime import datetime
import re
from typing import Any, Tuple, Optional

# Structured record for validation outcomes
ValidationResult = namedtuple("ValidationResult", ["is_valid", "value", "error_message"])

VALID_TRAVEL_CATEGORIES = {"Budget", "Standard", "Premium"}
VALID_DESTINATION_TYPES = {"Mountains", "Historical Places", "Lakes & Nature", "Any"}
VALID_BUDGET_TYPES = {"Home & Kitchen", "Personal Finance"}


def validate_positive_number(
    val: Any,
    field_name: str = "Amount",
    allow_zero: bool = False,
    max_val: Optional[float] = None,
) -> ValidationResult:
    """Validate that input is a positive number (float or int)."""
    if val is None or (isinstance(val, str) and not val.strip()):
        return ValidationResult(False, None, f"{field_name} cannot be empty.")
    try:
        clean_str = str(val).replace(",", "").strip()
        num = float(clean_str)
    except (ValueError, TypeError):
        return ValidationResult(False, None, f"{field_name} must be a valid numeric amount.")

    if allow_zero:
        if num < 0:
            return ValidationResult(False, None, f"{field_name} cannot be negative.")
    else:
        if num <= 0:
            return ValidationResult(False, None, f"{field_name} must be greater than zero.")

    if max_val is not None and num > max_val:
        return ValidationResult(False, None, f"{field_name} cannot exceed {max_val:,.2f}.")

    return ValidationResult(True, round(num, 2), "")


def validate_integer(
    val: Any,
    field_name: str = "Value",
    min_val: int = 1,
    max_val: Optional[int] = None,
) -> ValidationResult:
    """Validate that input is an integer within allowed bounds."""
    if val is None or (isinstance(val, str) and not val.strip()):
        return ValidationResult(False, None, f"{field_name} cannot be empty.")
    try:
        clean_str = str(val).replace(",", "").strip()
        # Ensure it doesn't have decimals if passed as string
        float_val = float(clean_str)
        if not float_val.is_integer():
            return ValidationResult(False, None, f"{field_name} must be a whole integer.")
        int_val = int(float_val)
    except (ValueError, TypeError):
        return ValidationResult(False, None, f"{field_name} must be an integer.")

    if int_val < min_val:
        return ValidationResult(False, None, f"{field_name} must be at least {min_val}.")

    if max_val is not None and int_val > max_val:
        return ValidationResult(False, None, f"{field_name} cannot exceed {max_val}.")

    return ValidationResult(True, int_val, "")


def validate_days_and_nights(days_val: Any, nights_val: Any) -> Tuple[bool, int, int, str]:
    """Validate trip days and nights:

    - Days must be an integer >= 1 (max 60 days).
    - Nights must be an integer >= 0.
    - Nights cannot exceed days (e.g. 1 day can have 0 or 1 night).
    """
    days_res = validate_integer(days_val, "Trip days", min_val=1, max_val=60)
    if not days_res.is_valid:
        return False, 0, 0, days_res.error_message

    nights_res = validate_integer(nights_val, "Trip nights", min_val=0, max_val=60)
    if not nights_res.is_valid:
        return False, 0, 0, nights_res.error_message

    days = days_res.value
    nights = nights_res.value

    if nights > days:
        return (
            False,
            days,
            nights,
            f"Trip nights ({nights}) cannot exceed trip days ({days}).",
        )

    return True, days, nights, ""


def validate_travel_category(cat_str: str) -> ValidationResult:
    """Validate travel category."""
    if not cat_str or not str(cat_str).strip():
        return ValidationResult(False, None, "Travel category cannot be empty.")
    clean = str(cat_str).strip().title()
    if clean not in VALID_TRAVEL_CATEGORIES:
        return ValidationResult(
            False,
            None,
            f"Invalid category '{clean}'. Must be one of: {', '.join(sorted(VALID_TRAVEL_CATEGORIES))}.",
        )
    return ValidationResult(True, clean, "")


def validate_destination_type(type_str: str) -> ValidationResult:
    """Validate preferred destination type."""
    if not type_str or not str(type_str).strip():
        return ValidationResult(True, "Any", "")
    clean = str(type_str).strip().title()
    # Normalize potential plural/case variations
    for valid in VALID_DESTINATION_TYPES:
        if clean.lower() == valid.lower():
            return ValidationResult(True, valid, "")
    return ValidationResult(
        False,
        None,
        f"Invalid destination type '{type_str}'. Must be one of: {', '.join(sorted(VALID_DESTINATION_TYPES))}.",
    )


def validate_budget_type(btype: str) -> ValidationResult:
    """Validate monthly budget type."""
    if not btype or not str(btype).strip():
        return ValidationResult(False, None, "Budget type cannot be empty.")
    clean = str(btype).strip().title()
    for valid in VALID_BUDGET_TYPES:
        if clean.lower() == valid.lower() or (
            "home" in clean.lower() and "Home & Kitchen" == valid
        ) or (
            "personal" in clean.lower() and "Personal Finance" == valid
        ):
            return ValidationResult(True, valid, "")
    return ValidationResult(
        False,
        None,
        f"Invalid budget type '{btype}'. Must be 'Home & Kitchen' or 'Personal Finance'.",
    )


def validate_date_string(date_str: str) -> ValidationResult:
    """Validate date format (YYYY-MM-DD)."""
    if not date_str or not str(date_str).strip():
        return ValidationResult(True, datetime.now().strftime("%Y-%m-%d"), "")
    clean = str(date_str).strip()
    try:
        parsed = datetime.strptime(clean, "%Y-%m-%d")
        return ValidationResult(True, parsed.strftime("%Y-%m-%d"), "")
    except ValueError:
        return ValidationResult(
            False,
            None,
            f"Invalid date format '{date_str}'. Please use YYYY-MM-DD (e.g. 2026-11-24).",
        )


def validate_email(email_str: str) -> ValidationResult:
    """Validate email address format."""
    if not email_str or not str(email_str).strip():
        return ValidationResult(False, None, "Email address cannot be empty.")
    clean = str(email_str).strip()
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if not re.match(pattern, clean):
        return ValidationResult(False, None, f"Invalid email format: '{clean}'.")
    return ValidationResult(True, clean, "")
