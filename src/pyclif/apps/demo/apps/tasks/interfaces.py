"""Renderer and interface for the Tasks app."""

from __future__ import annotations

from pyclif import BaseInterface, BaseRenderer, OperationResult

from .models import Tasks


class TasksRenderer(BaseRenderer):
    """Output renderer for Tasks commands."""

    model_class = Tasks
    columns = ["item", "success"]
    success_message = "Tasks operation completed."
    failure_message = "Tasks operation failed."


class TasksInterface(BaseInterface):
    """Interface for Tasks business logic."""

    renderers = {
        "list": TasksRenderer,
        "add": TasksRenderer,
        "show": TasksRenderer,
        "complete": TasksRenderer,
        "delete": TasksRenderer,
        "sync": TasksRenderer,
        # --- renderers --- (used by `pyclif project add command` — do not remove)
    }

    def list(self) -> list[OperationResult]:
        """List tasks.

        Returns:
            List of OperationResult objects.
        """
        # TODO: implement
        return []

    def add(self) -> list[OperationResult]:
        """Add tasks.

        Returns:
            List of OperationResult objects.
        """
        # TODO: implement
        return []

    def show(self) -> list[OperationResult]:
        """Show tasks.

        Returns:
            List of OperationResult objects.
        """
        # TODO: implement
        return []

    def complete(self) -> list[OperationResult]:
        """Complete tasks.

        Returns:
            List of OperationResult objects.
        """
        # TODO: implement
        return []

    def delete(self) -> list[OperationResult]:
        """Delete tasks.

        Returns:
            List of OperationResult objects.
        """
        # TODO: implement
        return []

    def sync(self) -> list[OperationResult]:
        """Sync tasks.

        Returns:
            List of OperationResult objects.
        """
        # TODO: implement
        return []

    # --- commands --- (used by `pyclif project add command` — do not remove)
