"""Renderer and interface for the Tasks app."""

from pyclif import BaseInterface, BaseRenderer

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
        # --- renderers --- (used by `pyclif project add command` — do not remove)
    }

    # --- commands --- (used by `pyclif project add command` — do not remove)
