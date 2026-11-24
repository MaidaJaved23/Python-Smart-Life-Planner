"""Tests for TripFeasibilityChecker and boundary classifications."""

import pytest
from services.feasibility_checker import TripFeasibilityChecker
from models.trip import CostBreakdown


class TestTripFeasibilityChecker:
    """Tests for feasibility classification, exact budget, PKR 1 boundaries, and shortage diagnostic."""

    def test_within_budget(self):
        budget = 50000.0
        total_cost = 45000.0
        status, msg = TripFeasibilityChecker.check_feasibility(budget, total_cost)
        assert status == TripFeasibilityChecker.STATUS_WITHIN_BUDGET
        assert "Within Budget" in msg
        assert "5,000.00" in msg

    def test_exactly_within_budget(self):
        """Test exact budget match boundary."""
        budget = 40000.0
        total_cost = 40000.0
        status, msg = TripFeasibilityChecker.check_feasibility(budget, total_cost)
        assert status == TripFeasibilityChecker.STATUS_EXACTLY_BUDGET
        assert "Exactly Within Budget" in msg

    def test_one_rupee_above_budget(self):
        """PKR 1 above budget boundary (total_cost is budget - 1 -> Within Budget)."""
        budget = 50000.0
        total_cost = 49999.0
        status, msg = TripFeasibilityChecker.check_feasibility(budget, total_cost)
        assert status == TripFeasibilityChecker.STATUS_WITHIN_BUDGET
        assert "Surplus remaining balance: PKR 1.00" in msg

    def test_one_rupee_below_budget(self):
        """PKR 1 below budget boundary (total_cost is budget + 1 -> Over Budget)."""
        budget = 50000.0
        total_cost = 50001.0
        status, msg = TripFeasibilityChecker.check_feasibility(budget, total_cost)
        assert status == TripFeasibilityChecker.STATUS_OVER_BUDGET
        assert "Budget deficit: PKR 1.00" in msg

    def test_explain_shortage_diagnostic(self):
        budget = 30000.0
        bd = CostBreakdown(
            transportation=8000.0,
            rooms_needed=1,
            accommodation=15000.0,
            food=8000.0,
            activities=3000.0,
            emergency_allowance=1700.0,
            total_cost=35700.0,
            cost_per_person=17850.0,
            remaining_budget=-5700.0,
            shortage=5700.0,
        )
        explanation = TripFeasibilityChecker.explain_shortage(budget, bd)
        assert "5,700.00" in explanation
        assert "Accommodation" in explanation
        assert "Primary Cost Driver" in explanation
