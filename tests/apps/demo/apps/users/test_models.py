"""Tests for the User model."""

from __future__ import annotations

import datetime

from pyclifer.apps.demo.apps.users.models import User

_DT = datetime.datetime(2024, 1, 1)


class TestUser:
    def test_valid_construction(self):
        user = User(username="alice", email="alice@example.com", created_at=_DT)
        assert user.username == "alice"
        assert user.email == "alice@example.com"

    def test_default_role_is_member(self):
        user = User(username="bob", email="bob@example.com", created_at=_DT)
        assert user.role == "member"

    def test_role_can_be_set_to_admin(self):
        user = User(username="admin", email="admin@example.com", created_at=_DT, role="admin")
        assert user.role == "admin"
