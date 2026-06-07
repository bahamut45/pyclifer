"""Output renderers for the Tasks app."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rich.panel import Panel
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn
from rich.text import Text

from pyclifer import BaseRenderer

from .models import Task

if TYPE_CHECKING:
    from rich.console import Console
    from rich.progress import TaskID

    from pyclifer import OperationResult, Response

_STATUS_COLORS: dict[str, str] = {
    "open": "blue",
    "in_progress": "yellow",
    "done": "green",
}
_PRIORITY_COLORS: dict[str, str] = {
    "low": "dim",
    "medium": "white",
    "high": "red",
}


class TaskListRenderer(BaseRenderer):
    """Declarative renderer for the task list command."""

    model_class = Task
    fields = ["id", "title", "priority", "status", "due_date", "assignee"]
    columns = ["id", "title", "priority", "status", "due_date", "assignee"]
    rich_title = "Tasks"
    success_message = "Tasks retrieved successfully."
    failure_message = "Failed to retrieve tasks."


class TaskDetailRenderer(BaseRenderer):
    """Renderer for a single task — a custom Rich panel with a colored status badge."""

    model_class = Task
    rich_title = "Task"
    success_message = "Task retrieved successfully."
    failure_message = "Task not found."

    def rich(self, response: Response, console: Console) -> None:
        """Display task fields in a panel with a colored status badge.

        Args:
            response: The command response carrying the task result.
            console: The Rich console to print to.
        """
        result = self._first_result(response, console)
        if result is None:
            return

        task: Task = result.data
        grid = self._detail_grid()

        status_color = _STATUS_COLORS.get(task.status, "white")
        priority_color = _PRIORITY_COLORS.get(task.priority, "white")

        grid.add_row("ID", task.id)
        grid.add_row("Title", task.title)
        grid.add_row("Description", task.description or "[dim]-[/dim]")
        grid.add_row("Priority", Text(task.priority, style=priority_color))
        grid.add_row("Status", Text(task.status, style=f"bold {status_color}"))
        grid.add_row("Due", task.due_date.isoformat() if task.due_date else "[dim]-[/dim]")
        grid.add_row("Tags", ", ".join(task.tags) if task.tags else "[dim]-[/dim]")
        grid.add_row("Assignee", task.assignee or "[dim]-[/dim]")
        grid.add_row("Created", task.created_at.date().isoformat())

        console.print(Panel(grid, title=f"[bold]{self.rich_title}[/bold] [dim]{task.id}[/dim]"))


class TaskAddRenderer(BaseRenderer):
    """Minimal renderer for the task add command."""

    rich_title = "Task added"
    success_message = "Task added successfully."
    failure_message = "Failed to add task."


class TaskCompleteRenderer(BaseRenderer):
    """Minimal renderer for the task complete command."""

    rich_title = "Task completed"
    success_message = "Task marked as done."
    failure_message = "Failed to complete task."


class TaskDeleteRenderer(BaseRenderer):
    """Minimal renderer for the task delete command."""

    rich_title = "Task deleted"
    success_message = "Task deleted."
    failure_message = "Task not found."


class TaskSyncRenderer(BaseRenderer):
    """Streaming renderer for the task sync command — progress bar and summary rule."""

    rich_title = "Syncing tasks"
    success_message = "Sync completed."
    failure_message = "Sync failed."

    _progress: Progress | None = None
    _task_bar: TaskID | None = None

    def rich_setup(self) -> Any:
        """Create and store a Progress bar for the live sync display.

        Returns:
            The Progress renderable to wrap in Live().
        """
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
        )
        self._progress = progress
        self._task_bar = progress.add_task("Syncing…", total=None)
        return self._progress

    def rich_on_item(self, result: OperationResult, all_so_far: list) -> None:
        """Advance the progress bar after each received task.

        Args:
            result: The latest OperationResult from the stream.
            all_so_far: All results received so far.
        """
        assert self._progress is not None
        assert self._task_bar is not None
        self._progress.advance(self._task_bar)

    def rich_summary(self, response: Response, console: Console) -> None:
        """Print a rule and import count after the stream closes.

        Args:
            response: The fully materialized response with all results.
            console: The Rich console to print to.
        """
        results = response.data.get("results", [])
        console.rule("[bold green]Sync complete")
        console.print(f"{len(results)} tasks imported.")
