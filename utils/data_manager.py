"""Data persistence manager for JSON files and directory management."""

import json
import os
import shutil
from typing import Any, Dict, List, Optional


class DataManager:
    """Handles reading, writing, and safe error handling for JSON persistence."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )
        self.data_dir = os.path.join(self.base_dir, "data")
        self.config_dir = os.path.join(self.base_dir, "config")
        self.reports_dir = os.path.join(self.base_dir, "reports")

        # Ensure essential directories exist
        self.ensure_directory(self.data_dir)
        self.ensure_directory(self.config_dir)
        self.ensure_directory(self.reports_dir)

    @staticmethod
    def ensure_directory(path: str) -> None:
        """Create directory if it does not already exist."""
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)

    def read_json(self, filepath: str, default: Any = None) -> Any:
        """Safely read JSON file with corruption and missing file handling."""
        if not os.path.exists(filepath):
            return default if default is not None else {}

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return default if default is not None else {}
                return json.loads(content)
        except (json.JSONDecodeError, OSError) as e:
            # Handle corrupted or unreadable JSON file safely
            backup_path = f"{filepath}.corrupted.{os.getpid()}"
            try:
                shutil.copyfile(filepath, backup_path)
            except OSError:
                pass
            return default if default is not None else {}

    def write_json(self, filepath: str, data: Any) -> bool:
        """Safely write JSON file with atomic write mechanism."""
        dir_name = os.path.dirname(filepath)
        self.ensure_directory(dir_name)

        temp_path = f"{filepath}.tmp.{os.getpid()}"
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            shutil.move(temp_path, filepath)
            return True
        except OSError:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            return False

    def get_destinations_path(self) -> str:
        return os.path.join(self.data_dir, "destinations.json")

    def get_trips_path(self) -> str:
        return os.path.join(self.data_dir, "trips.json")

    def get_budgets_path(self) -> str:
        return os.path.join(self.data_dir, "budgets.json")

    def get_developer_config_path(self) -> str:
        return os.path.join(self.config_dir, "developer.json")

    def load_developer_config(self) -> Dict[str, str]:
        """Load developer configuration with fallback defaults."""
        cfg = self.read_json(self.get_developer_config_path(), default={})
        return {
            "developer_name": cfg.get("developer_name", "Smart Life Planner Developer"),
            "github_username": cfg.get("github_username", "smart-life-planner"),
            "email": cfg.get("email", "developer@smartlifeplanner.pk"),
        }

    def save_developer_config(self, config: Dict[str, str]) -> bool:
        """Save developer configuration."""
        return self.write_json(self.get_developer_config_path(), config)

    def load_destinations_data(self) -> List[Dict[str, Any]]:
        """Load destinations from JSON file."""
        data = self.read_json(self.get_destinations_path(), default={})
        if isinstance(data, dict):
            return data.get("destinations", [])
        elif isinstance(data, list):
            return data
        return []

    def load_trips_data(self) -> List[Dict[str, Any]]:
        """Load trips list from JSON file."""
        data = self.read_json(self.get_trips_path(), default=[])
        return data if isinstance(data, list) else []

    def save_trips_data(self, trips_list: List[Dict[str, Any]]) -> bool:
        """Save trips list to JSON file."""
        return self.write_json(self.get_trips_path(), trips_list)

    def load_budgets_data(self) -> List[Dict[str, Any]]:
        """Load budgets list from JSON file."""
        data = self.read_json(self.get_budgets_path(), default=[])
        return data if isinstance(data, list) else []

    def save_budgets_data(self, budgets_list: List[Dict[str, Any]]) -> bool:
        """Save budgets list to JSON file."""
        return self.write_json(self.get_budgets_path(), budgets_list)
