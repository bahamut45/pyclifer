"""Tests for TaskInterface — Storage is mocked to avoid filesystem I/O."""

from __future__ import annotations

import datetime
import importlib
from unittest.mock import MagicMock, patch

import pytest

from pyclif import ExitCode
from pyclif.apps.demo.apps.tasks.interfaces import _FAKE_SYNC_TITLES, TaskInterface
from pyclif.apps.demo.apps.tasks.models import Task
from pyclif.apps.demo.core.context import DemoContext

_DT = datetime.datetime(2024, 1, 1)
_interfaces_mod = importlib.import_module("pyclif.apps.demo.apps.tasks.interfaces")


def _task(**kwargs) -> Task:
    return Task(**{"id": "t1", "title": "Test task", "created_at": _DT, **kwargs})


@pytest.fixture
def ctx():
    c = DemoContext()
    c._storage = MagicMock()
    return c


@pytest.fixture
def iface(ctx):
    return TaskInterface(ctx)


@pytest.fixture
def storage(ctx):
    return ctx._storage


class TestListTasks:
    def test_returns_all_tasks(self, iface, storage):
        storage.get_tasks.return_value = [_task(id="t1"), _task(id="t2", title="T2")]
        results = iface.list_tasks()
        assert len(results) == 2
        assert all(r.success for r in results)

    def test_returns_task_ids_as_items(self, iface, storage):
        storage.get_tasks.return_value = [_task(id="abc")]
        results = iface.list_tasks()
        assert results[0].item == "abc"

    def test_filters_by_status(self, iface, storage):
        storage.get_tasks.return_value = [
            _task(id="t1", status="open"),
            _task(id="t2", title="T2", status="done"),
        ]
        results = iface.list_tasks(status="open")
        assert len(results) == 1
        assert results[0].item == "t1"

    def test_filters_by_priority(self, iface, storage):
        storage.get_tasks.return_value = [
            _task(id="t1", priority="low"),
            _task(id="t2", title="T2", priority="high"),
        ]
        results = iface.list_tasks(priority="high")
        assert len(results) == 1
        assert results[0].item == "t2"

    def test_returns_empty_list_when_no_tasks(self, iface, storage):
        storage.get_tasks.return_value = []
        assert iface.list_tasks() == []


class TestAddTask:
    def test_creates_and_persists_task(self, iface, storage):
        results = iface.add_task(title="New task")
        assert len(results) == 1
        assert results[0].success
        storage.upsert_task.assert_called_once()

    def test_result_data_is_task_instance(self, iface, storage):
        results = iface.add_task(title="My task")
        assert isinstance(results[0].data, Task)

    def test_task_title_is_preserved(self, iface, storage):
        results = iface.add_task(title="My task")
        assert results[0].data.title == "My task"

    def test_tags_stored_correctly(self, iface, storage):
        results = iface.add_task(title="Tagged", tags=["bug", "urgent"])
        assert results[0].data.tags == ["bug", "urgent"]

    def test_empty_tags_default_to_empty_list(self, iface, storage):
        results = iface.add_task(title="T", tags=None)
        assert results[0].data.tags == []


class TestShowTask:
    def test_found_returns_ok_with_task(self, iface, storage):
        task = _task()
        storage.get_task.return_value = task
        results = iface.show_task("t1")
        assert results[0].success
        assert results[0].data is task

    def test_not_found_returns_error_404(self, iface, storage):
        storage.get_task.return_value = None
        results = iface.show_task("missing")
        assert not results[0].success
        assert results[0].error_code == ExitCode.NOT_FOUND


class TestCompleteTask:
    def test_marks_open_task_done(self, iface, storage):
        storage.get_task.return_value = _task(status="open")
        results = iface.complete_task("t1")
        assert results[0].success
        storage.upsert_task.assert_called_once()

    def test_already_done_returns_error(self, iface, storage):
        storage.get_task.return_value = _task(status="done")
        results = iface.complete_task("t1")
        assert not results[0].success

    def test_not_found_returns_error_404(self, iface, storage):
        storage.get_task.return_value = None
        results = iface.complete_task("missing")
        assert not results[0].success
        assert results[0].error_code == ExitCode.NOT_FOUND


class TestDeleteTask:
    def test_found_deletes_and_returns_ok(self, iface, storage):
        storage.delete_task.return_value = True
        results = iface.delete_task("t1")
        assert results[0].success
        storage.delete_task.assert_called_once_with("t1")

    def test_not_found_returns_error_404(self, iface, storage):
        storage.delete_task.return_value = False
        results = iface.delete_task("missing")
        assert not results[0].success
        assert results[0].error_code == ExitCode.NOT_FOUND


class TestSyncTasks:
    def test_yields_one_result_per_fake_title(self, iface, storage):
        with patch.object(_interfaces_mod.time, "sleep"):
            results = list(iface.sync_tasks("https://example.com"))
        assert len(results) == len(_FAKE_SYNC_TITLES)

    def test_all_results_are_successful(self, iface, storage):
        with patch.object(_interfaces_mod.time, "sleep"):
            results = list(iface.sync_tasks())
        assert all(r.success for r in results)

    def test_each_result_carries_a_task(self, iface, storage):
        with patch.object(_interfaces_mod.time, "sleep"):
            results = list(iface.sync_tasks())
        assert all(isinstance(r.data, Task) for r in results)

    def test_tasks_are_persisted(self, iface, storage):
        with patch.object(_interfaces_mod.time, "sleep"):
            list(iface.sync_tasks())
        assert storage.upsert_task.call_count == len(_FAKE_SYNC_TITLES)
