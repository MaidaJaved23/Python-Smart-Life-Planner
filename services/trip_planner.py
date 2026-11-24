"""Trip planner service orchestrating trip workflows, modifications, and itineraries."""

from collections import deque
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import uuid

from models.destination import Destination
from models.trip import Trip, CostBreakdown, OptimizationOption
from services.trip_calculator import TripCostCalculator
from services.feasibility_checker import TripFeasibilityChecker
from services.trip_optimizer import TripOptimizer
from utils.data_manager import DataManager


class TripPlanner:
    """Manages the full lifecycle of Pakistan Trip Planning.

    Features:
    - Multi-destination database management.
    - Day and night calculation handling.
    - Dynamic non-destructive modification with rollback using collections.deque.
    - Adaptive day-wise itinerary generation.
    - Confirmation and persistence.
    """

    def __init__(self, data_manager: Optional[DataManager] = None):
        self.data_manager = data_manager or DataManager()
        self.destinations: Dict[str, Destination] = {}
        self.confirmed_trips: List[Trip] = []
        # Audit history / state tracking using collections.deque (capacity 25)
        self.history: deque = deque(maxlen=25)
        self.load_destinations()
        self.load_saved_trips()

    def load_destinations(self) -> None:
        """Load destinations from JSON data store."""
        raw_list = self.data_manager.load_destinations_data()
        self.destinations = {}
        for item in raw_list:
            dest = Destination.from_dict(item)
            self.destinations[dest.id] = dest

    def load_saved_trips(self) -> None:
        """Load confirmed trips from storage."""
        raw_list = self.data_manager.load_trips_data()
        self.confirmed_trips = [Trip.from_dict(d) for d in raw_list]

    def get_destination(self, dest_id: str) -> Optional[Destination]:
        """Find destination by ID (case-insensitive) or name."""
        clean = str(dest_id).strip().lower()
        if clean in self.destinations:
            return self.destinations[clean]
        for dest in self.destinations.values():
            if dest.name.lower() == clean:
                return dest
        return None

    def get_destinations_by_category(self, category: str = "Any") -> List[Destination]:
        """Filter destinations by preferred destination type."""
        cat_clean = category.strip().lower()
        if cat_clean == "any":
            return list(self.destinations.values())
        return [
            d for d in self.destinations.values() if d.category.lower() == cat_clean
        ]

    def create_trip_plan(
        self,
        budget: float,
        travellers: int,
        destination_name_or_id: str,
        departure_city: str,
        days: int,
        nights: int,
        travel_category: str = "Standard",
        transport_pref: Optional[str] = None,
        accommodation_pref: Optional[str] = None,
        destination_type_pref: str = "Any",
    ) -> Tuple[Trip, CostBreakdown, str, str]:
        """Create a new trip plan, calculate costs, and determine feasibility.

        Returns:
            (trip_object, cost_breakdown, feasibility_status, feasibility_message)
        """
        dest = self.get_destination(destination_name_or_id)
        if not dest:
            raise ValueError(f"Destination '{destination_name_or_id}' was not found in database.")

        cost_breakdown = TripCostCalculator.calculate(
            destination=dest,
            travellers=travellers,
            days=days,
            nights=nights,
            travel_category=travel_category,
            budget=budget,
        )

        status, status_msg = TripFeasibilityChecker.check_feasibility(
            budget=budget, total_cost=cost_breakdown.total_cost
        )

        t_pref = transport_pref or dest.get_transport_description(travel_category)
        a_pref = accommodation_pref or dest.get_accommodation_description(travel_category)

        trip_id = f"TRIP-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        trip = Trip(
            trip_id=trip_id,
            destination_id=dest.id,
            destination_name=dest.name,
            departure_city=departure_city,
            budget=budget,
            travellers=travellers,
            days=days,
            nights=nights,
            travel_category=travel_category,
            transport_pref=t_pref,
            accommodation_pref=a_pref,
            destination_type_pref=destination_type_pref,
            status=status,
            cost_breakdown=cost_breakdown,
            confirmed=False,
        )

        trip.itinerary = self.generate_day_wise_itinerary(trip, dest)
        self.history.append(f"Created trip plan {trip.trip_id} for {dest.name}")
        return trip, cost_breakdown, status, status_msg

    def modify_trip_parameters(
        self,
        base_trip: Trip,
        **updates: Any,
    ) -> Tuple[Trip, CostBreakdown, str, str]:
        """Modify trip parameters non-destructively.

        Clones the base trip, applies updates, recalculates expenses and feasibility.
        Returns a new candidate Trip object without overwriting the base trip.
        """
        candidate = base_trip.clone()

        if "budget" in updates and updates["budget"] is not None:
            candidate.budget = float(updates["budget"])
        if "travellers" in updates and updates["travellers"] is not None:
            candidate.travellers = int(updates["travellers"])
        if "days" in updates and updates["days"] is not None:
            candidate.days = int(updates["days"])
        if "nights" in updates and updates["nights"] is not None:
            candidate.nights = int(updates["nights"])
        if "travel_category" in updates and updates["travel_category"]:
            candidate.travel_category = str(updates["travel_category"]).title()
        if "departure_city" in updates and updates["departure_city"]:
            candidate.departure_city = str(updates["departure_city"]).strip()

        if "destination" in updates and updates["destination"]:
            dest = self.get_destination(str(updates["destination"]))
            if not dest:
                raise ValueError(f"Destination '{updates['destination']}' not recognized.")
            candidate.destination_id = dest.id
            candidate.destination_name = dest.name
        else:
            dest = self.get_destination(candidate.destination_id)

        # Update preferences if category changed or specific options provided
        if "transport_pref" in updates and updates["transport_pref"]:
            candidate.transport_pref = updates["transport_pref"]
        elif "travel_category" in updates:
            candidate.transport_pref = dest.get_transport_description(candidate.travel_category)

        if "accommodation_pref" in updates and updates["accommodation_pref"]:
            candidate.accommodation_pref = updates["accommodation_pref"]
        elif "travel_category" in updates:
            candidate.accommodation_pref = dest.get_accommodation_description(candidate.travel_category)

        # Recalculate
        bd = TripCostCalculator.calculate(
            destination=dest,
            travellers=candidate.travellers,
            days=candidate.days,
            nights=candidate.nights,
            travel_category=candidate.travel_category,
            budget=candidate.budget,
        )

        status, status_msg = TripFeasibilityChecker.check_feasibility(
            budget=candidate.budget, total_cost=bd.total_cost
        )

        candidate.cost_breakdown = bd
        candidate.status = status
        candidate.itinerary = self.generate_day_wise_itinerary(candidate, dest)

        self.history.append(
            f"Evaluated modification candidate for {candidate.trip_id} (Status: {status})"
        )
        return candidate, bd, status, status_msg

    def confirm_and_save_trip(self, trip: Trip) -> bool:
        """Confirm final trip plan and persist to disk."""
        trip.confirmed = True
        dest = self.get_destination(trip.destination_id)
        if dest and not trip.itinerary:
            trip.itinerary = self.generate_day_wise_itinerary(trip, dest)

        # Update in-memory list
        existing_idx = next(
            (i for i, t in enumerate(self.confirmed_trips) if t.trip_id == trip.trip_id),
            None,
        )
        if existing_idx is not None:
            self.confirmed_trips[existing_idx] = trip
        else:
            self.confirmed_trips.append(trip)

        # Persist to disk
        data_to_save = [t.to_dict() for t in self.confirmed_trips]
        success = self.data_manager.save_trips_data(data_to_save)
        if success:
            self.history.append(f"Confirmed and saved trip {trip.trip_id}")
        return success

    def get_trip_alternatives(self, trip: Trip) -> List[OptimizationOption]:
        """Generate verified optimization alternatives when trip is over budget."""
        dest = self.get_destination(trip.destination_id)
        if not dest:
            return []
        all_destinations = list(self.destinations.values())
        return TripOptimizer.generate_all_alternatives(trip, dest, all_destinations)

    def generate_day_wise_itinerary(
        self, trip: Trip, destination: Destination
    ) -> List[Dict[str, Any]]:
        """Generate adaptive day-wise itinerary matching exact duration and destination attractions."""
        days = trip.days
        nights = trip.nights
        attractions = destination.attractions or [
            "Scenic viewpoints and landscape exploration",
            "Local cultural heritage sightseeing",
            "Traditional bazaar and handicraft shopping",
            "Regional culinary specialties and evening dining",
        ]

        itinerary: List[Dict[str, Any]] = []

        if days == 1 and nights == 0:
            # Single Day Excursion / Zero-night trip
            itinerary.append(
                {
                    "day": 1,
                    "title": f"Day Trip Excursion to {destination.name}",
                    "schedule": [
                        f"06:30 AM - Departure from {trip.departure_city} via {trip.transport_pref}.",
                        f"10:00 AM - Arrival in {destination.name}; morning tea and panoramic landscape view.",
                        f"11:00 AM - Sightseeing: {attractions[0] if len(attractions) > 0 else 'Local sightseeing'}.",
                        f"01:30 PM - Lunch featuring local specialties ({trip.travel_category} dining).",
                        f"03:00 PM - Afternoon exploration: {attractions[1] if len(attractions) > 1 else 'Market walk'}.",
                        f"05:30 PM - Evening tea and photography session at scenic viewpoint.",
                        f"06:30 PM - Board return journey back to {trip.departure_city}.",
                        f"10:00 PM - Safe arrival in {trip.departure_city}.",
                    ],
                    "night_stay": "No overnight stay (Same day return trip)",
                }
            )
            return itinerary

        # Multi-day trip
        attr_idx = 0
        for day_num in range(1, days + 1):
            if day_num == 1:
                # Arrival day
                first_attr = attractions[0] if attractions else "local sights"
                attr_idx += 1
                stay_info = (
                    f"Overnight at {trip.accommodation_pref}"
                    if nights >= 1
                    else "No overnight stay"
                )
                itinerary.append(
                    {
                        "day": 1,
                        "title": f"Departure from {trip.departure_city} & Welcome to {destination.name}",
                        "schedule": [
                            f"07:00 AM - Morning departure from {trip.departure_city} via {trip.transport_pref}.",
                            f"01:00 PM - Arrival in {destination.name}; welcome refreshments and orientation.",
                            f"02:00 PM - Check-in at {trip.accommodation_pref} and relaxation.",
                            f"04:00 PM - Initial exploration: {first_attr}.",
                            f"07:30 PM - Dinner featuring regional cuisine followed by an evening walk.",
                        ],
                        "night_stay": stay_info,
                    }
                )
            elif day_num == days:
                # Last day / Return journey
                last_attr = (
                    attractions[attr_idx % len(attractions)]
                    if attractions
                    else "souvenir market"
                )
                itinerary.append(
                    {
                        "day": day_num,
                        "title": f"Farewell {destination.name} & Return to {trip.departure_city}",
                        "schedule": [
                            "08:00 AM - Breakfast and check-out from hotel.",
                            f"09:30 AM - Morning visit: {last_attr} & souvenir shopping.",
                            "12:00 PM - Farewell lunch with scenic panorama.",
                            f"01:30 PM - Departure on return journey towards {trip.departure_city}.",
                            f"08:30 PM - Expected safe arrival in {trip.departure_city}.",
                        ],
                        "night_stay": "Trip concluded - Return to home city",
                    }
                )
            else:
                # Intermediate full exploration days
                cur_attr_1 = (
                    attractions[attr_idx % len(attractions)]
                    if attractions
                    else "Mountain viewpoint"
                )
                attr_idx += 1
                cur_attr_2 = (
                    attractions[attr_idx % len(attractions)]
                    if attractions
                    else "Cultural discovery"
                )
                attr_idx += 1

                stay_info = (
                    f"Overnight at {trip.accommodation_pref}"
                    if day_num <= nights
                    else "No overnight stay"
                )
                itinerary.append(
                    {
                        "day": day_num,
                        "title": f"Full Day Discovery: {cur_attr_1}",
                        "schedule": [
                            "08:00 AM - Breakfast at hotel.",
                            f"09:30 AM - Morning excursion: {cur_attr_1}.",
                            "01:00 PM - Traditional local lunch and photography session.",
                            f"02:30 PM - Afternoon adventure: {cur_attr_2}.",
                            "06:30 PM - Sunset observation from vantage point.",
                            "08:00 PM - Dinner and leisure time.",
                        ],
                        "night_stay": stay_info,
                    }
                )

        return itinerary
