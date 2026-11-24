"""Tests for TripOptimizer and intelligent alternative generation."""

import pytest
from models.destination import Destination
from models.trip import Trip, CostBreakdown
from services.trip_optimizer import TripOptimizer
from services.trip_calculator import TripCostCalculator


@pytest.fixture
def mock_destinations():
    """Create a list of diverse test destinations with varied price points."""
    return [
        Destination(
            id="murree",
            name="Murree",
            region="Punjab",
            category="Mountains",
            description="Nearby hill station",
            room_capacity=2,
            base_transport_cost=2500,
            base_accommodation_cost=4000,
            base_food_cost=1500,
            base_activities_cost=1000,
        ),
        Destination(
            id="skardu",
            name="Skardu",
            region="Gilgit-Baltistan",
            category="Lakes & Nature",
            description="Far northern valley",
            room_capacity=2,
            base_transport_cost=15000,
            base_accommodation_cost=9000,
            base_food_cost=3000,
            base_activities_cost=2500,
        ),
        Destination(
            id="lahore",
            name="Lahore",
            region="Punjab",
            category="Historical Places",
            description="Cultural hub",
            room_capacity=2,
            base_transport_cost=3000,
            base_accommodation_cost=4500,
            base_food_cost=2000,
            base_activities_cost=1200,
        ),
    ]


class TestTripOptimizer:
    """Test suite for intelligent trip alternative generation and ranking."""

    def test_increase_budget_calculation(self, mock_destinations):
        skardu = mock_destinations[1]
        budget = 50000.0
        bd = TripCostCalculator.calculate(
            destination=skardu,
            travellers=2,
            days=4,
            nights=3,
            travel_category="Standard",
            budget=budget,
        )
        assert bd.total_cost > budget

        trip = Trip(
            trip_id="TRIP-TEST",
            destination_id=skardu.id,
            destination_name=skardu.name,
            departure_city="Islamabad",
            budget=budget,
            travellers=2,
            days=4,
            nights=3,
            cost_breakdown=bd,
        )

        res = TripOptimizer.calculate_increase_budget_option(trip, bd)
        assert res["required_budget"] == bd.total_cost
        assert res["additional_amount"] == bd.shortage
        assert res["additional_amount"] > 0

    def test_reduce_travellers_alternative(self, mock_destinations):
        """When 4 travellers are over budget, optimizer should find max feasible travellers."""
        murree = mock_destinations[0]
        budget = 25000.0
        # 4 travellers costs more than 25,000
        trip = Trip(
            trip_id="TRIP-TEST-TRAV",
            destination_id=murree.id,
            destination_name=murree.name,
            departure_city="Islamabad",
            budget=budget,
            travellers=4,
            days=3,
            nights=2,
            travel_category="Standard",
        )
        opt = TripOptimizer.find_feasible_travellers_reduction(trip, murree)
        assert opt is not None
        assert opt.strategy == "reduce_travellers"
        assert opt.modified_trip.travellers < 4
        assert opt.cost_breakdown.total_cost <= budget

    def test_reduce_duration_alternative(self, mock_destinations):
        """When 5 days is over budget, optimizer should find feasible shortened duration."""
        murree = mock_destinations[0]
        budget = 28000.0
        trip = Trip(
            trip_id="TRIP-TEST-DUR",
            destination_id=murree.id,
            destination_name=murree.name,
            departure_city="Islamabad",
            budget=budget,
            travellers=2,
            days=5,
            nights=4,
            travel_category="Standard",
        )
        opt = TripOptimizer.find_feasible_duration_reduction(trip, murree)
        assert opt is not None
        assert opt.strategy == "reduce_duration"
        assert opt.modified_trip.days < 5
        assert opt.cost_breakdown.total_cost <= budget

    def test_preference_adjustment_downgrade(self, mock_destinations):
        """When Premium is unaffordable, optimizer suggests Standard or Budget."""
        murree = mock_destinations[0]
        # Set budget that fits Standard but not Premium
        premium_cost = TripCostCalculator.calculate(
            destination=murree,
            travellers=2,
            days=3,
            nights=2,
            travel_category="Premium",
        ).total_cost
        standard_cost = TripCostCalculator.calculate(
            destination=murree,
            travellers=2,
            days=3,
            nights=2,
            travel_category="Standard",
        ).total_cost

        budget = standard_cost + 1000.0
        assert budget < premium_cost

        trip = Trip(
            trip_id="TRIP-TEST-PREF",
            destination_id=murree.id,
            destination_name=murree.name,
            departure_city="Islamabad",
            budget=budget,
            travellers=2,
            days=3,
            nights=2,
            travel_category="Premium",
        )

        opt = TripOptimizer.find_feasible_preference_adjustment(trip, murree)
        assert opt is not None
        assert opt.modified_trip.travel_category in ["Standard", "Budget"]
        assert opt.cost_breakdown.total_cost <= budget

    def test_destination_alternative(self, mock_destinations):
        """Expensive Skardu should recommend affordable Murree or Lahore."""
        skardu = mock_destinations[1]
        budget = 35000.0
        trip = Trip(
            trip_id="TRIP-TEST-DEST",
            destination_id=skardu.id,
            destination_name=skardu.name,
            departure_city="Islamabad",
            budget=budget,
            travellers=2,
            days=3,
            nights=2,
            travel_category="Standard",
        )
        alternatives = TripOptimizer.find_feasible_destination_alternatives(
            trip, mock_destinations
        )
        assert len(alternatives) > 0
        for alt in alternatives:
            assert alt.cost_breakdown.total_cost <= budget
            assert alt.modified_trip.destination_id != "skardu"

    def test_strict_affordability_guarantee(self, mock_destinations):
        """CRITICAL: Optimizer MUST NEVER recommend an alternative that exceeds budget."""
        skardu = mock_destinations[1]
        # Unrealistically small budget of PKR 100 (unaffordable for anything)
        impossible_budget = 100.0
        trip = Trip(
            trip_id="TRIP-IMPOSSIBLE",
            destination_id=skardu.id,
            destination_name=skardu.name,
            departure_city="Islamabad",
            budget=impossible_budget,
            travellers=2,
            days=3,
            nights=2,
            travel_category="Standard",
        )

        all_alts = TripOptimizer.generate_all_alternatives(trip, skardu, mock_destinations)
        # All alternatives returned must be strictly <= impossible_budget
        assert all(alt.cost_breakdown.total_cost <= impossible_budget for alt in all_alts)
        # In this case, none can fit PKR 100
        assert len(all_alts) == 0
