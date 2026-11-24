"""Expense model for tracking actual spending."""

from datetime import datetime
from typing import Dict, Any


class Expense:
    """Represents an individual expense record in the Monthly Budget Manager.

    Attributes:
        expense_id: Unique identifier for the expense (e.g. 'EXP-001').
        category: Associated budget category.
        description: Description of the purchase or bill.
        amount: Numerical amount spent in PKR.
        date: Date of expense (YYYY-MM-DD).
    """

    def __init__(
        self,
        expense_id: str,
        category: str,
        description: str,
        amount: float,
        date: str = "",
    ):
        if not expense_id or not str(expense_id).strip():
            raise ValueError("Expense ID cannot be empty.")
        if not category or not str(category).strip():
            raise ValueError("Expense category cannot be empty.")
        if amount <= 0:
            raise ValueError("Expense amount must be greater than zero.")

        self.expense_id = str(expense_id).strip()
        self.category = str(category).strip()
        self.description = str(description).strip() or "General Expense"
        self.amount = float(amount)
        self.date = date.strip() or datetime.now().strftime("%Y-%m-%d")

    def update(
        self,
        category: str = None,
        description: str = None,
        amount: float = None,
        date: str = None,
    ) -> None:
        """Update expense attributes with validation."""
        if category is not None:
            if not category.strip():
                raise ValueError("Category cannot be empty.")
            self.category = category.strip()

        if description is not None:
            self.description = description.strip() or "General Expense"

        if amount is not None:
            if amount <= 0:
                raise ValueError("Amount must be greater than zero.")
            self.amount = float(amount)

        if date is not None:
            if not date.strip():
                raise ValueError("Date cannot be empty.")
            self.date = date.strip()

    def to_dict(self) -> Dict[str, Any]:
        """Convert expense to dictionary."""
        return {
            "expense_id": self.expense_id,
            "category": self.category,
            "description": self.description,
            "amount": self.amount,
            "date": self.date,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Expense":
        """Instantiate an Expense from a dictionary."""
        return cls(
            expense_id=data.get("expense_id", ""),
            category=data.get("category", ""),
            description=data.get("description", ""),
            amount=float(data.get("amount", 0.0)),
            date=data.get("date", ""),
        )

    def __repr__(self) -> str:
        return f"<Expense {self.expense_id}: {self.category} PKR {self.amount:,.2f}>"
