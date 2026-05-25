"""CLI integration tests for task commands — invoked via CliRunner through the full pyclif app."""

from __future__ import annotations

import datetime
import importlib
import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from pyclif import ExitCode
from pyclif.apps.demo.apps.tasks.interfaces import _FAKE_SYNC_TITLES
from pyclif.apps.demo.apps.tasks.models import Task
from pyclif.cli import app

_demo_context_mod = importlib.import_module("pyclif.apps.demo.core.context")
_interfaces_mod = importlib.import_module("pyclif.apps.demo.apps.tasks.interfaces")

_DT = datetime.datetime(2024, 1, 1)


def _task(**kwargs) -> Task:
    return Task(**{"id": "t1", "title": "Test task", "created_at": _DT, **kwargs})


@pytest.fixture
def storage() -> MagicMock:
    return MagicMock()


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _run(runner, storage, *args, **kwargs):
    """Invoke an app command with Storage mocked."""
    with patch.object(_demo_context_mod, "Storage", return_value=storage):
        return runner.invoke(app, list(args), **kwargs)


class TestListCommand:
    def test_success_with_tasks(self, runner, storage):
        storage.get_tasks.return_value = [_task()]
        result = _run(runner, storage, "demo", "tasks", "list")
        assert result.exit_code == 0

    def test_empty_storage_shows_no_dataset(self, runner, storage):
        storage.get_tasks.return_value = []
        result = _run(runner, storage, "demo", "tasks", "list")
        assert result.exit_code == 0
        assert "No dataset available" in result.output

    def test_status_filter_accepted(self, runner, storage):
        storage.get_tasks.return_value = [_task(status="open")]
        result = _run(runner, storage, "demo", "tasks", "list", "--status", "open")
        assert result.exit_code == 0

    def test_priority_filter_accepted(self, runner, storage):
        storage.get_tasks.return_value = [_task(priority="high")]
        result = _run(runner, storage, "demo", "tasks", "list", "--priority", "high")
        assert result.exit_code == 0

    def test_json_output_includes_results(self, runner, storage):
        storage.get_tasks.return_value = [_task(title="My task")]
        result = _run(runner, storage, "--output-format", "json", "demo", "tasks", "list")
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["data"]["results"][0]["title"] == "My task"


class TestAddCommand:
    def test_creates_task_and_calls_upsert(self, runner, storage):
        result = _run(runner, storage, "demo", "tasks", "add", "--title", "My task")
        assert result.exit_code == 0
        storage.upsert_task.assert_called_once()

    def test_title_is_required(self, runner, storage):
        result = _run(runner, storage, "demo", "tasks", "add")
        assert result.exit_code != 0

    def test_all_options_accepted(self, runner, storage):
        result = _run(
            runner,
            storage,
            "demo",
            "tasks",
            "add",
            "--title",
            "T",
            "--priority",
            "high",
            "--due",
            "2024-06-01",
            "--tags",
            "bug,urgent",
            "--assignee",
            "alice",
        )
        assert result.exit_code == 0

    def test_json_output_shows_added_task(self, runner, storage):
        result = _run(
            runner,
            storage,
            "--output-format",
            "json",
            "demo",
            "tasks",
            "add",
            "--title",
            "New task",
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"]


class TestShowCommand:
    def test_found_exits_zero(self, runner, storage):
        storage.get_task.return_value = _task()
        result = _run(runner, storage, "demo", "tasks", "show", "t1")
        assert result.exit_code == 0

    def test_not_found_returns_failure_response(self, runner, storage):
        storage.get_task.return_value = None
        result = _run(
            runner, storage, "--output-format", "json", "demo", "tasks", "show", "missing"
        )
        assert result.exit_code == ExitCode.NOT_FOUND
        data = json.loads(result.output)
        assert not data["success"]


class TestCompleteCommand:
    def test_success(self, runner, storage):
        storage.get_task.return_value = _task(status="open")
        result = _run(runner, storage, "demo", "tasks", "complete", "t1")
        assert result.exit_code == 0

    def test_not_found_returns_failure_response(self, runner, storage):
        storage.get_task.return_value = None
        result = _run(
            runner, storage, "--output-format", "json", "demo", "tasks", "complete", "missing"
        )
        assert result.exit_code == ExitCode.NOT_FOUND
        data = json.loads(result.output)
        assert not data["success"]


class TestDeleteCommand:
    def test_delete_with_yes_flag_calls_storage(self, runner, storage):
        storage.delete_task.return_value = True
        result = _run(runner, storage, "demo", "tasks", "delete", "t1", "--yes")
        assert result.exit_code == 0
        storage.delete_task.assert_called_once_with("t1")

    def test_delete_with_y_input_calls_storage(self, runner, storage):
        storage.delete_task.return_value = True
        _run(runner, storage, "demo", "tasks", "delete", "t1", input="y\n")
        storage.delete_task.assert_called_once()

    def test_delete_aborted_on_n_skips_storage(self, runner, storage):
        _run(runner, storage, "demo", "tasks", "delete", "t1", input="n\n")
        storage.delete_task.assert_not_called()

    def test_delete_with_yes_shorthand(self, runner, storage):
        storage.delete_task.return_value = True
        result = _run(runner, storage, "demo", "tasks", "delete", "t1", "-y")
        assert result.exit_code == 0


class TestSyncCommand:
    def test_sync_persists_all_fake_tasks(self, runner, storage):
        with patch.object(_interfaces_mod.time, "sleep"):
            result = _run(runner, storage, "demo", "tasks", "sync")
        assert result.exit_code == 0
        assert storage.upsert_task.call_count == len(_FAKE_SYNC_TITLES)

    def test_sync_with_custom_source(self, runner, storage):
        with patch.object(_interfaces_mod.time, "sleep"):
            result = _run(
                runner,
                storage,
                "demo",
                "tasks",
                "sync",
                "--source",
                "https://example.com/api/tasks",
            )
        assert result.exit_code == 0
