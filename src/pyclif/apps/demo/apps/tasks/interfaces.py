"""Interface for the Tasks app."""

from __future__ import annotations

import datetime
import time
import uuid
from collections.abc import Iterator

from pyclif import BaseInterface, OperationResult, get_logger

from ...core.context import DemoContext
from .models import Task
from .renderers import (
    TaskAddRenderer,
    TaskCompleteRenderer,
    TaskDeleteRenderer,
    TaskDetailRenderer,
    TaskListRenderer,
    TaskSyncRenderer,
)

logger = get_logger(__name__)

_FAKE_SYNC_TITLES = [
    "Fix login bug",
    "Update documentation",
    "Review open PRs",
    "Deploy to staging",
    "Write integration tests",
    "Refactor auth module",
    "Add rate limiting",
    "Update dependencies",
]


class TaskInterface(BaseInterface):
    """Interface for Tasks business logic."""

    ctx: DemoContext

    renderers = {
        "list_tasks": TaskListRenderer,
        "add_task": TaskAddRenderer,
        "show_task": TaskDetailRenderer,
        "complete_task": TaskCompleteRenderer,
        "delete_task": TaskDeleteRenderer,
        "sync_tasks": TaskSyncRenderer,
        # --- renderers --- (used by `pyclif project add command` — do not remove)
    }

    def list_tasks(
        self,
        status: str | None = None,
        priority: str | None = None,
    ) -> list[OperationResult]:
        """Return all tasks, optionally filtered by status and priority.

        Pagination is handled at the command level via PaginatedResponse.

        Args:
            status: Only return tasks with this status. None means no filter.
            priority: Only return tasks with this priority. None means no filter.

        Returns:
            One OperationResult per matching task.
        """
        tasks = self.ctx.storage.get_tasks()
        if status:
            tasks = [t for t in tasks if t.status == status]
        if priority:
            tasks = [t for t in tasks if t.priority == priority]
        logger.debug("list tasks: %d results (status=%s priority=%s)", len(tasks), status, priority)
        return [OperationResult.ok(item=t.id, data=t) for t in tasks]

    def add_task(
        self,
        title: str = "",
        description: str = "",
        priority: str = "medium",
        due_date: datetime.date | None = None,
        tags: list[str] | None = None,
        assignee: str = "",
    ) -> list[OperationResult]:
        """Create and persist a new task.

        Args:
            title: Short task title.
            description: Optional longer description.
            priority: One of lows, medium, high.
            due_date: Optional due date.
            tags: Optional list of tag strings.
            assignee: Optional assignee name.

        Returns:
            A single OperationResult with the new task as data.
        """
        task = Task(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
            tags=tags or [],
            assignee=assignee,
            created_at=datetime.datetime.now(),
        )
        self.ctx.storage.upsert_task(task)
        logger.debug("add task: created %s", task.id)
        return [OperationResult.ok(item=task.id, message=f"Task '{title}' created.", data=task)]

    def show_task(self, task_id: str = "") -> list[OperationResult]:
        """Return a single task by id.

        Args:
            task_id: UUID of the task to retrieve.

        Returns:
            A single OperationResult with the task as data, or an error result
            with error_code 404 when not found.
        """
        task = self.ctx.storage.get_task(task_id)
        if task is None:
            return [
                OperationResult.error(
                    item=task_id, message=f"Task '{task_id}' not found.", error_code=404
                )
            ]
        return [OperationResult.ok(item=task.id, data=task)]

    def complete_task(self, task_id: str = "") -> list[OperationResult]:
        """Mark a task as done.

        Args:
            task_id: UUID of the task to complete.

        Returns:
            A successful result, or an error result when the task is not found
            or already done.
        """
        task = self.ctx.storage.get_task(task_id)
        if task is None:
            return [
                OperationResult.error(
                    item=task_id, message=f"Task '{task_id}' not found.", error_code=404
                )
            ]
        if task.status == "done":
            return [
                OperationResult.error(item=task_id, message=f"Task '{task_id}' is already done.")
            ]
        task.status = "done"
        self.ctx.storage.upsert_task(task)
        logger.debug("complete task: %s marked done", task_id)
        return [OperationResult.ok(item=task_id, message=f"Task '{task.title}' marked as done.")]

    def delete_task(self, task_id: str = "") -> list[OperationResult]:
        """Delete a task permanently.

        Args:
            task_id: UUID of the task to delete.

        Returns:
            A successful result, or an error result with error_code 404 when
            the task is not found.
        """
        found = self.ctx.storage.delete_task(task_id)
        if not found:
            return [
                OperationResult.error(
                    item=task_id, message=f"Task '{task_id}' not found.", error_code=404
                )
            ]
        logger.debug("delete task: %s removed", task_id)
        return [OperationResult.ok(item=task_id, message=f"Task '{task_id}' deleted.")]

    def sync_tasks(
        self, source: str = "https://remote.example.com/tasks"
    ) -> Iterator[OperationResult]:
        """Simulate a live sync from a remote source, yielding one result per task.

        Yields one OperationResult every 0.1 s to drive the streaming renderer.
        Credentials embedded in the URL are masked before logging.

        Args:
            source: URL of the remote task source. May contain embedded credentials.

        Yields:
            One OperationResult per imported task.
        """
        logger.debug("sync tasks from %s", source)
        for title in _FAKE_SYNC_TITLES:
            time.sleep(0.1)
            task = Task(
                id=str(uuid.uuid4()),
                title=title,
                created_at=datetime.datetime.now(),
            )
            self.ctx.storage.upsert_task(task)
            yield OperationResult.ok(item=task.id, data=task, message=f"Synced: {title}")

    # --- commands --- (used by `pyclif project add command` — do not remove)
