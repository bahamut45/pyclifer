"""Data models for the Tasks app."""

from __future__ import annotations

import datetime

import pydantic

from pyclif import BaseModel

from ...core.constants import PRIORITIES, STATUSES


class Task(BaseModel):
    """Single task in the demo task manager."""

    id: str
    title: str
    description: str = ""
    priority: str = "medium"
    status: str = "open"
    due_date: datetime.date | None = None
    tags: list[str] = []
    assignee: str = ""
    created_at: datetime.datetime

    @pydantic.field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        """Reject priority values outside the allowed set.

        Args:
            v: The raw priority string.

        Returns:
            The validated priority string.

        Raises:
            ValueError: When v is not in PRIORITIES.
        """
        if v not in PRIORITIES:
            raise ValueError(f"priority must be one of {PRIORITIES}, got {v!r}")
        return v

    @pydantic.field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Reject status values outside the allowed set.

        Args:
            v: The raw status string.

        Returns:
            The validated status string.

        Raises:
            ValueError: When v is not in STATUSES.
        """
        if v not in STATUSES:
            raise ValueError(f"status must be one of {STATUSES}, got {v!r}")
        return v
