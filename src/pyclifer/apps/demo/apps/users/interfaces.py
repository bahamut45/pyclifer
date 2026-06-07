"""Renderers and interface for the Users app."""

from __future__ import annotations

import datetime
import os
from typing import TYPE_CHECKING

from rich.panel import Panel

from pyclifer import BaseInterface, BaseRenderer, OperationResult, get_logger

from ...core.context import DemoContext
from .models import User

if TYPE_CHECKING:
    from rich.console import Console

    from pyclifer import Response

logger = get_logger(__name__)

_DEMO_USERS = [
    {"username": "alice", "email": "alice@example.com", "role": "admin"},
    {"username": "bob", "email": "bob@example.com", "role": "member"},
    {"username": "carol", "email": "carol@example.com", "role": "member"},
]

_DEMO_CREATED_AT = datetime.datetime(2024, 1, 1)


class UserListRenderer(BaseRenderer):
    """Declarative renderer for the user's list command."""

    model_class = User
    fields = ["username", "email", "role"]
    columns = ["username", "email", "role"]
    rich_title = "Users"
    success_message = "Users retrieved successfully."
    failure_message = "Failed to retrieve users."


class UserWhoamiRenderer(BaseRenderer):
    """Renderer for the whoami command — overrides rich() for a personalized panel."""

    model_class = User
    fields = ["username", "email", "role", "created_at"]
    columns = ["username", "email", "role", "created_at"]
    rich_title = "Whoami"
    success_message = "User identified."
    failure_message = "Failed to identify current user."

    def rich(self, response: Response, console: Console) -> None:
        """Display current user info in a Rich panel.

        Args:
            response: The command response carrying the user result.
            console: The Rich console to print to.
        """
        result = self._first_result(response, console)
        if result is None:
            return

        user: User = result.data
        grid = self._detail_grid()
        grid.add_row("Username", user.username)
        grid.add_row("Email", user.email)
        grid.add_row("Role", user.role)
        grid.add_row("Since", user.created_at.date().isoformat())
        console.print(
            Panel(grid, title=f"[bold]Logged in as[/bold] [green]{user.username}[/green]")
        )


class UserInterface(BaseInterface):
    """Interface for Users business logic."""

    ctx: DemoContext

    renderers = {
        "list_users": UserListRenderer,
        "whoami": UserWhoamiRenderer,
        # --- renderers --- (used by `pyclifer project add command` — do not remove)
    }

    def list_users(self) -> list[OperationResult]:
        """Return the user roster, seeding demo users on the first call.

        Returns:
            One OperationResult per user.
        """
        users = self.ctx.storage.get_users()
        if not users:
            users = self._seed_demo_users()
        logger.debug("list users: %d results", len(users))
        return [OperationResult.ok(item=u.username, data=u) for u in users]

    def whoami(self) -> list[OperationResult]:
        """Return the current Unix user, creating a profile in storage if needed.

        Returns:
            A single OperationResult with the current user as data.
        """
        username = os.getenv("USER", "unknown")
        user = self.ctx.storage.get_user(username)
        if user is None:
            user = User(
                username=username,
                email=f"{username}@example.com",
                role="admin",
                created_at=datetime.datetime.now(),
            )
            self.ctx.storage.upsert_user(user)
        logger.debug("whoami: %s", user.username)
        return [OperationResult.ok(item=user.username, data=user)]

    def _seed_demo_users(self) -> list[User]:
        """Populate storage with demo users on the first list call.

        Returns:
            The seeded list of User instances.
        """
        for raw in _DEMO_USERS:
            self.ctx.storage.upsert_user(User(**raw, created_at=_DEMO_CREATED_AT))
        return self.ctx.storage.get_users()

    # --- commands --- (used by `pyclifer project add command` — do not remove)
