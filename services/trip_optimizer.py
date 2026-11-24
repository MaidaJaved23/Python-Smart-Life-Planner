"""Trip optimizer service.

Calculates realistic alternatives dynamically when a trip exceeds available budget.
Strictly ensures that only fully recalculated, truly affordable alternatives are recommended.
"""

from typing import List, Dict, Optional, Tuple
from models.destination import Destination
from models.trip import Trip, CostBreakdown, OptimizationOption
from services.trip_calculator import TripCostCalculator


class TripOptimizer:
    """Calculates intelligent and mathematically verified alternatives for over-budget trips."""

    @classmethod
    def calculate_increase_budget_option(
        cls,
        trip: Trip,
        breakdown: CostBreakdown,
    ) -> Dict[str, float]:
        """Calculate required budget increase."""
        shortage = round(breakdown.total_cost - trip.budget, 2)
        return {
            "required_budget": breakdown.total_cost,
            "additional_amount": shortage,
            "cost_per_person": breakdown.cost_per_person,
        }

    @classmethod
    def find_feasible_travellers_reduction(
        cls,
        trip: Trip,
        destination: Destination,
    ) -> Optional[OptimizationOption]:
        """Find the maximum number of travellers that can travel within budget."""
        for t in range(trip.travellers - 1, 0, -1):
            bd = TripCostCalculator.calculate(
                destination=destination,
                travellers=t,
                days=trip.days,
                nights=trip.nights,
                travel_category=trip.travel_category,
                budget=trip.budget,
            )
            if bd.total_cost <= trip.budget:
                mod_trip = trip.clone()
                mod_trip.travellers = t
                mod_trip.cost_breakdown = bd
                mod_trip.status = "Within Budget"
                surplus = round(trip.budget - bd.total_cost, 2)
                score = (t / trip.travellers) * 50 + (1 - bd.total_cost / trip.budget) * 20
                return OptimizationOption(
                    strategy="reduce_travellers",
                    title=f"Reduce Travellers to {t} Person(s)",
                    description=(
                        f"Travel with {t} person(s) instead of {trip.travellers}. "
                        f"Recalculated cost: PKR {bd.total_cost:,.2f} (Savings: PKR {surplus:,.2f})."
                    ),
                    modified_trip=mod_trip,
                    cost_breakdown=bd,
                    remaining_budget=surplus,
                    score=round(score, 2),
                )
        return None

    @classmethod
    def find_feasible_duration_reduction(
        cls,
        trip: Trip,
        destination: Destination,
    ) -> Optional[OptimizationOption]:
        """Find feasible reduced duration (days and nights) within budget."""
        # Try decreasing days from trip.days - 1 down to 1
        best_option = None
        for d in range(trip.days - 1, 0, -1):
            # Typical night counts for d days: d-1 (overnights) or 0 (if day trip)
            candidate_nights = [max(0, d - 1)]
            if d == 1 and 0 not in candidate_nights:
                candidate_nights.append(0)

            for n in candidate_nights:
                bd = TripCostCalculator.calculate(
                    destination=destination,
                    travellers=trip.travellers,
                    days=d,
                    nights=n,
                    travel_category=trip.travel_category,
                    budget=trip.budget,
                )
                if bd.total_cost <= trip.budget:
                    mod_trip = trip.clone()
                    mod_trip.days = d
                    mod_trip.nights = n
                    mod_trip.cost_breakdown = bd
                    mod_trip.status = "Within Budget"
                    surplus = round(trip.budget - bd.total_cost, 2)
                    score = (d / trip.days) * 45 + (1 - bd.total_cost / trip.budget) * 25
                    night_str = f"{n} night" if n == 1 else f"{n} nights"
                    day_str = f"{d} day" if d == 1 else f"{d} days"
                    return OptimizationOption(
                        strategy="reduce_duration",
                        title=f"Reduce Duration to {day_str}, {night_str}",
                        description=(
                            f"Shorten trip to {day_str} and {night_str} for all {trip.travellers} travellers. "
                            f"Recalculated cost: PKR {bd.total_cost:,.2f} (Surplus: PKR {surplus:,.2f})."
                        ),
                        modified_trip=mod_trip,
                        cost_breakdown=bd,
                        remaining_budget=surplus,
                        score=round(score, 2),
                    )
        return None

    @classmethod
    def find_feasible_preference_adjustment(
        cls,
        trip: Trip,
        destination: Destination,
    ) -> Optional[OptimizationOption]:
        """Downgrade travel category tier to reduce costs."""
        current_cat = trip.travel_category.title()
        downgrade_candidates = []
        if current_cat == "Premium":
            downgrade_candidates = ["Standard", "Budget"]
        elif current_cat == "Standard":
            downgrade_candidates = ["Budget"]

        for cat in downgrade_candidates:
            bd = TripCostCalculator.calculate(
                destination=destination,
                travellers=trip.travellers,
                days=trip.days,
                nights=trip.nights,
                travel_category=cat,
                budget=trip.budget,
            )
            if bd.total_cost <= trip.budget:
                mod_trip = trip.clone()
                mod_trip.travel_category = cat
                mod_trip.transport_pref = destination.get_transport_description(cat)
                mod_trip.accommodation_pref = destination.get_accommodation_description(cat)
                mod_trip.cost_breakdown = bd
                mod_trip.status = "Within Budget"
                surplus = round(trip.budget - bd.total_cost, 2)
                score = 50.0 + (1 - bd.total_cost / trip.budget) * 30
                return OptimizationOption(
                    strategy="adjust_preferences",
                    title=f"Switch to {cat} Travel Category",
                    description=(
                        f"Change travel tier from {current_cat} to {cat} while keeping destination, "
                        f"travellers, and duration intact. Recalculated cost: PKR {bd.total_cost:,.2f} "
                        f"(Surplus: PKR {surplus:,.2f})."
                    ),
                    modified_trip=mod_trip,
                    cost_breakdown=bd,
                    remaining_budget=surplus,
                    score=round(score, 2),
                )
        return None

    @classmethod
    def find_feasible_destination_alternatives(
        cls,
        trip: Trip,
        all_destinations: List[Destination],
    ) -> List[OptimizationOption]:
        """Find alternative destinations that fit the budget with identical travellers and duration."""
        affordable_options: List[OptimizationOption] = []

        for dest in all_destinations:
            if dest.id.lower() == trip.destination_id.lower():
                continue

            # Check at original category
            for cat in [trip.travel_category, "Budget"]:
                bd = TripCostCalculator.calculate(
                    destination=dest,
                    travellers=trip.travellers,
                    days=trip.days,
                    nights=trip.nights,
                    travel_category=cat,
                    budget=trip.budget,
                )
                if bd.total_cost <= trip.budget:
                    mod_trip = trip.clone()
                    mod_trip.destination_id = dest.id
                    mod_trip.destination_name = dest.name
                    mod_trip.travel_category = cat
                    mod_trip.transport_pref = dest.get_transport_description(cat)
                    mod_trip.accommodation_pref = dest.get_accommodation_description(cat)
                    mod_trip.cost_breakdown = bd
                    mod_trip.status = "Within Budget"
                    surplus = round(trip.budget - bd.total_cost, 2)

                    # Score calculation
                    pref_match = 15.0 if trip.destination_type_pref.lower() in [
                        "any",
                        dest.category.lower(),
                    ] else 0.0
                    score = 40.0 + pref_match + (1 - bd.total_cost / trip.budget) * 20

                    tier_info = f" ({cat} tier)" if cat != trip.travel_category else ""
                    opt = OptimizationOption(
                        strategy="change_destination",
                        title=f"Change Destination to {dest.name}{tier_info}",
                        description=(
                            f"Travel to {dest.name} ({dest.category}, {dest.region}) with "
                            f"{trip.travellers} travellers for {trip.days} days / {trip.nights} nights. "
                            f"Recalculated cost: PKR {bd.total_cost:,.2f} (Surplus: PKR {surplus:,.2f})."
                        ),
                        modified_trip=mod_trip,
                        cost_breakdown=bd,
                        remaining_budget=surplus,
                        score=round(score, 2),
                    )
                    affordable_options.append(opt)
                    break  # Found best category for this destination

        return affordable_options

    @classmethod
    def generate_all_alternatives(
        cls,
        trip: Trip,
        destination: Destination,
        all_destinations: List[Destination],
    ) -> List[OptimizationOption]:
        """Aggregate, verify, and rank all affordable optimization alternatives.

        Guaranteed: Every option returned strictly satisfies total_cost <= available_budget.
        """
        raw_options: List[OptimizationOption] = []

        # 1. Adjust Preferences (category downgrade)
        pref_opt = cls.find_feasible_preference_adjustment(trip, destination)
        if pref_opt:
            raw_options.append(pref_opt)

        # 2. Reduce Duration
        dur_opt = cls.find_feasible_duration_reduction(trip, destination)
        if dur_opt:
            raw_options.append(dur_opt)

        # 3. Reduce Travellers
        trav_opt = cls.find_feasible_travellers_reduction(trip, destination)
        if trav_opt:
            raw_options.append(trav_opt)

        # 4. Change Destination
        dest_opts = cls.find_feasible_destination_alternatives(trip, all_destinations)
        raw_options.extend(dest_opts)

        # CRITICAL FILTER: Ensure absolute affordability (no false positives!)
        verified_options = [
            opt for opt in raw_options if opt.cost_breakdown.total_cost <= trip.budget
        ]

        # Rank alternatives by score descending, then by remaining budget descending
        verified_options.sort(
            key=lambda x: (x.score, x.remaining_budget),
            reverse=True,
        )

        return verified_options
