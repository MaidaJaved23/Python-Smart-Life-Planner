"""Tests for input validators and boundary validation logic."""

import pytest
from utils.validators import (
    validate_positive_number,
    validate_integer,
    validate_days_and_nights,
    validate_travel_category,
    validate_destination_type,
    validate_budget_type,
    validate_date_string,
    validate_email,
)


class TestValidators:
    """Test suite for input validation functions and boundary edge cases."""

    @pytest.mark.parametrize(
        "val,allow_zero,expected_valid,expected_val",
        [
            ("1000", False, True, 1000.0),
            ("50,000.50", False, True, 50000.50),
            (2500, False, True, 2500.0),
            ("0", True, True, 0.0),
            ("0", False, False, None),
            ("-150", False, False, None),
            ("-150", True, False, None),
            ("", False, False, None),
            ("   ", False, False, None),
            ("abc", False, False, None),
            ("12.34.56", False, False, None),
            (None, False, False, None),
        ],
    )
    def test_validate_positive_number(self, val, allow_zero, expected_valid, expected_val):
        res = validate_positive_number(val, "Test Field", allow_zero=allow_zero)
        assert res.is_valid == expected_valid
        if expected_valid:
            assert res.value == expected_val
        else:
            assert res.error_message != ""

    @pytest.mark.parametrize(
        "val,min_val,max_val,expected_valid,expected_val",
        [
            ("1", 1, 100, True, 1),
            ("10", 1, 100, True, 10),
            ("100", 1, 100, True, 100),
            ("0", 1, 100, False, None),
            ("-5", 1, 100, False, None),
            ("101", 1, 100, False, None),
            ("3.5", 1, 100, False, None),
            ("abc", 1, 100, False, None),
            ("", 1, 100, False, None),
        ],
    )
    def test_validate_integer(self, val, min_val, max_val, expected_valid, expected_val):
        res = validate_integer(val, "Test Int", min_val=min_val, max_val=max_val)
        assert res.is_valid == expected_valid
        if expected_valid:
            assert res.value == expected_val
        else:
            assert res.error_message != ""

    @pytest.mark.parametrize(
        "days,nights,expected_valid,expected_d,expected_n",
        [
            ("1", "0", True, 1, 0),    # Single day trip with 0 nights
            ("1", "1", True, 1, 1),    # 1 day 1 night
            ("3", "2", True, 3, 2),    # Normal multi-day
            ("5", "4", True, 5, 4),
            ("7", "7", True, 7, 7),
            ("2", "3", False, 2, 3),   # Nights > Days (invalid!)
            ("0", "0", False, 0, 0),   # Days < 1
            ("-1", "0", False, 0, 0),  # Negative days
            ("3", "-1", False, 0, 0),  # Negative nights
            ("abc", "1", False, 0, 0), # Non-numeric days
            ("3", "xyz", False, 0, 0), # Non-numeric nights
        ],
    )
    def test_validate_days_and_nights(self, days, nights, expected_valid, expected_d, expected_n):
        valid, d, n, err = validate_days_and_nights(days, nights)
        assert valid == expected_valid
        if expected_valid:
            assert d == expected_d
            assert n == expected_n
            assert err == ""
        else:
            assert err != ""

    @pytest.mark.parametrize(
        "category,expected_valid,expected_val",
        [
            ("Budget", True, "Budget"),
            ("standard", True, "Standard"),
            ("PREMIUM", True, "Premium"),
            ("Luxury", False, None),
            ("", False, None),
            ("123", False, None),
        ],
    )
    def test_validate_travel_category(self, category, expected_valid, expected_val):
        res = validate_travel_category(category)
        assert res.is_valid == expected_valid
        if expected_valid:
            assert res.value == expected_val

    @pytest.mark.parametrize(
        "dtype,expected_valid,expected_val",
        [
            ("Mountains", True, "Mountains"),
            ("historical places", True, "Historical Places"),
            ("Lakes & Nature", True, "Lakes & Nature"),
            ("Any", True, "Any"),
            ("", True, "Any"),  # Defaults to Any
            ("Deserts", False, None),
        ],
    )
    def test_validate_destination_type(self, dtype, expected_valid, expected_val):
        res = validate_destination_type(dtype)
        assert res.is_valid == expected_valid
        if expected_valid:
            assert res.value == expected_val

    @pytest.mark.parametrize(
        "btype,expected_valid,expected_val",
        [
            ("Home & Kitchen", True, "Home & Kitchen"),
            ("home", True, "Home & Kitchen"),
            ("Personal Finance", True, "Personal Finance"),
            ("personal", True, "Personal Finance"),
            ("Corporate", False, None),
            ("", False, None),
        ],
    )
    def test_validate_budget_type(self, btype, expected_valid, expected_val):
        res = validate_budget_type(btype)
        assert res.is_valid == expected_valid
        if expected_valid:
            assert res.value == expected_val

    @pytest.mark.parametrize(
        "date_str,expected_valid,expected_val",
        [
            ("2026-11-24", True, "2026-11-24"),
            ("2025-01-01", True, "2025-01-01"),
            ("24-11-2026", False, None),  # Invalid format
            ("2026/11/24", False, None),
            ("not-a-date", False, None),
        ],
    )
    def test_validate_date_string(self, date_str, expected_valid, expected_val):
        res = validate_date_string(date_str)
        assert res.is_valid == expected_valid
        if expected_valid:
            assert res.value == expected_val

    @pytest.mark.parametrize(
        "email,expected_valid",
        [
            ("user@example.com", True),
            ("developer.test+1@domain.pk", True),
            ("invalid-email", False),
            ("@domain.com", False),
            ("user@", False),
            ("", False),
        ],
    )
    def test_validate_email(self, email, expected_valid):
        res = validate_email(email)
        assert res.is_valid == expected_valid
