"""Tests for UserInterface — Storage is mocked to avoid filesystem I/O."""

from __future__ import annotations

import datetime
import importlib
from unittest.mock import MagicMock, patch

import pytest

from pyclif.apps.demo.apps.users.interfaces import _DEMO_USERS, UserInterface
from pyclif.apps.demo.apps.users.models import User
from pyclif.apps.demo.core.context import DemoContext

_DT = datetime.datetime(2024, 1, 1)
_users_iface_mod = importlib.import_module("pyclif.apps.demo.apps.users.interfaces")


def _user(**kwargs) -> User:
    return User(**{"username": "alice", "email": "alice@example.com", "created_at": _DT, **kwargs})


@pytest.fixture
def ctx():
    c = DemoContext()
    c._storage = MagicMock()
    return c


@pytest.fixture
def iface(ctx):
    return UserInterface(ctx)


@pytest.fixture
def storage(ctx):
    return ctx._storage


class TestListUsers:
    def test_returns_existing_users(self, iface, storage):
        storage.get_users.return_value = [
            _user(username="alice"),
            _user(username="bob", email="b@e.com"),
        ]
        results = iface.list_users()
        assert len(results) == 2
        assert all(r.success for r in results)

    def test_seeds_demo_users_when_storage_empty(self, iface, storage):
        seeded = [_user(username=u["username"], email=u["email"]) for u in _DEMO_USERS]
        storage.get_users.side_effect = [[], seeded]
        results = iface.list_users()
        assert len(results) == len(_DEMO_USERS)
        assert storage.upsert_user.call_count == len(_DEMO_USERS)

    def test_result_items_are_usernames(self, iface, storage):
        storage.get_users.return_value = [_user(username="alice")]
        results = iface.list_users()
        assert results[0].item == "alice"


class TestWhoami:
    def test_returns_existing_user(self, iface, storage):
        user = _user(username="testuser")
        storage.get_user.return_value = user
        with patch.object(_users_iface_mod.os, "getenv", return_value="testuser"):
            results = iface.whoami()
        assert results[0].success
        assert results[0].data is user

    def test_creates_user_when_absent(self, iface, storage):
        storage.get_user.return_value = None
        with patch.object(_users_iface_mod.os, "getenv", return_value="newuser"):
            results = iface.whoami()
        assert results[0].success
        assert results[0].data.username == "newuser"
        storage.upsert_user.assert_called_once()

    def test_created_user_has_admin_role(self, iface, storage):
        storage.get_user.return_value = None
        with patch.object(_users_iface_mod.os, "getenv", return_value="someone"):
            results = iface.whoami()
        assert results[0].data.role == "admin"

    def test_falls_back_to_unknown_when_env_unset(self, iface, storage):
        storage.get_user.return_value = None
        with patch.object(_users_iface_mod.os, "getenv", return_value="unknown"):
            results = iface.whoami()
        assert results[0].data.username == "unknown"
