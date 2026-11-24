"""Tests for ReportGenerator textual formatting and comparison tables."""

import pytest
from models.trip import Trip, CostBreakdown, OptimizationOption
from services.report_generator import ReportGenerator


class TestReportGenerator:
    """Test suite for text summaries and reporting tables."""

    def test_trip_text_summary_content(self):
        bd = CostBreakdown(
            transportation=5000.0,
            rooms_needed=1,
            accommodation=8000.0,
            food=6000.0,
            activities=3000.0,
            emergency_allowance=1100.0,
            total_cost=23100.0,
            cost_per_person=11550.0,
            remaining_budget=6900.0,
            shortage=0.0,
        )
        trip = Trip(
            trip_id="TRIP-TEST-RPT",
            destination_id="swat",
            destination_name="Swat",
            departure_city="Islamabad",
            budget=30000.0,
            travellers=2,
            days=3,
            nights=2,
            cost_breakdown=bd,
            itinerary=[
                {"day": 1, "title": "Welcome to Swat", "schedule": ["Depart Islamabad", "Checkin"], "night_stay": "Hotel"}
            ],
            status="Within Budget",
        )

        summary = ReportGenerator.generate_trip_text_summary(trip)
        assert "PAKISTAN TRIP PLAN - SWAT" in summary
        assert "TRIP-TEST-RPT" in summary
        assert "PKR 23,100.00" in summary
        assert "PKR 6,900.00" in summary
        assert "DAY 1" in summary

    def test_alternatives_comparison_table(self):
        bd = CostBreakdown(
            transportation=4000.0,
            rooms_needed=1,
            accommodation=6000.0,
            food=4000.0,
            activities=2000.0,
            emergency_allowance=800.0,
            total_cost=16800.0,
            cost_per_person=8400.0,
            remaining_budget=3200.0,
            shortage=0.0,
        )
        dummy_trip = Trip(
            trip_id="T1",
            destination_id="murree",
            destination_name="Murree",
            departure_city="Islamabad",
            budget=20000.0,
            travellers=2,
            days=2,
            nights=1,
            cost_breakdown=bd,
        )
        opts = [
            OptimizationOption(
                strategy="reduce_duration",
                title="Reduce to 2 Days",
                description="Shorten trip to fit budget.",
                modified_trip=dummy_trip,
                cost_breakdown=bd,
                remaining_budget=3200.0,
                score=85.5,
            )
        ]
        table = ReportGenerator.generate_alternatives_comparison_table(opts)
        assert "RANKED FEASIBLE TRIP ALTERNATIVES" in table
        assert "Reduce to 2 Days" in table
        assert "PKR 16,800.00" in table
        assert "85.5" in table

    def test_budget_text_summary_with_overspending(self):
        summary_data = {
            "budget_id": "B-001",
            "month": "December 2026",
            "budget_type": "Home & Kitchen",
            "total_available": 50000.0,
            "total_planned": 45000.0,
            "unallocated_funds": 5000.0,
            "total_actual": 52000.0,
            "remaining_balance": -2000.0,
            "savings_percentage": 0.0,
            "is_overall_overspent": True,
            "overall_shortage": 2000.0,
            "category_breakdown": [
                {
                    "category": "Rent",
                    "planned": 20000.0,
                    "actual": 25000.0,
                    "difference": -5000.0,
                    "status": "Overspent",
                }
            ],
            "overspent_categories": [
                {
                    "category": "Rent",
                    "planned": 20000.0,
                    "actual": 25000.0,
                    "overspent_by": 5000.0,
                }
            ],
        }

        output = ReportGenerator.generate_budget_text_summary(summary_data)
        assert "MONTHLY FINANCIAL REPORT - DECEMBER 2026" in output
        assert "OVERSPENT CATEGORIES DETECTED" in output
        assert "Rent: Planned PKR 20,000.00" in output
        assert "TOTAL ACTUAL EXPENSES EXCEED MONTHLY BUDGET" in output
