"""Trip feasibility checker service.

Classifies trip feasibility and provides diagnostic explanations for unaffordable plans.
"""

from typing import Tuple
from models.trip import CostBreakdown


class TripFeasibilityChecker:
    """Evaluates trip budget constraints and classifies feasibility."""

    STATUS_WITHIN_BUDGET = "Within Budget"
    STATUS_EXACTLY_BUDGET = "Exactly Within Budget"
    STATUS_OVER_BUDGET = "Over Budget"

    @classmethod
    def check_feasibility(cls, budget: float, total_cost: float) -> Tuple[str, str]:
        """Classify feasibility and return (status, detailed_explanation).

        Boundaries:
        - Within Budget: estimated cost < budget
        - Exactly Within Budget: estimated cost == budget (within 1 paisa tolerance)
        - Over Budget: estimated cost > budget
        """
        diff = round(budget - total_cost, 2)

        if abs(diff) < 0.01:
            status = cls.STATUS_EXACTLY_BUDGET
            msg = (
                f"Trip is Exactly Within Budget! Total cost matches available budget (PKR {budget:,.2f}) perfectly."
            )
        elif diff > 0:
            status = cls.STATUS_WITHIN_BUDGET
            msg = (
                f"Trip is Within Budget! Surplus remaining balance: PKR {diff:,.2f}."
            )
        else:
            status = cls.STATUS_OVER_BUDGET
            shortage = abs(diff)
            pct_over = round((shortage / budget) * 100, 1) if budget > 0 else 100.0
            msg = (
                f"Trip is Over Budget! Budget deficit: PKR {shortage:,.2f} "
                f"({pct_over}% above your budget of PKR {budget:,.2f})."
            )

        return status, msg

    @classmethod
    def explain_shortage(
        cls,
        budget: float,
        breakdown: CostBreakdown,
    ) -> str:
        """Provide a detailed diagnostic explanation of the budget shortage."""
        if breakdown.total_cost <= budget:
            return "Trip is affordable. No shortage exists."

        shortage = round(breakdown.total_cost - budget, 2)
        pct_over = round((shortage / budget) * 100, 1) if budget > 0 else 100.0

        components = [
            ("Transportation", breakdown.transportation),
            ("Accommodation", breakdown.accommodation),
            ("Food", breakdown.food),
            ("Activities & Misc", breakdown.activities),
            ("Emergency Allowance", breakdown.emergency_allowance),
        ]
        # Sort by cost descending
        components.sort(key=lambda x: x[1], reverse=True)
        top_driver = components[0]

        explanation = (
            f"Budget Shortage Diagnostic:\n"
            f"  * Available Budget : PKR {budget:,.2f}\n"
            f"  * Estimated Cost   : PKR {breakdown.total_cost:,.2f}\n"
            f"  * Shortage (Deficit): PKR {shortage:,.2f} ({pct_over}% above budget)\n"
            f"  * Primary Cost Driver: {top_driver[0]} at PKR {top_driver[1]:,.2f} "
            f"({round((top_driver[1]/breakdown.total_cost)*100, 1)}% of total cost).\n"
            f"  * Note: Base costs without emergency allowance amount to "
            f"PKR {round(breakdown.total_cost - breakdown.emergency_allowance, 2):,.2f}."
        )
        return explanation
