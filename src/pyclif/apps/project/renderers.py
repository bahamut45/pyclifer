"""Renderers for pyclif project scaffolding commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress as RichProgress
from rich.progress import SpinnerColumn, TextColumn

from pyclif.core.output.renderer import BaseRenderer

if TYPE_CHECKING:
    from rich.progress import TaskID

    from pyclif.core.output.responses import OperationResult, Response


class ScaffoldingRenderer(BaseRenderer):
    """Renderer for scaffolding commands (init, add app, add command, add integration).

    Table and JSON output show the file path and action (created/modified/error).
    Rich output shows a live spinner per file during execution, then a summary panel.
    """

    fields = ["item", "action", "success", "message"]
    columns = ["item", "action"]
    rich_title = "Scaffolding"

    _ACTION_LABEL: dict[str, str] = {
        "created": ":sparkles:  created",
        "modified": ":pencil2:  modified",
    }

    def __init__(self, name: str = "") -> None:
        """Store optional project/resource name for dynamic messages.

        Args:
            name: Human-readable name used in success/failure messages.
        """
        self.name = name
        self._progress: RichProgress | None = None
        self._task_id: TaskID | None = None

    def get_success_message(self, results: list) -> str:
        """Return a success message including the resource name if set.

        Args:
            results: All OperationResult items from the batch.

        Returns:
            Human-readable success message.
        """
        if self.name:
            return f"'{self.name}' created successfully."
        succeeded = sum(1 for r in results if r.success)
        return f"{succeeded} file(s) created."

    def get_failure_message(self, results: list) -> str:
        """Return a failure message including the resource name if set.

        Args:
            results: All OperationResult items from the batch.

        Returns:
            Human-readable failure message.
        """
        if self.name:
            return f"'{self.name}' creation failed."
        failed = sum(1 for r in results if not r.success)
        return f"{failed}/{len(results)} file(s) failed."

    def _result_to_row(self, result: OperationResult, columns: list[str]) -> dict:
        """Map an OperationResult to a table row with a formatted action label.

        Args:
            result: The operation result to map.
            columns: Column names (unused here — mapping is fixed).

        Returns:
            Dict with item path and formatted action label.
        """
        if result.success:
            action_raw = result.data.get("action", "") if isinstance(result.data, dict) else ""
            action = self._ACTION_LABEL.get(action_raw, action_raw)
        else:
            action = f":x:  {result.message}"
        return {"item": result.item, "action": action}

    def rich_setup(self) -> RichProgress:
        """Create the progress bar for the Live context.

        Returns:
            A Progress instance used as the Live renderable.
        """
        progress = RichProgress(SpinnerColumn(), TextColumn("{task.description}"))
        self._progress = progress
        self._task_id = progress.add_task("Scaffolding…")
        return progress

    def rich_on_item(self, result: OperationResult, all_so_far: list) -> None:
        """Update the progress bar description with the latest file path.

        Args:
            result: The latest OperationResult.
            all_so_far: All results received so far.
        """
        assert self._progress is not None and self._task_id is not None
        icon = ":white_check_mark:" if result.success else ":x:"
        self._progress.update(self._task_id, description=f"{icon}  {result.item}")

    def rich_summary(self, response: Response, console: Console) -> None:
        """Print a summary panel after all files are processed.

        Args:
            response: The fully materialized response.
            console: The Rich console to print to.
        """
        icon = "[green]✓[/]" if response.success else "[red]✗[/]"
        console.print(Panel(f"{icon} {response.message}", title=self.rich_title))
