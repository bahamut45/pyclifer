"""Data models for the Users app."""

from __future__ import annotations

import datetime

from pyclifer import BaseModel

ROLES = ["admin", "member"]


class User(BaseModel):
    """Single user in the demo task manager."""

    username: str
    email: str
    role: str = "member"
    created_at: datetime.datetime
