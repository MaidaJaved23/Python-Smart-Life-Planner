"""Trip and cost breakdown models."""

from collections import namedtuple
import copy
from datetime import datetime
from typing import Dict, Any, List, Optional

# NamedTuple for structured immutable cost breakdown
CostBreakdown = namedtuple(
    "CostBreakdown",
    [
        "transportation",
        "rooms_needed",
        "accommodation",
        "food",
        "activities",
        "emergency_allowance",
        "total_cost",
        "cost_per_person",
        "remaining_budget",
        "shortage",
    ],
)

# NamedTuple for optimization alternatives
OptimizationOption = namedtuple(
    "OptimizationOption",
    [
        "strategy",
        "title",
        "description",
        "modified_trip",
        "cost_breakdown",
        "remaining_budget",
        "score",
    ],
)


class Trip:
    """Represents a planned trip in Pakistan.

    Encapsulates trip parameters, calculation results, feasibility status,
    and day-wise itinerary.
    """

    def __init__(
        self,
        trip_id: str,
        destination_id: str,
        destination_name: str,
        departure_city: str,
        budget: float,
        travellers: int,
        days: int,
        nights: int,
        travel_category: str = "Standard",
        transport_pref: Optional[str] = None,
        accommodation_pref: Optional[str] = None,
        destination_type_pref: str = "Any",
        status: str = "Pending",
        cost_breakdown: Optional[CostBreakdown] = None,
        itinerary: Optional[List[Dict[str, Any]]] = None,
        created_at: Optional[str] = None,
        confirmed: bool = False,
    ):
        self.trip_id = trip_id
        self.destination_id = str(destination_id).strip().lower()
        self.destination_name = destination_name
        self.departure_city = departure_city.strip()
        self.budget = float(budget)
        self.travellers = int(travellers)
        self.days = int(days)
        self.nights = int(nights)
        self.travel_category = travel_category.title()
        self.transport_pref = transport_pref or f"{self.travel_category} Transport"
        self.accommodation_pref = accommodation_pref or f"{self.travel_category} Hotel"
        self.destination_type_pref = destination_type_pref
        self.status = status  # "Within Budget", "Exactly Within Budget", "Over Budget", "Pending"
        self.cost_breakdown = cost_breakdown
        self.itinerary = itinerary or []
        self.created_at = created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.confirmed = confirmed

    def clone(self) -> "Trip":
        """Create a deep copy of the trip to test modifications safely without overwriting."""
        return Trip(
            trip_id=self.trip_id,
            destination_id=self.destination_id,
            destination_name=self.destination_name,
            departure_city=self.departure_city,
            budget=self.budget,
            travellers=self.travellers,
            days=self.days,
            nights=self.nights,
            travel_category=self.travel_category,
            transport_pref=self.transport_pref,
            accommodation_pref=self.accommodation_pref,
            destination_type_pref=self.destination_type_pref,
            status=self.status,
            cost_breakdown=copy.deepcopy(self.cost_breakdown),
            itinerary=copy.deepcopy(self.itinerary),
            created_at=self.created_at,
            confirmed=self.confirmed,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert Trip to dictionary for JSON persistence."""
        breakdown_dict = None
        if self.cost_breakdown:
            breakdown_dict = {
                "transportation": self.cost_breakdown.transportation,
                "rooms_needed": self.cost_breakdown.rooms_needed,
                "accommodation": self.cost_breakdown.accommodation,
                "food": self.cost_breakdown.food,
                "activities": self.cost_breakdown.activities,
                "emergency_allowance": self.cost_breakdown.emergency_allowance,
                "total_cost": self.cost_breakdown.total_cost,
                "cost_per_person": self.cost_breakdown.cost_per_person,
                "remaining_budget": self.cost_breakdown.remaining_budget,
                "shortage": self.cost_breakdown.shortage,
            }

        return {
            "trip_id": self.trip_id,
            "destination_id": self.destination_id,
            "destination_name": self.destination_name,
            "departure_city": self.departure_city,
            "budget": self.budget,
            "travellers": self.travellers,
            "days": self.days,
            "nights": self.nights,
            "travel_category": self.travel_category,
            "transport_pref": self.transport_pref,
            "accommodation_pref": self.accommodation_pref,
            "destination_type_pref": self.destination_type_pref,
            "status": self.status,
            "cost_breakdown": breakdown_dict,
            "itinerary": self.itinerary,
            "created_at": self.created_at,
            "confirmed": self.confirmed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Trip":
        """Instantiate Trip from a dictionary."""
        bd_data = data.get("cost_breakdown")
        cost_bd = None
        if bd_data and isinstance(bd_data, dict):
            cost_bd = CostBreakdown(
                transportation=float(bd_data.get("transportation", 0.0)),
                rooms_needed=int(bd_data.get("rooms_needed", 0)),
                accommodation=float(bd_data.get("accommodation", 0.0)),
                food=float(bd_data.get("food", 0.0)),
                activities=float(bd_data.get("activities", 0.0)),
                emergency_allowance=float(bd_data.get("emergency_allowance", 0.0)),
                total_cost=float(bd_data.get("total_cost", 0.0)),
                cost_per_person=float(bd_data.get("cost_per_person", 0.0)),
                remaining_budget=float(bd_data.get("remaining_budget", 0.0)),
                shortage=float(bd_data.get("shortage", 0.0)),
            )

        return cls(
            trip_id=data.get("trip_id", ""),
            destination_id=data.get("destination_id", ""),
            destination_name=data.get("destination_name", ""),
            departure_city=data.get("departure_city", ""),
            budget=float(data.get("budget", 0.0)),
            travellers=int(data.get("travellers", 1)),
            days=int(data.get("days", 1)),
            nights=int(data.get("nights", 0)),
            travel_category=data.get("travel_category", "Standard"),
            transport_pref=data.get("transport_pref"),
            accommodation_pref=data.get("accommodation_pref"),
            destination_type_pref=data.get("destination_type_pref", "Any"),
            status=data.get("status", "Pending"),
            cost_breakdown=cost_bd,
            itinerary=data.get("itinerary", []),
            created_at=data.get("created_at"),
            confirmed=data.get("confirmed", False),
        )

    def __repr__(self) -> str:
        return f"<Trip {self.trip_id} -> {self.destination_name} ({self.status})>"
