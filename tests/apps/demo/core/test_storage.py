"""Tests for demo core storage."""

from __future__ import annotations

import datetime
import json

from pyclif.apps.demo.apps.tasks.models import Task
from pyclif.apps.demo.apps.users.models import User
from pyclif.apps.demo.core.storage import Storage

_DT = datetime.datetime(2024, 1, 1, 12, 0)


def _storage(tmp_path) -> Storage:
    s = Storage()
    s._path = tmp_path / "demo.json"
    return s


def _task(**kwargs) -> Task:
    return Task(**{"id": "t1", "title": "Test task", "created_at": _DT, **kwargs})


def _user(**kwargs) -> User:
    return User(**{"username": "alice", "email": "alice@example.com", "created_at": _DT, **kwargs})


class TestLoad:
    def test_returns_empty_structure_when_file_absent(self, tmp_path):
        data = _storage(tmp_path).load()
        assert data == {"tasks": [], "users": []}

    def test_returns_stored_data_when_file_exists(self, tmp_path):
        s = _storage(tmp_path)
        s.save({"tasks": [{"id": "x"}], "users": []})
        assert s.load()["tasks"][0]["id"] == "x"


class TestSave:
    def test_creates_file_and_parent_directories(self, tmp_path):
        s = _storage(tmp_path / "nested" / "path")
        s.save({"tasks": [], "users": []})
        assert s._path.exists()

    def test_output_is_valid_json(self, tmp_path):
        s = _storage(tmp_path)
        s.save({"tasks": [{"id": "1", "title": "T"}], "users": []})
        raw = json.loads(s._path.read_text())
        assert raw["tasks"][0]["id"] == "1"


class TestTaskOperations:
    def test_round_trip(self, tmp_path):
        s = _storage(tmp_path)
        s.upsert_task(_task())
        result = s.get_task("t1")
        assert result is not None
        assert result.id == "t1"
        assert result.title == "Test task"

    def test_get_task_not_found_returns_none(self, tmp_path):
        assert _storage(tmp_path).get_task("missing") is None

    def test_get_tasks_returns_all(self, tmp_path):
        s = _storage(tmp_path)
        s.upsert_task(_task(id="t1"))
        s.upsert_task(_task(id="t2", title="Second"))
        assert len(s.get_tasks()) == 2

    def test_upsert_replaces_existing_by_id(self, tmp_path):
        s = _storage(tmp_path)
        s.upsert_task(_task(title="Original"))
        s.upsert_task(_task(title="Updated"))
        tasks = s.get_tasks()
        assert len(tasks) == 1
        assert tasks[0].title == "Updated"

    def test_delete_found_returns_true_and_removes(self, tmp_path):
        s = _storage(tmp_path)
        s.upsert_task(_task())
        assert s.delete_task("t1") is True
        assert s.get_task("t1") is None

    def test_delete_not_found_returns_false(self, tmp_path):
        assert _storage(tmp_path).delete_task("missing") is False


class TestUserOperations:
    def test_round_trip(self, tmp_path):
        s = _storage(tmp_path)
        s.upsert_user(_user())
        result = s.get_user("alice")
        assert result is not None
        assert result.username == "alice"

    def test_get_user_not_found_returns_none(self, tmp_path):
        assert _storage(tmp_path).get_user("nobody") is None

    def test_get_users_returns_all(self, tmp_path):
        s = _storage(tmp_path)
        s.upsert_user(_user(username="alice"))
        s.upsert_user(_user(username="bob", email="bob@example.com"))
        assert len(s.get_users()) == 2

    def test_upsert_replaces_existing_by_username(self, tmp_path):
        s = _storage(tmp_path)
        s.upsert_user(_user(role="member"))
        s.upsert_user(_user(role="admin"))
        users = s.get_users()
        assert len(users) == 1
        assert users[0].role == "admin"
