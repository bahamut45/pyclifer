"""Renderer and interface for the Users app."""

from pyclif import BaseInterface, BaseRenderer

from .models import Users


class UsersRenderer(BaseRenderer):
    """Output renderer for Users commands."""

    model_class = Users
    columns = ["item", "success"]
    success_message = "Users operation completed."
    failure_message = "Users operation failed."


class UsersInterface(BaseInterface):
    """Interface for Users business logic."""

    renderers = {
        # --- renderers --- (used by `pyclif project add command` — do not remove)
    }

    # --- commands --- (used by `pyclif project add command` — do not remove)
