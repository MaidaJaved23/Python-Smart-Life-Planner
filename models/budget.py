"""Budget model representing monthly budget planning and tracking."""

from collections import defaultdict
from datetime import datetime
from typing import Dict, Any, List, Optional
from models.expense import Expense


class Budget:
    """Represents a monthly budget record.

    Encapsulates budget configuration, planned category amounts, and actual expenses.
    Utilizes defaultdict for grouping and calculating actual expenses by category.
    """

    DEFAULT_HOME_KITCHEN_CATEGORIES = [
        "Grocery",
        "Electricity",
        "Gas",
        "Water",
        "Internet",
        "Rent",
        "Kitchen Supplies",
        "Medical Expenses",
        "Transportation",
        "Emergency Savings",
        "Other Expenses",
    ]

    DEFAULT_PERSONAL_FINANCE_CATEGORIES = [
        "Cosmetics and Personal Care",
        "Fitness and Gym",
        "Health and Medical",
        "Shopping",
        "Clothing",
        "Food and Restaurants",
        "Transportation",
        "Education",
        "Entertainment",
        "Investments and Savings",
        "Other Expenses",
    ]

    def __init__(
        self,
        budget_id: str,
        month: str,
        budget_type: str,
        total_available: float,
        planned_categories: Optional[Dict[str, float]] = None,
        expenses: Optional[List[Expense]] = None,
        created_at: Optional[str] = None,
    ):
        if not budget_id or not str(budget_id).strip():
            raise ValueError("Budget ID cannot be empty.")
        if not month or not str(month).strip():
            raise ValueError("Budget month cannot be empty.")
        if total_available <= 0:
            raise ValueError("Total available budget must be greater than zero.")

        self.budget_id = str(budget_id).strip()
        self.month = str(month).strip()
        self.budget_type = str(budget_type).strip()
        self.total_available = float(total_available)
        self.planned_categories: Dict[str, float] = planned_categories or {}
        self.expenses: List[Expense] = expenses or []
        self.created_at = created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # If planned_categories is empty, populate with default categories for the type
        if not self.planned_categories:
            self._initialize_default_categories()

    def _initialize_default_categories(self) -> None:
        """Initialize zero-allocation default categories based on budget type."""
        categories = (
            self.DEFAULT_HOME_KITCHEN_CATEGORIES
            if "home" in self.budget_type.lower()
            else self.DEFAULT_PERSONAL_FINANCE_CATEGORIES
        )
        for cat in categories:
            self.planned_categories[cat] = 0.0

    def add_category(self, category_name: str, planned_amount: float = 0.0) -> None:
        """Add a new category with a planned amount."""
        cat_clean = category_name.strip()
        if not cat_clean:
            raise ValueError("Category name cannot be empty.")
        if planned_amount < 0:
            raise ValueError("Planned amount cannot be negative.")
        # Case-insensitive check
        for existing in self.planned_categories:
            if existing.lower() == cat_clean.lower():
                raise ValueError(f"Category '{cat_clean}' already exists.")
        self.planned_categories[cat_clean] = float(planned_amount)

    def update_category(self, category_name: str, planned_amount: float) -> None:
        """Update planned amount for an existing category."""
        cat_clean = category_name.strip()
        if planned_amount < 0:
            raise ValueError("Planned amount cannot be negative.")
        target_key = self._find_category_key(cat_clean)
        if not target_key:
            raise KeyError(f"Category '{cat_clean}' not found.")
        self.planned_categories[target_key] = float(planned_amount)

    def remove_category(self, category_name: str) -> None:
        """Remove a category. Expenses under this category will have their category mapped to 'Other Expenses'."""
        cat_clean = category_name.strip()
        target_key = self._find_category_key(cat_clean)
        if not target_key:
            raise KeyError(f"Category '{cat_clean}' not found.")

        # Reassign any expenses belonging to this category to 'Other Expenses'
        fallback_cat = "Other Expenses"
        if fallback_cat not in self.planned_categories and target_key != fallback_cat:
            self.planned_categories[fallback_cat] = 0.0

        for exp in self.expenses:
            if exp.category.lower() == target_key.lower():
                exp.category = fallback_cat

        del self.planned_categories[target_key]

    def _find_category_key(self, category_name: str) -> Optional[str]:
        """Case-insensitive category lookup."""
        for existing in self.planned_categories:
            if existing.lower() == category_name.lower():
                return existing
        return None

    def add_expense(self, expense: Expense) -> None:
        """Add an actual expense."""
        # Ensure category exists in planned_categories (auto-add with 0 planned if new custom)
        cat_key = self._find_category_key(expense.category)
        if not cat_key:
            self.planned_categories[expense.category] = 0.0
        else:
            expense.category = cat_key

        # Check duplicate expense_id
        if any(e.expense_id == expense.expense_id for e in self.expenses):
            raise ValueError(f"Expense with ID '{expense.expense_id}' already exists.")
        self.expenses.append(expense)

    def get_expense(self, expense_id: str) -> Optional[Expense]:
        """Find an expense by ID."""
        for e in self.expenses:
            if e.expense_id == expense_id:
                return e
        return None

    def delete_expense(self, expense_id: str) -> bool:
        """Delete an expense by ID."""
        for i, e in enumerate(self.expenses):
            if e.expense_id == expense_id:
                del self.expenses[i]
                return True
        return False

    def get_actual_expenses_by_category(self) -> Dict[str, float]:
        """Group actual expenses by category using collections.defaultdict."""
        grouped = defaultdict(float)
        # Ensure all planned categories are represented with at least 0.0
        for cat in self.planned_categories:
            grouped[cat] = 0.0
        for exp in self.expenses:
            grouped[exp.category] += exp.amount
        return dict(grouped)

    def to_dict(self) -> Dict[str, Any]:
        """Convert budget to dictionary."""
        return {
            "budget_id": self.budget_id,
            "month": self.month,
            "budget_type": self.budget_type,
            "total_available": self.total_available,
            "planned_categories": self.planned_categories,
            "expenses": [e.to_dict() for e in self.expenses],
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Budget":
        """Instantiate Budget from dictionary."""
        expenses_data = data.get("expenses", [])
        expenses = [Expense.from_dict(e) for e in expenses_data]
        return cls(
            budget_id=data.get("budget_id", ""),
            month=data.get("month", ""),
            budget_type=data.get("budget_type", "Home & Kitchen"),
            total_available=float(data.get("total_available", 0.0)),
            planned_categories=data.get("planned_categories", {}),
            expenses=expenses,
            created_at=data.get("created_at"),
        )

    def __repr__(self) -> str:
        return f"<Budget {self.budget_id} ({self.month}) Available: PKR {self.total_available:,.2f}>"
