"""Monthly budget manager service.

Implements all features for budget creation, category management, expense tracking,
overspending detection, savings calculations, and data persistence using collections.
"""

from collections import Counter, defaultdict, deque
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import uuid

from models.budget import Budget
from models.expense import Expense
from utils.calculations import calculate_savings
from utils.data_manager import DataManager


class MonthlyBudgetManager:
    """Manages monthly household and personal budgets.

    Demonstrates:
    - collections.defaultdict for grouping actual expenses by category.
    - collections.Counter for counting transactions and summing category volumes.
    - collections.deque for keeping an audit activity history.
    """

    def __init__(self, data_manager: Optional[DataManager] = None):
        self.data_manager = data_manager or DataManager()
        self.budgets: Dict[str, Budget] = {}
        # Audit history deque with fixed capacity of 30 records
        self.activity_log: deque = deque(maxlen=30)
        self.load_budgets()

    def load_budgets(self) -> None:
        """Load budgets from JSON persistence."""
        raw_list = self.data_manager.load_budgets_data()
        self.budgets = {}
        for item in raw_list:
            b = Budget.from_dict(item)
            self.budgets[b.budget_id] = b

    def save_budgets(self) -> bool:
        """Persist all budgets to JSON storage."""
        data_to_save = [b.to_dict() for b in self.budgets.values()]
        return self.data_manager.save_budgets_data(data_to_save)

    def create_budget(
        self,
        month: str,
        budget_type: str,
        total_available: float,
        planned_categories: Optional[Dict[str, float]] = None,
    ) -> Budget:
        """Create and initialize a new monthly budget."""
        budget_id = f"BUDGET-{datetime.now().strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"
        budget = Budget(
            budget_id=budget_id,
            month=month,
            budget_type=budget_type,
            total_available=total_available,
            planned_categories=planned_categories,
        )
        self.budgets[budget_id] = budget
        self.activity_log.append(
            f"Created {budget_type} budget {budget_id} for {month} (Available: PKR {total_available:,.2f})"
        )
        self.save_budgets()
        return budget

    def get_budget(self, budget_id: str) -> Optional[Budget]:
        """Retrieve budget by ID."""
        return self.budgets.get(str(budget_id).strip())

    def list_budgets(self) -> List[Budget]:
        """Return all budgets sorted by creation date."""
        return list(self.budgets.values())

    def add_category(self, budget_id: str, category_name: str, planned_amount: float = 0.0) -> None:
        """Add a custom or standard category to a budget."""
        b = self.get_budget(budget_id)
        if not b:
            raise KeyError(f"Budget '{budget_id}' not found.")
        b.add_category(category_name, planned_amount)
        self.activity_log.append(f"Added category '{category_name}' (PKR {planned_amount:,.2f}) to {budget_id}")
        self.save_budgets()

    def update_category_planned(self, budget_id: str, category_name: str, planned_amount: float) -> None:
        """Update the planned allocation for a category."""
        b = self.get_budget(budget_id)
        if not b:
            raise KeyError(f"Budget '{budget_id}' not found.")
        b.update_category(category_name, planned_amount)
        self.activity_log.append(f"Updated category '{category_name}' planned to PKR {planned_amount:,.2f} in {budget_id}")
        self.save_budgets()

    def remove_category(self, budget_id: str, category_name: str) -> None:
        """Remove a category from a budget."""
        b = self.get_budget(budget_id)
        if not b:
            raise KeyError(f"Budget '{budget_id}' not found.")
        b.remove_category(category_name)
        self.activity_log.append(f"Removed category '{category_name}' from {budget_id}")
        self.save_budgets()

    def record_expense(
        self,
        budget_id: str,
        category: str,
        description: str,
        amount: float,
        date: str = "",
        expense_id: Optional[str] = None,
    ) -> Expense:
        """Record a new actual spending entry."""
        b = self.get_budget(budget_id)
        if not b:
            raise KeyError(f"Budget '{budget_id}' not found.")

        exp_id = expense_id or f"EXP-{len(b.expenses) + 1:03d}-{uuid.uuid4().hex[:4].upper()}"
        expense = Expense(
            expense_id=exp_id,
            category=category,
            description=description,
            amount=amount,
            date=date,
        )
        b.add_expense(expense)
        self.activity_log.append(
            f"Recorded expense {expense.expense_id} ({expense.category}: PKR {expense.amount:,.2f}) in {budget_id}"
        )
        self.save_budgets()
        return expense

    def update_expense(
        self,
        budget_id: str,
        expense_id: str,
        category: Optional[str] = None,
        description: Optional[str] = None,
        amount: Optional[float] = None,
        date: Optional[str] = None,
    ) -> Expense:
        """Update an existing expense in a budget."""
        b = self.get_budget(budget_id)
        if not b:
            raise KeyError(f"Budget '{budget_id}' not found.")
        exp = b.get_expense(expense_id)
        if not exp:
            raise KeyError(f"Expense '{expense_id}' not found in budget {budget_id}.")

        exp.update(category=category, description=description, amount=amount, date=date)
        # Ensure category is in planned categories if updated
        if category and not b._find_category_key(category):
            b.planned_categories[category] = 0.0

        self.activity_log.append(f"Updated expense {expense_id} in {budget_id}")
        self.save_budgets()
        return exp

    def delete_expense(self, budget_id: str, expense_id: str) -> bool:
        """Delete an expense record."""
        b = self.get_budget(budget_id)
        if not b:
            raise KeyError(f"Budget '{budget_id}' not found.")
        deleted = b.delete_expense(expense_id)
        if deleted:
            self.activity_log.append(f"Deleted expense {expense_id} from {budget_id}")
            self.save_budgets()
        return deleted

    def calculate_financial_summary(self, budget_id: str) -> Dict[str, Any]:
        """Perform comprehensive financial analysis on the budget.

        Uses:
        - collections.defaultdict to group expenses
        - collections.Counter to tally transaction counts and identify highest frequency categories
        """
        b = self.get_budget(budget_id)
        if not b:
            raise KeyError(f"Budget '{budget_id}' not found.")

        # 1. Planned totals
        total_planned = round(sum(b.planned_categories.values()), 2)
        unallocated_funds = round(b.total_available - total_planned, 2)

        # 2. Actual expenses grouped by category using defaultdict
        actual_by_cat = defaultdict(float)
        # 3. Transaction count using Counter
        cat_transaction_counts = Counter()

        for exp in b.expenses:
            actual_by_cat[exp.category] += exp.amount
            cat_transaction_counts[exp.category] += 1

        total_actual = round(sum(actual_by_cat.values()), 2)

        # 4. Remaining balance & savings
        remaining_balance, savings_pct = calculate_savings(b.total_available, total_actual)

        # 5. Overspending detection
        category_breakdown = []
        overspent_categories = []
        total_overspent_amount = 0.0

        all_categories = sorted(
            set(list(b.planned_categories.keys()) + list(actual_by_cat.keys()))
        )

        for cat in all_categories:
            planned = b.planned_categories.get(cat, 0.0)
            actual = round(actual_by_cat.get(cat, 0.0), 2)
            variance = round(planned - actual, 2)  # positive = surplus, negative = overspent
            is_overspent = actual > planned
            diff_abs = round(abs(variance), 2)
            tx_count = cat_transaction_counts.get(cat, 0)

            if is_overspent:
                overspent_categories.append(
                    {
                        "category": cat,
                        "planned": planned,
                        "actual": actual,
                        "overspent_by": diff_abs,
                        "transaction_count": tx_count,
                    }
                )
                total_overspent_amount += diff_abs

            category_breakdown.append(
                {
                    "category": cat,
                    "planned": planned,
                    "actual": actual,
                    "difference": variance,
                    "status": "Overspent" if is_overspent else "Within Budget",
                    "transaction_count": tx_count,
                }
            )

        overall_overspent = total_actual > b.total_available
        planned_exceeds_available = total_planned > b.total_available

        return {
            "budget_id": b.budget_id,
            "month": b.month,
            "budget_type": b.budget_type,
            "total_available": b.total_available,
            "total_planned": total_planned,
            "unallocated_funds": unallocated_funds,
            "planned_exceeds_available": planned_exceeds_available,
            "total_actual": total_actual,
            "remaining_balance": remaining_balance,
            "savings": max(0.0, remaining_balance),
            "savings_percentage": savings_pct if remaining_balance >= 0 else 0.0,
            "is_overall_overspent": overall_overspent,
            "overall_shortage": round(total_actual - b.total_available, 2) if overall_overspent else 0.0,
            "category_breakdown": category_breakdown,
            "overspent_categories": overspent_categories,
            "total_overspent_amount": round(total_overspent_amount, 2),
            "total_transactions": len(b.expenses),
            "most_active_category": cat_transaction_counts.most_common(1)[0] if cat_transaction_counts else ("None", 0),
        }
