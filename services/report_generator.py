"""Report generator service for formatting text summaries and comparison tables."""

from typing import List, Dict, Any
from models.trip import Trip, OptimizationOption
from utils.calculations import format_currency


class ReportGenerator:
    """Generates formatted text reports and terminal tables."""

    @staticmethod
    def generate_trip_text_summary(trip: Trip) -> str:
        """Format an extensive textual summary of a trip plan."""
        bd = trip.cost_breakdown
        if not bd:
            return f"Trip {trip.trip_id} has no cost calculation breakdown."

        lines = [
            "=" * 72,
            f"          PAKISTAN TRIP PLAN - {trip.destination_name.upper()}",
            "=" * 72,
            f"Trip ID          : {trip.trip_id}",
            f"Departure City   : {trip.departure_city}",
            f"Destination      : {trip.destination_name} (Category: {trip.destination_type_pref})",
            f"Travellers       : {trip.travellers} person(s)",
            f"Duration         : {trip.days} Day(s), {trip.nights} Night(s)",
            f"Travel Category  : {trip.travel_category}",
            f"Transport Choice : {trip.transport_pref}",
            f"Hotel Selection  : {trip.accommodation_pref}",
            f"Required Rooms   : {bd.rooms_needed} room(s)",
            "-" * 72,
            "ESTIMATED FINANCIAL BREAKDOWN (PKR):",
            f"  1. Transportation Cost      : {format_currency(bd.transportation):>16}",
            f"  2. Accommodation Cost       : {format_currency(bd.accommodation):>16}",
            f"  3. Food & Dining Cost       : {format_currency(bd.food):>16}",
            f"  4. Activities & Sightseeing : {format_currency(bd.activities):>16}",
            f"  5. Emergency Allowance (5%) : {format_currency(bd.emergency_allowance):>16}",
            "-" * 72,
            f"  TOTAL ESTIMATED COST        : {format_currency(bd.total_cost):>16}",
            f"  Cost Per Person             : {format_currency(bd.cost_per_person):>16}",
            f"  Available Budget            : {format_currency(trip.budget):>16}",
        ]

        if bd.remaining_budget >= 0:
            lines.append(f"  Surplus Remaining Balance   : {format_currency(bd.remaining_budget):>16}")
        else:
            lines.append(f"  BUDGET SHORTAGE (Deficit)   : {format_currency(bd.shortage):>16}")

        lines.extend([
            "-" * 72,
            f"FEASIBILITY STATUS: {trip.status.upper()}",
            "=" * 72,
        ])

        if trip.itinerary:
            lines.extend([
                "",
                "DAY-WISE ITINERARY:",
                "-" * 72,
            ])
            for item in trip.itinerary:
                lines.append(f"\n[DAY {item['day']}] : {item['title']}")
                for step in item.get("schedule", []):
                    lines.append(f"  * {step}")
                lines.append(f"  Overnight Stay: {item.get('night_stay', 'N/A')}")
            lines.append("-" * 72)

        return "\n".join(lines)

    @staticmethod
    def generate_alternatives_comparison_table(alternatives: List[OptimizationOption]) -> str:
        """Format a ranked comparison table for trip optimization options."""
        if not alternatives:
            return "No feasible alternatives found within your specified budget."

        lines = [
            "=" * 88,
            "               RANKED FEASIBLE TRIP ALTERNATIVES (WITHIN BUDGET)",
            "=" * 88,
            f"{'Rank':<5} | {'Option Title':<34} | {'Total Cost':<14} | {'Surplus':<14} | {'Score':<6}",
            "-" * 88,
        ]

        for i, opt in enumerate(alternatives, 1):
            title = (opt.title[:32] + "..") if len(opt.title) > 34 else opt.title
            lines.append(
                f"{i:<5} | {title:<34} | {format_currency(opt.cost_breakdown.total_cost):<14} | "
                f"{format_currency(opt.remaining_budget):<14} | {opt.score:<6.1f}"
            )
            lines.append(f"      Details: {opt.description}")
            lines.append("-" * 88)

        return "\n".join(lines)

    @staticmethod
    def generate_budget_text_summary(summary: Dict[str, Any]) -> str:
        """Format an extensive textual summary of a monthly budget."""
        lines = [
            "=" * 82,
            f"        MONTHLY FINANCIAL REPORT - {summary['month'].upper()} ({summary['budget_type'].upper()})",
            "=" * 82,
            f"Budget ID           : {summary['budget_id']}",
            f"Total Income/Budget : {format_currency(summary['total_available'])}",
            f"Total Planned       : {format_currency(summary['total_planned'])}",
            f"Unallocated Amount  : {format_currency(summary['unallocated_funds'])}",
            f"Total Actual Spent  : {format_currency(summary['total_actual'])}",
            f"Remaining Balance   : {format_currency(summary['remaining_balance'])}",
            f"Savings Percentage  : {summary['savings_percentage']:.1f}%",
            "-" * 82,
            f"{'Category':<28} | {'Planned':>12} | {'Actual':>12} | {'Difference':>12} | {'Status':<10}",
            "-" * 82,
        ]

        for cat in summary["category_breakdown"]:
            c_name = (cat["category"][:26] + "..") if len(cat["category"]) > 28 else cat["category"]
            lines.append(
                f"{c_name:<28} | {format_currency(cat['planned']):>12} | "
                f"{format_currency(cat['actual']):>12} | {format_currency(cat['difference']):>12} | {cat['status']:<10}"
            )

        lines.append("=" * 82)

        if summary["overspent_categories"]:
            lines.extend([
                "WARNING: OVERSPENT CATEGORIES DETECTED:",
                "-" * 82,
            ])
            for o in summary["overspent_categories"]:
                lines.append(
                    f"  ! {o['category']}: Planned {format_currency(o['planned'])}, "
                    f"Actual {format_currency(o['actual'])} -> Overspent by {format_currency(o['overspent_by'])}"
                )
            lines.append("-" * 82)

        if summary["is_overall_overspent"]:
            lines.append(
                f"ALERT: TOTAL ACTUAL EXPENSES EXCEED MONTHLY BUDGET BY {format_currency(summary['overall_shortage'])}!"
            )
            lines.append("=" * 82)

        return "\n".join(lines)
