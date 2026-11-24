"""Reusable financial and mathematical calculation functions."""

import math
from typing import Tuple


def format_currency(amount: float) -> str:
    """Format floating point amount into readable PKR currency string."""
    try:
        val = float(amount)
        if abs(val) < 0.005:
            val = 0.0
        return f"PKR {val:,.2f}"
    except (ValueError, TypeError):
        return f"PKR {amount}"


def calculate_rooms_needed(travellers: int, room_capacity: int = 2) -> int:
    """Calculate required rooms using ceiling division.

    Edge cases:
    - 0 travellers -> 0 rooms
    - capacity <= 0 -> defaults to capacity 1
    """
    if travellers <= 0:
        return 0
    cap = max(1, room_capacity)
    return math.ceil(travellers / cap)


def calculate_transport_cost(base_cost: float, multiplier: float, travellers: int) -> float:
    """Calculate transportation cost = cost per person × travellers."""
    if travellers <= 0 or base_cost <= 0:
        return 0.0
    return round(base_cost * multiplier * travellers, 2)


def calculate_accommodation_cost(
    base_room_cost: float,
    multiplier: float,
    rooms: int,
    nights: int,
) -> float:
    """Calculate accommodation cost = room cost × rooms × nights.

    CRITICAL RULE: A zero-night trip MUST have zero accommodation cost!
    """
    if nights <= 0 or rooms <= 0 or base_room_cost <= 0:
        return 0.0
    return round(base_room_cost * multiplier * rooms * nights, 2)


def calculate_food_cost(
    base_food_cost: float,
    multiplier: float,
    travellers: int,
    days: int,
) -> float:
    """Calculate food cost = food cost per person/day × travellers × days."""
    if travellers <= 0 or days <= 0 or base_food_cost <= 0:
        return 0.0
    return round(base_food_cost * multiplier * travellers * days, 2)


def calculate_activities_cost(
    base_activity_cost: float,
    multiplier: float,
    travellers: int,
    days: int = 1,
) -> float:
    """Calculate activities and misc expenses = activity cost per person/day × travellers × days."""
    if travellers <= 0 or days <= 0 or base_activity_cost <= 0:
        return 0.0
    return round(base_activity_cost * multiplier * travellers * days, 2)


def calculate_emergency_allowance(subtotal: float, percentage: float = 0.05) -> float:
    """Calculate emergency allowance using a defined percentage of base expenses."""
    if subtotal <= 0 or percentage <= 0:
        return 0.0
    return round(subtotal * percentage, 2)


def calculate_total_trip_cost(
    transport: float,
    accommodation: float,
    food: float,
    activities: float,
    emergency_allowance: float,
) -> float:
    """Calculate total estimated trip cost."""
    return round(transport + accommodation + food + activities + emergency_allowance, 2)


def calculate_cost_per_person(total_cost: float, travellers: int) -> float:
    """Calculate cost per person."""
    if travellers <= 0:
        return 0.0
    return round(total_cost / travellers, 2)


def calculate_savings_percentage(savings: float, total_income: float) -> float:
    """Calculate savings percentage of total income."""
    if total_income <= 0:
        return 0.0
    return round((savings / total_income) * 100, 2)


def calculate_savings(total_income: float, total_expenses: float) -> Tuple[float, float]:
    """Calculate savings amount and savings percentage.

    Returns:
        (savings_amount, savings_percentage)
    """
    savings = round(total_income - total_expenses, 2)
    pct = calculate_savings_percentage(savings, total_income)
    return savings, pct

