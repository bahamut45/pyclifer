"""Tests for the Task model validators."""

from __future__ import annotations

import datetime

import pytest

from pyclif.apps.demo.apps.tasks.models import Task

_DT = datetime.datetime(2024, 1, 1)


class TestTask:
    def test_valid_construction(self):
        task = Task(id="abc", title="Fix bug", created_at=_DT)
        assert task.id == "abc"
        assert task.title == "Fix bug"

    def test_default_values(self):
        task = Task(id="1", title="T", created_at=_DT)
        assert task.status == "open"
        assert task.priority == "medium"
        assert task.description == ""
        assert task.tags == []
        assert task.assignee == ""
        assert task.due_date is None

    def test_invalid_priority_raises(self):
        with pytest.raises(ValueError, match="priority must be one of"):
            Task(id="1", title="T", created_at=_DT, priority="urgent")

    def test_invalid_status_raises(self):
        with pytest.raises(ValueError, match="status must be one of"):
            Task(id="1", title="T", created_at=_DT, status="blocked")

    def test_all_valid_priorities_accepted(self):
        for p in ("low", "medium", "high"):
            task = Task(id="1", title="T", created_at=_DT, priority=p)
            assert task.priority == p

    def test_all_valid_statuses_accepted(self):
        for s in ("open", "in_progress", "done"):
            task = Task(id="1", title="T", created_at=_DT, status=s)
            assert task.status == s
