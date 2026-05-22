"""Tests for task output renderers."""

from __future__ import annotations

import datetime
import io
from unittest.mock import MagicMock

from rich.console import Console

from pyclif import OperationResult, Response
from pyclif.apps.demo.apps.tasks.models import Task
from pyclif.apps.demo.apps.tasks.renderers import (
    TaskAddRenderer,
    TaskCompleteRenderer,
    TaskDeleteRenderer,
    TaskDetailRenderer,
    TaskListRenderer,
    TaskSyncRenderer,
)

_DT = datetime.datetime(2024, 1, 1, 12, 0)


def _task(**kwargs) -> Task:
    return Task(**{"id": "t1", "title": "Test task", "created_at": _DT, **kwargs})


def _response(task: Task, *, success: bool = True) -> Response:
    result = (
        OperationResult.ok(item=task.id, data=task)
        if success
        else OperationResult.error(item="x", message="Not found", error_code=404)
    )
    return Response(
        success=success, message="OK" if success else "Not found", data={"results": [result]}
    )


def _console() -> tuple[io.StringIO, Console]:
    buf = io.StringIO()
    return buf, Console(file=buf, no_color=True, highlight=False)


class TestTaskListRenderer:
    def test_fields_and_columns_declared(self):
        r = TaskListRenderer()
        assert "id" in r.get_fields()
        assert "title" in r.get_fields()
        assert "status" in r.get_fields()
        assert r.get_columns() == r.get_fields()

    def test_table_contains_task_row(self):
        r = TaskListRenderer()
        result = OperationResult.ok(item="t1", data=_task())
        response = Response(success=True, message="OK", data={"results": [result]})
        table = r.table(response)
        assert table.table.row_count == 1

    def test_table_empty_when_no_results(self):
        r = TaskListRenderer()
        response = Response(success=True, message="OK", data={"results": []})
        table = r.table(response)
        assert table.table.row_count == 0

    def test_serialize_includes_declared_fields(self):
        r = TaskListRenderer()
        result = OperationResult.ok(item="t1", data=_task(title="My task"))
        response = Response(success=True, message="OK", data={"results": [result]}, renderer=r)
        serialized = r.serialize(response)
        row = serialized["data"]["results"][0]
        assert row["id"] == "t1"
        assert row["title"] == "My task"


class TestTaskDetailRenderer:
    def test_rich_displays_task_title_in_panel(self):
        r = TaskDetailRenderer()
        buf, console = _console()
        r.rich(_response(_task(title="Important task")), console)
        assert "Important task" in buf.getvalue()

    def test_rich_displays_task_id(self):
        r = TaskDetailRenderer()
        buf, console = _console()
        r.rich(_response(_task(id="abc-123")), console)
        assert "abc-123" in buf.getvalue()

    def test_rich_shows_error_panel_when_no_result(self):
        r = TaskDetailRenderer()
        response = Response(success=False, message="Task not found", data={"results": []})
        buf, console = _console()
        r.rich(response, console)
        assert "Task not found" in buf.getvalue()

    def test_rich_shows_error_panel_when_result_failed(self):
        r = TaskDetailRenderer()
        error_result = OperationResult.error(item="x", message="Not found", error_code=404)
        response = Response(success=False, message="Not found", data={"results": [error_result]})
        buf, console = _console()
        r.rich(response, console)
        assert "Not found" in buf.getvalue()


class TestMinimalRenderers:
    def test_task_add_renderer_messages(self):
        r = TaskAddRenderer()
        assert r.success_message
        assert r.failure_message

    def test_task_complete_renderer_messages(self):
        r = TaskCompleteRenderer()
        assert r.success_message
        assert r.failure_message

    def test_task_delete_renderer_messages(self):
        r = TaskDeleteRenderer()
        assert r.success_message
        assert r.failure_message


class TestTaskSyncRenderer:
    def test_rich_setup_creates_progress_bar(self):
        r = TaskSyncRenderer()
        progress = r.rich_setup()
        assert r._progress is not None
        assert r._task_bar is not None
        assert progress is r._progress

    def test_rich_on_item_advances_progress(self):
        r = TaskSyncRenderer()
        r.rich_setup()
        before = r._progress.tasks[0].completed
        r.rich_on_item(MagicMock(), [MagicMock()])
        assert r._progress.tasks[0].completed > before

    def test_rich_summary_prints_count(self):
        r = TaskSyncRenderer()
        results = [
            OperationResult.ok(item=str(i), data=_task(id=str(i), title=f"T{i}")) for i in range(3)
        ]
        response = Response(success=True, message="Sync complete", data={"results": results})
        buf, console = _console()
        r.rich_summary(response, console)
        output = buf.getvalue()
        assert "Sync complete" in output
        assert "3 tasks imported" in output
