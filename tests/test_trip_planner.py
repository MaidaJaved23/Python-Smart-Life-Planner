"""Tests for TripPlanner service and dynamic parameter modifications."""

import pytest
from models.destination import Destination
from services.trip_planner import TripPlanner
from utils.data_manager import DataManager


@pytest.fixture
def mock_planner(tmp_path):
    """Create a TripPlanner instance with isolated temporary data directories."""
    dm = DataManager(base_dir=str(tmp_path))
    # Seed destination data
    dest = Destination(
        id="murree",
        name="Murree",
        region="Punjab",
        category="Mountains",
        description="Pine hills",
        room_capacity=2,
        base_transport_cost=3000,
        base_accommodation_cost=5000,
        base_food_cost=2000,
        base_activities_cost=1000,
        attractions=["Mall Road", "Patriata Chairlift"],
    )
    dm.save_trips_data([])
    planner = TripPlanner(data_manager=dm)
    planner.destinations = {"murree": dest}
    return planner


class TestTripPlanner:
    """Test suite for trip planning workflows, adjustments, and confirmations."""

    def test_create_valid_trip_plan(self, mock_planner):
        trip, bd, status, msg = mock_planner.create_trip_plan(
            budget=60000.0,
            travellers=2,
            destination_name_or_id="murree",
            departure_city="Islamabad",
            days=3,
            nights=2,
            travel_category="Standard",
        )
        assert trip is not None
        assert trip.destination_name == "Murree"
        assert trip.travellers == 2
        assert trip.days == 3
        assert trip.nights == 2
        assert len(trip.itinerary) == 3
        assert trip.confirmed is False

    def test_create_zero_night_itinerary(self, mock_planner):
        """Test day trip (0 nights) generates accurate 1-day itinerary."""
        trip, bd, status, msg = mock_planner.create_trip_plan(
            budget=30000.0,
            travellers=2,
            destination_name_or_id="murree",
            departure_city="Rawalpindi",
            days=1,
            nights=0,
            travel_category="Standard",
        )
        assert len(trip.itinerary) == 1
        day1 = trip.itinerary[0]
        assert "Day Trip Excursion" in day1["title"]
        assert "Same day return" in day1["night_stay"]

    def test_dynamic_modification_cancellation(self, mock_planner):
        """CRITICAL: Cancelled modification must preserve previous plan intact."""
        trip, bd, status, msg = mock_planner.create_trip_plan(
            budget=50000.0,
            travellers=2,
            destination_name_or_id="murree",
            departure_city="Islamabad",
            days=3,
            nights=2,
        )
        original_travellers = trip.travellers
        original_days = trip.days
        original_cost = trip.cost_breakdown.total_cost

        # Propose modification to 5 travellers and 5 days
        cand_trip, cand_bd, cand_status, _ = mock_planner.modify_trip_parameters(
            trip, travellers=5, days=5, nights=4
        )

        assert cand_trip.travellers == 5
        assert cand_trip.cost_breakdown.total_cost > original_cost

        # Verify original trip object was NOT modified (safe immutability/cloning)
        assert trip.travellers == original_travellers
        assert trip.days == original_days
        assert trip.cost_breakdown.total_cost == original_cost

    def test_dynamic_modification_confirmation(self, mock_planner):
        """Confirmed modification updates and saves the plan."""
        trip, bd, status, msg = mock_planner.create_trip_plan(
            budget=80000.0,
            travellers=2,
            destination_name_or_id="murree",
            departure_city="Islamabad",
            days=3,
            nights=2,
        )
        cand_trip, cand_bd, cand_status, _ = mock_planner.modify_trip_parameters(
            trip, travellers=3, budget=90000.0
        )

        # Confirm candidate trip
        success = mock_planner.confirm_and_save_trip(cand_trip)
        assert success is True
        assert cand_trip.confirmed is True
        assert len(mock_planner.confirmed_trips) == 1
        assert mock_planner.confirmed_trips[0].travellers == 3

    def test_invalid_destination_raises_error(self, mock_planner):
        with pytest.raises(ValueError, match="not found in database"):
            mock_planner.create_trip_plan(
                budget=50000.0,
                travellers=2,
                destination_name_or_id="atlantis",
                departure_city="Islamabad",
                days=3,
                nights=2,
            )
