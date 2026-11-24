"""Tests for PDFReportGenerator and compulsory PDF requirements."""

import os
import pytest
from models.trip import Trip, CostBreakdown
from pdf.pdf_generator import PDFReportGenerator
from utils.data_manager import DataManager


@pytest.fixture
def pdf_fixture(tmp_path):
    dm = DataManager(base_dir=str(tmp_path))
    # Developer config
    dm.save_developer_config({
        "developer_name": "Shahzaib Dev",
        "github_username": "shahzaib-dev",
        "email": "shahzaib@smartlifeplanner.pk",
    })
    generator = PDFReportGenerator(data_manager=dm)
    return generator, dm, tmp_path


class TestPDFReportGenerator:
    """Test suite for ReportLab PDF compilation, footers, and validation gates."""

    def test_unconfirmed_trip_rejects_pdf_generation(self, pdf_fixture):
        """CRITICAL: PDF reports cannot be generated before user confirms plan."""
        generator, dm, _ = pdf_fixture
        unconfirmed_trip = Trip(
            trip_id="TRIP-UNCONFIRMED",
            destination_id="murree",
            destination_name="Murree",
            departure_city="Islamabad",
            budget=50000.0,
            travellers=2,
            days=3,
            nights=2,
            confirmed=False,  # Unconfirmed!
        )

        with pytest.raises(ValueError, match="only be generated for confirmed trip plans"):
            generator.generate_trip_pdf(unconfirmed_trip)

    def test_generate_confirmed_trip_pdf(self, pdf_fixture):
        """Verify successful PDF generation with financial metrics and itinerary."""
        generator, dm, tmp_path = pdf_fixture

        bd = CostBreakdown(
            transportation=6000.0,
            rooms_needed=1,
            accommodation=10000.0,
            food=12000.0,
            activities=6000.0,
            emergency_allowance=1700.0,
            total_cost=35700.0,
            cost_per_person=17850.0,
            remaining_budget=14300.0,
            shortage=0.0,
        )

        trip = Trip(
            trip_id="TRIP-CONFIRMED-001",
            destination_id="murree",
            destination_name="Murree",
            departure_city="Islamabad",
            budget=50000.0,
            travellers=2,
            days=3,
            nights=2,
            travel_category="Standard",
            cost_breakdown=bd,
            confirmed=True,  # Confirmed!
            itinerary=[
                {
                    "day": 1,
                    "title": "Departure & Arrival",
                    "schedule": ["08:00 AM - Depart Islamabad", "01:00 PM - Arrive Murree"],
                    "night_stay": "Overnight Standard Hotel",
                },
                {
                    "day": 2,
                    "title": "Sightseeing",
                    "schedule": ["10:00 AM - Mall Road", "02:00 PM - Patriata Cable Car"],
                    "night_stay": "Overnight Standard Hotel",
                },
                {
                    "day": 3,
                    "title": "Return Journey",
                    "schedule": ["11:00 AM - Checkout", "04:00 PM - Arrive Islamabad"],
                    "night_stay": "Trip Concluded",
                },
            ],
        )

        pdf_path = generator.generate_trip_pdf(trip)

        assert os.path.exists(pdf_path)
        assert os.path.getsize(pdf_path) > 1000  # Generated valid non-empty PDF file
        assert pdf_path.endswith(".pdf")

    def test_generate_monthly_budget_pdf(self, pdf_fixture):
        generator, dm, _ = pdf_fixture

        summary = {
            "budget_id": "BUDGET-202611-ABCD",
            "month": "November 2026",
            "budget_type": "Home & Kitchen",
            "total_available": 150000.0,
            "total_planned": 120000.0,
            "unallocated_funds": 30000.0,
            "total_actual": 110000.0,
            "remaining_balance": 40000.0,
            "savings": 40000.0,
            "savings_percentage": 26.7,
            "is_overall_overspent": False,
            "category_breakdown": [
                {
                    "category": "Grocery",
                    "planned": 40000.0,
                    "actual": 38000.0,
                    "difference": 2000.0,
                    "status": "Within Budget",
                },
                {
                    "category": "Electricity",
                    "planned": 20000.0,
                    "actual": 25000.0,
                    "difference": -5000.0,
                    "status": "Overspent",
                },
            ],
            "overspent_categories": [
                {
                    "category": "Electricity",
                    "planned": 20000.0,
                    "actual": 25000.0,
                    "overspent_by": 5000.0,
                }
            ],
        }

        pdf_path = generator.generate_budget_pdf(summary)
        assert os.path.exists(pdf_path)
        assert os.path.getsize(pdf_path) > 1000

    def test_prevent_report_overwrite(self, pdf_fixture):
        """Verify unique filename generation prevents overwriting existing reports."""
        generator, dm, _ = pdf_fixture

        path1 = generator._get_unique_filepath("test_report", "ID100")
        # Simulate file existing
        with open(path1, "w") as f:
            f.write("content 1")

        path2 = generator._get_unique_filepath("test_report", "ID100")
        assert path1 != path2
