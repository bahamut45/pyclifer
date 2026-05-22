"""JSON file backend for the demo app."""

from __future__ import annotations

import json
import pathlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..apps.tasks.models import Task
    from ..apps.users.models import User

DATA_PATH = pathlib.Path.home() / ".config" / "pyclif" / "demo.json"


class Storage:
    """Read/write helper for the demo JSON data store.

    Persists tasks and users in a single JSON file at DATA_PATH.
    Created automatically on first writing.
    """

    def __init__(self) -> None:
        self._path = DATA_PATH

    def load(self) -> dict[str, Any]:
        """Load the full data store from the disk.

        Returns:
            Dict with 'tasks' and 'users' lists. Returns empty lists when the
            file does not exist yet.
        """
        if not self._path.exists():
            return {"tasks": [], "users": []}
        with self._path.open() as f:
            return json.load(f)

    def save(self, data: dict[str, Any]) -> None:
        """Persist the full data store to disk.

        Args:
            data: Dict with 'tasks' and 'users' lists to write.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w") as f:
            json.dump(data, f, indent=2, default=str)

    def get_tasks(self) -> list[Task]:
        """Return all stored tasks as model instances.

        Returns:
            List of Task objects, empty when no tasks are stored.
        """
        from ..apps.tasks.models import Task  # noqa: PLC0415

        return [Task(**t) for t in self.load().get("tasks", [])]

    def get_users(self) -> list[User]:
        """Return all stored users as model instances.

        Returns:
            List of User objects, empty when no users are stored.
        """
        from ..apps.users.models import User  # noqa: PLC0415

        return [User(**u) for u in self.load().get("users", [])]

    def get_task(self, task_id: str) -> Task | None:
        """Return a single task by id, or None if not found.

        Args:
            task_id: UUID string identifying the task.

        Returns:
            The matching Task, or None.
        """
        from ..apps.tasks.models import Task  # noqa: PLC0415

        for raw in self.load().get("tasks", []):
            if raw["id"] == task_id:
                return Task(**raw)
        return None

    def upsert_task(self, task: Task) -> None:
        """Insert or replace a task in the store.

        Matches by task.id. Appends when no existing task shares the id.

        Args:
            task: Task instance to persist.
        """
        data = self.load()
        tasks = data.get("tasks", [])
        task_dict = task.model_dump(mode="json")
        for i, raw in enumerate(tasks):
            if raw["id"] == task.id:
                tasks[i] = task_dict
                break
        else:
            tasks.append(task_dict)
        data["tasks"] = tasks
        self.save(data)

    def get_user(self, username: str) -> User | None:
        """Return a single user by username, or None if not found.

        Args:
            username: Username string identifying the user.

        Returns:
            The matching User, or None.
        """
        from ..apps.users.models import User  # noqa: PLC0415

        for raw in self.load().get("users", []):
            if raw["username"] == username:
                return User(**raw)
        return None

    def upsert_user(self, user: User) -> None:
        """Insert or replace a user in the store.

        Matches by user.username. Appends when no existing user shares the username.

        Args:
            user: User instance to persist.
        """
        data = self.load()
        users = data.get("users", [])
        user_dict = user.model_dump(mode="json")
        for i, raw in enumerate(users):
            if raw["username"] == user.username:
                users[i] = user_dict
                break
        else:
            users.append(user_dict)
        data["users"] = users
        self.save(data)

    def delete_task(self, task_id: str) -> bool:
        """Remove a task from the store.

        Args:
            task_id: UUID string identifying the task to delete.

        Returns:
            True when the task was found and deleted, False when not found.
        """
        data = self.load()
        tasks = data.get("tasks", [])
        new_tasks = [t for t in tasks if t["id"] != task_id]
        if len(new_tasks) == len(tasks):
            return False
        data["tasks"] = new_tasks
        self.save(data)
        return True
