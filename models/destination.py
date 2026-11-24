"""Destination model representing a Pakistani travel destination."""

import math
from typing import Dict, Any, List, Optional


class Destination:
    """Represents a travel destination with cost metrics and travel categories.

    Attributes:
        id: Unique alphanumeric identifier (e.g. 'murree').
        name: Common name of the destination (e.g. 'Murree').
        region: Geographic administrative region.
        category: Destination category (e.g. 'Mountains', 'Historical Places', 'Lakes & Nature').
        description: Informative description.
        room_capacity: Standard capacity of travelers per room (default 2).
        base_transport_cost: Estimated transport cost per person.
        base_accommodation_cost: Estimated accommodation cost per room per night.
        base_food_cost: Estimated food cost per person per day.
        base_activities_cost: Estimated activities cost per person per day.
        transport_options: Dict of category to transport description.
        accommodation_options: Dict of category to accommodation description.
        category_multipliers: Multipliers for Budget, Standard, Premium tiers.
        attractions: List of key attractions and activities.
    """

    def __init__(
        self,
        id: str,
        name: str,
        region: str,
        category: str,
        description: str,
        room_capacity: int = 2,
        base_transport_cost: float = 0.0,
        base_accommodation_cost: float = 0.0,
        base_food_cost: float = 0.0,
        base_activities_cost: float = 0.0,
        transport_options: Optional[Dict[str, str]] = None,
        accommodation_options: Optional[Dict[str, str]] = None,
        category_multipliers: Optional[Dict[str, Dict[str, float]]] = None,
        attractions: Optional[List[str]] = None,
    ):
        self.id = str(id).strip().lower()
        self.name = str(name).strip()
        self.region = str(region).strip()
        self.category = str(category).strip()
        self.description = str(description).strip()
        self.room_capacity = max(1, int(room_capacity))
        self.base_transport_cost = float(base_transport_cost)
        self.base_accommodation_cost = float(base_accommodation_cost)
        self.base_food_cost = float(base_food_cost)
        self.base_activities_cost = float(base_activities_cost)
        self.transport_options = transport_options or {}
        self.accommodation_options = accommodation_options or {}
        self.category_multipliers = category_multipliers or {
            "Budget": {"transport": 0.8, "accommodation": 0.7, "food": 0.8, "activities": 0.8},
            "Standard": {"transport": 1.0, "accommodation": 1.0, "food": 1.0, "activities": 1.0},
            "Premium": {"transport": 1.8, "accommodation": 2.0, "food": 1.5, "activities": 1.5},
        }
        self.attractions = attractions or []

    def calculate_required_rooms(self, travellers: int) -> int:
        """Calculate required rooms using ceiling division."""
        if travellers <= 0:
            return 0
        return math.ceil(travellers / self.room_capacity)

    def get_tier_multiplier(self, category: str, component: str) -> float:
        """Get multiplier for a given category and component."""
        cat_key = category.title() if category else "Standard"
        if cat_key in self.category_multipliers and component in self.category_multipliers[cat_key]:
            return self.category_multipliers[cat_key][component]
        return 1.0

    def get_transport_description(self, category: str) -> str:
        """Return the transport option description for category."""
        cat_key = category.title() if category else "Standard"
        return self.transport_options.get(cat_key, f"{cat_key} Transport")

    def get_accommodation_description(self, category: str) -> str:
        """Return the accommodation option description for category."""
        cat_key = category.title() if category else "Standard"
        return self.accommodation_options.get(cat_key, f"{cat_key} Room")

    def to_dict(self) -> Dict[str, Any]:
        """Convert Destination instance to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "region": self.region,
            "category": self.category,
            "description": self.description,
            "room_capacity": self.room_capacity,
            "base_transport_cost": self.base_transport_cost,
            "base_accommodation_cost": self.base_accommodation_cost,
            "base_food_cost": self.base_food_cost,
            "base_activities_cost": self.base_activities_cost,
            "transport_options": self.transport_options,
            "accommodation_options": self.accommodation_options,
            "category_multipliers": self.category_multipliers,
            "attractions": self.attractions,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Destination":
        """Instantiate Destination from dictionary."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            region=data.get("region", ""),
            category=data.get("category", ""),
            description=data.get("description", ""),
            room_capacity=data.get("room_capacity", 2),
            base_transport_cost=data.get("base_transport_cost", 0.0),
            base_accommodation_cost=data.get("base_accommodation_cost", 0.0),
            base_food_cost=data.get("base_food_cost", 0.0),
            base_activities_cost=data.get("base_activities_cost", 0.0),
            transport_options=data.get("transport_options", {}),
            accommodation_options=data.get("accommodation_options", {}),
            category_multipliers=data.get("category_multipliers", {}),
            attractions=data.get("attractions", []),
        )

    def __repr__(self) -> str:
        return f"<Destination {self.name} ({self.category})>"
