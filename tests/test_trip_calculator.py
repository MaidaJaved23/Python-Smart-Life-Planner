"""Tests for TripCostCalculator and cost breakdown formulas."""

import pytest
from models.destination import Destination
from services.trip_calculator import TripCostCalculator


@pytest.fixture
def sample_destination():
    """Create a standardized destination for testing calculation formulas."""
    return Destination(
        id="test_murree",
        name="Test Murree",
        region="Punjab",
        category="Mountains",
        description="Test mountain destination",
        room_capacity=2,
        base_transport_cost=3000.0,
        base_accommodation_cost=5000.0,
        base_food_cost=2000.0,
        base_activities_cost=1000.0,
        category_multipliers={
            "Budget": {"transport": 0.8, "accommodation": 0.7, "food": 0.8, "activities": 0.8},
            "Standard": {"transport": 1.0, "accommodation": 1.0, "food": 1.0, "activities": 1.0},
            "Premium": {"transport": 1.8, "accommodation": 2.0, "food": 1.5, "activities": 1.5},
        },
    )


class TestTripCostCalculator:
    """Comprehensive test suite for financial calculations."""

    def test_standard_trip_calculation(self, sample_destination):
        """Verify calculations for 2 travellers, 3 days, 2 nights in Standard category."""
        travellers = 2
        days = 3
        nights = 2
        budget = 50000.0

        # Calculations:
        # Transport: 3000 * 1.0 * 2 = 6,000
        # Rooms: ceil(2 / 2) = 1 room
        # Accommodation: 5000 * 1.0 * 1 * 2 = 10,000
        # Food: 2000 * 1.0 * 2 * 3 = 12,000
        # Activities: 1000 * 1.0 * 2 * 3 = 6,000
        # Subtotal: 6,000 + 10,000 + 12,000 + 6,000 = 34,000
        # Emergency (5%): 34,000 * 0.05 = 1,700
        # Total: 35,700
        # Per person: 35,700 / 2 = 17,850
        # Remaining budget: 50,000 - 35,700 = 14,300

        bd = TripCostCalculator.calculate(
            destination=sample_destination,
            travellers=travellers,
            days=days,
            nights=nights,
            travel_category="Standard",
            budget=budget,
            emergency_pct=0.05,
        )

        assert bd.transportation == 6000.0
        assert bd.rooms_needed == 1
        assert bd.accommodation == 10000.0
        assert bd.food == 12000.0
        assert bd.activities == 6000.0
        assert bd.emergency_allowance == 1700.0
        assert bd.total_cost == 35700.0
        assert bd.cost_per_person == 17850.0
        assert bd.remaining_budget == 14300.0
        assert bd.shortage == 0.0

    def test_zero_night_day_trip(self, sample_destination):
        """CRITICAL: A zero-night trip MUST have zero accommodation cost."""
        travellers = 4
        days = 1
        nights = 0
        budget = 30000.0

        bd = TripCostCalculator.calculate(
            destination=sample_destination,
            travellers=travellers,
            days=days,
            nights=nights,
            travel_category="Standard",
            budget=budget,
        )

        assert bd.accommodation == 0.0  # Must be strictly 0
        assert bd.rooms_needed == 2     # ceil(4/2) = 2
        # Transport: 3000 * 4 = 12,000
        assert bd.transportation == 12000.0
        # Food: 2000 * 4 * 1 = 8,000
        assert bd.food == 8000.0
        # Activities: 1000 * 4 * 1 = 4,000
        assert bd.activities == 4000.0
        # Subtotal: 24,000; Emergency: 1,200; Total: 25,200
        assert bd.total_cost == 25200.0
        assert bd.cost_per_person == 6300.0
        assert bd.remaining_budget == 4800.0

    def test_room_capacity_ceiling_division(self, sample_destination):
        """Test that odd number of travellers requires ceiling of rooms.

        For room capacity 2:
        1 pax -> 1 room
        2 pax -> 1 room
        3 pax -> 2 rooms
        5 pax -> 3 rooms
        """
        assert sample_destination.calculate_required_rooms(1) == 1
        assert sample_destination.calculate_required_rooms(2) == 1
        assert sample_destination.calculate_required_rooms(3) == 2
        assert sample_destination.calculate_required_rooms(5) == 3

        # Calculation for 3 pax: 2 rooms required
        bd = TripCostCalculator.calculate(
            destination=sample_destination,
            travellers=3,
            days=2,
            nights=1,
            travel_category="Standard",
        )
        assert bd.rooms_needed == 2
        # Accommodation: 5000 * 1.0 * 2 rooms * 1 night = 10,000
        assert bd.accommodation == 10000.0

    @pytest.mark.parametrize(
        "category,transport_mult,hotel_mult",
        [
            ("Budget", 0.8, 0.7),
            ("Standard", 1.0, 1.0),
            ("Premium", 1.8, 2.0),
        ],
    )
    def test_travel_categories_multipliers(
        self, sample_destination, category, transport_mult, hotel_mult
    ):
        """Verify tier multipliers properly scale individual components."""
        bd = TripCostCalculator.calculate(
            destination=sample_destination,
            travellers=1,
            days=2,
            nights=1,
            travel_category=category,
        )
        expected_transport = round(3000.0 * transport_mult * 1, 2)
        expected_hotel = round(5000.0 * hotel_mult * 1 * 1, 2)
        assert bd.transportation == expected_transport
        assert bd.accommodation == expected_hotel

    def test_emergency_allowance_boundary_impact(self, sample_destination):
        """Verify that emergency allowance calculation is strictly applied and affects shortage."""
        budget = 34500.0
        # Base subtotal is 34,000. With 5% emergency allowance (1,700), total is 35,700.
        # Budget 34,500 would cover base (34,000), but exceeds with emergency allowance (35,700).
        bd = TripCostCalculator.calculate(
            destination=sample_destination,
            travellers=2,
            days=3,
            nights=2,
            travel_category="Standard",
            budget=budget,
            emergency_pct=0.05,
        )
        assert bd.total_cost == 35700.0
        assert bd.shortage == 1200.0
        assert bd.remaining_budget == -1200.0
