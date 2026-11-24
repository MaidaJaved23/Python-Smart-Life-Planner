"""Trip cost calculator service.

Implements all required cost formulas and returns structured CostBreakdown.

Calculation Assumptions:
1. Transportation Cost: Base transportation cost multiplied by tier multiplier (Budget: 0.8,
   Standard: 1.0, Premium: 1.8) multiplied by the total number of travellers.
2. Room Capacity & Allocation: Calculated using ceiling division math.ceil(travellers / room_capacity).
   For example, 3 travellers with room capacity 2 require 2 rooms.
3. Accommodation Cost: Room cost per night multiplied by tier multiplier, multiplied by
   the number of required rooms, multiplied by the number of nights.
   ZERO-NIGHT RULE: A day trip with 0 nights has 0 accommodation cost.
4. Food Cost: Base food cost per person per day multiplied by tier multiplier,
   multiplied by the number of travellers, multiplied by the number of days.
5. Activities & Miscellaneous: Base activities cost per person per day multiplied by tier
   multiplier, multiplied by travellers, multiplied by days.
6. Emergency Allowance: A defined safety buffer (default 5%) calculated over the sum of
   base operational expenses (transport + accommodation + food + activities).
7. Total Estimated Cost: Sum of transportation, accommodation, food, activities,
   and emergency allowance.
8. Cost Per Person: Total cost divided by the number of travellers.
9. Remaining Budget / Shortage: Available budget minus total estimated cost.
"""

from typing import Optional
from models.destination import Destination
from models.trip import CostBreakdown
from utils.calculations import (
    calculate_rooms_needed,
    calculate_transport_cost,
    calculate_accommodation_cost,
    calculate_food_cost,
    calculate_activities_cost,
    calculate_emergency_allowance,
    calculate_total_trip_cost,
    calculate_cost_per_person,
)


class TripCostCalculator:
    """Service to calculate trip costs and financial breakdowns."""

    DEFAULT_EMERGENCY_PCT = 0.05  # 5% emergency buffer

    @classmethod
    def calculate(
        cls,
        destination: Destination,
        travellers: int,
        days: int,
        nights: int,
        travel_category: str = "Standard",
        budget: float = 0.0,
        emergency_pct: Optional[float] = None,
    ) -> CostBreakdown:
        """Calculate complete financial breakdown for a trip."""
        if travellers <= 0 or days <= 0:
            return CostBreakdown(
                transportation=0.0,
                rooms_needed=0,
                accommodation=0.0,
                food=0.0,
                activities=0.0,
                emergency_allowance=0.0,
                total_cost=0.0,
                cost_per_person=0.0,
                remaining_budget=budget,
                shortage=0.0,
            )

        cat = travel_category.title() if travel_category else "Standard"
        pct = cls.DEFAULT_EMERGENCY_PCT if emergency_pct is None else emergency_pct

        # Multipliers
        transport_mult = destination.get_tier_multiplier(cat, "transport")
        room_mult = destination.get_tier_multiplier(cat, "accommodation")
        food_mult = destination.get_tier_multiplier(cat, "food")
        activity_mult = destination.get_tier_multiplier(cat, "activities")

        # 1. Transportation
        transport_cost = calculate_transport_cost(
            destination.base_transport_cost, transport_mult, travellers
        )

        # 2. Rooms & Accommodation
        rooms_needed = calculate_rooms_needed(travellers, destination.room_capacity)
        accommodation_cost = calculate_accommodation_cost(
            destination.base_accommodation_cost, room_mult, rooms_needed, nights
        )

        # 3. Food
        food_cost = calculate_food_cost(
            destination.base_food_cost, food_mult, travellers, days
        )

        # 4. Activities & Misc
        activities_cost = calculate_activities_cost(
            destination.base_activities_cost, activity_mult, travellers, days
        )

        # 5. Emergency Allowance
        subtotal = transport_cost + accommodation_cost + food_cost + activities_cost
        emergency_allowance = calculate_emergency_allowance(subtotal, pct)

        # 6. Total Cost & Cost per person
        total_cost = calculate_total_trip_cost(
            transport_cost,
            accommodation_cost,
            food_cost,
            activities_cost,
            emergency_allowance,
        )
        cost_per_person = calculate_cost_per_person(total_cost, travellers)

        # 7. Remaining budget or shortage
        remaining_budget = round(budget - total_cost, 2)
        shortage = round(total_cost - budget, 2) if total_cost > budget else 0.0

        return CostBreakdown(
            transportation=transport_cost,
            rooms_needed=rooms_needed,
            accommodation=accommodation_cost,
            food=food_cost,
            activities=activities_cost,
            emergency_allowance=emergency_allowance,
            total_cost=total_cost,
            cost_per_person=cost_per_person,
            remaining_budget=remaining_budget,
            shortage=shortage,
        )
