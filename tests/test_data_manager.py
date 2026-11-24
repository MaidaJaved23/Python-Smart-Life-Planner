"""Tests for DataManager and file persistence resilience."""

import json
import os
import pytest
from utils.data_manager import DataManager


@pytest.fixture
def data_manager(tmp_path):
    return DataManager(base_dir=str(tmp_path))


class TestDataManager:
    """Tests for file persistence, directory auto-creation, and corrupted JSON handling."""

    def test_directory_creation_on_init(self, tmp_path):
        dm = DataManager(base_dir=str(tmp_path))
        assert os.path.exists(dm.data_dir)
        assert os.path.exists(dm.config_dir)
        assert os.path.exists(dm.reports_dir)

    def test_missing_file_returns_default(self, data_manager):
        fake_path = os.path.join(data_manager.data_dir, "nonexistent.json")
        res = data_manager.read_json(fake_path, default=[])
        assert res == []

    def test_empty_file_returns_default(self, data_manager):
        empty_file = os.path.join(data_manager.data_dir, "empty.json")
        with open(empty_file, "w", encoding="utf-8") as f:
            f.write("")
        res = data_manager.read_json(empty_file, default={"status": "empty"})
        assert res == {"status": "empty"}

    def test_corrupted_json_handled_safely(self, data_manager):
        """CRITICAL: Corrupted JSON must not crash the application and must safely return fallback."""
        corrupt_file = os.path.join(data_manager.data_dir, "corrupt.json")
        with open(corrupt_file, "w", encoding="utf-8") as f:
            f.write("{{{{INVALID_JSON_CONTENT;;;;")

        res = data_manager.read_json(corrupt_file, default=[])
        assert res == []

    def test_atomic_write_and_read(self, data_manager):
        target_path = os.path.join(data_manager.data_dir, "test_data.json")
        data = {"app": "Smart Life Planner", "version": "1.0", "items": [1, 2, 3]}

        success = data_manager.write_json(target_path, data)
        assert success is True
        assert os.path.exists(target_path)

        read_back = data_manager.read_json(target_path)
        assert read_back == data

    def test_developer_config_persistence(self, data_manager):
        cfg = {
            "developer_name": "Test Student",
            "github_username": "student-dev",
            "email": "student@example.com",
        }
        saved = data_manager.save_developer_config(cfg)
        assert saved is True

        loaded = data_manager.load_developer_config()
        assert loaded["developer_name"] == "Test Student"
        assert loaded["github_username"] == "student-dev"
        assert loaded["email"] == "student@example.com"
