"""Renderer and interface for the Users app."""

from __future__ import annotations

from pyclif import BaseInterface, BaseRenderer, OperationResult

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
        "list": UsersRenderer,
        "whoami": UsersRenderer,
        # --- renderers --- (used by `pyclif project add command` — do not remove)
    }

    def list(self) -> list[OperationResult]:
        """List users.

        Returns:
            List of OperationResult objects.
        """
        # TODO: implement
        return []

    def whoami(self) -> list[OperationResult]:
        """Whoami user.

        Returns:
            List of OperationResult objects.
        """
        # TODO: implement
        return []

    # --- commands --- (used by `pyclif project add command` — do not remove)
