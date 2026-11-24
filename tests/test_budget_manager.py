"""Tests for MonthlyBudgetManager and financial accounting features."""

import pytest
from models.budget import Budget
from models.expense import Expense
from services.budget_manager import MonthlyBudgetManager
from utils.data_manager import DataManager


@pytest.fixture
def budget_manager(tmp_path):
    dm = DataManager(base_dir=str(tmp_path))
    return MonthlyBudgetManager(data_manager=dm)


class TestMonthlyBudgetManager:
    """Test suite for budget management, expense tracking, and savings."""

    def test_create_valid_budget(self, budget_manager):
        budget = budget_manager.create_budget(
            month="November 2026",
            budget_type="Home & Kitchen",
            total_available=100000.0,
        )
        assert budget is not None
        assert budget.month == "November 2026"
        assert budget.total_available == 100000.0
        assert len(budget.planned_categories) > 0  # Default categories initialized
        assert "Grocery" in budget.planned_categories

    def test_reject_zero_or_negative_budget(self):
        with pytest.raises(ValueError, match="greater than zero"):
            Budget(
                budget_id="B-TEST",
                month="November 2026",
                budget_type="Home & Kitchen",
                total_available=0.0,
            )

        with pytest.raises(ValueError, match="greater than zero"):
            Budget(
                budget_id="B-TEST",
                month="November 2026",
                budget_type="Home & Kitchen",
                total_available=-5000.0,
            )

    def test_add_and_update_categories(self, budget_manager):
        budget = budget_manager.create_budget("December 2026", "Personal Finance", 80000.0)

        # Add custom category
        budget_manager.add_category(budget.budget_id, "Crypto Investments", 15000.0)
        assert "Crypto Investments" in budget.planned_categories
        assert budget.planned_categories["Crypto Investments"] == 15000.0

        # Reject duplicate category
        with pytest.raises(ValueError, match="already exists"):
            budget_manager.add_category(budget.budget_id, "crypto investments", 5000.0)

        # Update planned allocation
        budget_manager.update_category_planned(budget.budget_id, "Crypto Investments", 20000.0)
        assert budget.planned_categories["Crypto Investments"] == 20000.0

    def test_record_update_delete_expenses(self, budget_manager):
        b = budget_manager.create_budget("January 2027", "Home & Kitchen", 120000.0)
        b.update_category("Grocery", 30000.0)

        # Record expense
        exp = budget_manager.record_expense(
            budget_id=b.budget_id,
            category="Grocery",
            description="Weekly vegetables & meat",
            amount=8500.0,
            date="2027-01-05",
        )
        assert exp.amount == 8500.0
        assert len(b.expenses) == 1

        # Reject negative expense amount
        with pytest.raises(ValueError, match="greater than zero"):
            budget_manager.record_expense(b.budget_id, "Grocery", "Invalid", -100.0)

        # Update expense
        budget_manager.update_expense(
            budget_id=b.budget_id,
            expense_id=exp.expense_id,
            amount=9000.0,
            description="Updated description",
        )
        assert exp.amount == 9000.0
        assert exp.description == "Updated description"

        # Delete expense
        deleted = budget_manager.delete_expense(b.budget_id, exp.expense_id)
        assert deleted is True
        assert len(b.expenses) == 0

    def test_financial_summary_and_overspending(self, budget_manager):
        b = budget_manager.create_budget("February 2027", "Home & Kitchen", 50000.0)
        budget_manager.update_category_planned(b.budget_id, "Electricity", 10000.0)
        budget_manager.update_category_planned(b.budget_id, "Internet", 4000.0)

        # Record electricity expense exceeding planned (Overspending)
        budget_manager.record_expense(b.budget_id, "Electricity", "Summer AC bill", 14000.0)
        # Record internet within planned
        budget_manager.record_expense(b.budget_id, "Internet", "Fiber optic", 3500.0)

        summary = budget_manager.calculate_financial_summary(b.budget_id)

        assert summary["total_actual"] == 17500.0
        assert summary["remaining_balance"] == 32500.0
        assert summary["savings"] == 32500.0
        assert summary["savings_percentage"] == 65.0  # (32500 / 50000) * 100
        assert summary["is_overall_overspent"] is False

        # Category overspending check
        assert len(summary["overspent_categories"]) == 1
        over = summary["overspent_categories"][0]
        assert over["category"] == "Electricity"
        assert over["overspent_by"] == 4000.0  # 14000 - 10000

    def test_overall_budget_overspending(self, budget_manager):
        b = budget_manager.create_budget("March 2027", "Personal Finance", 20000.0)
        budget_manager.record_expense(b.budget_id, "Shopping", "New clothes", 25000.0)

        summary = budget_manager.calculate_financial_summary(b.budget_id)
        assert summary["is_overall_overspent"] is True
        assert summary["overall_shortage"] == 5000.0
        assert summary["remaining_balance"] == -5000.0
        assert summary["savings"] == 0.0
        assert summary["savings_percentage"] == 0.0

    def test_handling_nonexistent_expense(self, budget_manager):
        b = budget_manager.create_budget("April 2027", "Home & Kitchen", 50000.0)
        with pytest.raises(KeyError, match="not found"):
            budget_manager.update_expense(b.budget_id, "NON-EXISTENT-ID", amount=500.0)

        deleted = budget_manager.delete_expense(b.budget_id, "NON-EXISTENT-ID")
        assert deleted is False
