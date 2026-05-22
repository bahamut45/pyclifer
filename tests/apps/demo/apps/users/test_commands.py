"""CLI integration tests for user commands — invoked via CliRunner through the full pyclif app."""

from __future__ import annotations

import datetime
import importlib
import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from pyclif.apps.demo.apps.users.models import User
from pyclif.cli import app

_demo_context_mod = importlib.import_module("pyclif.apps.demo.core.context")
_users_iface_mod = importlib.import_module("pyclif.apps.demo.apps.users.interfaces")

_DT = datetime.datetime(2024, 1, 1)


def _user(**kwargs) -> User:
    return User(**{"username": "alice", "email": "alice@example.com", "created_at": _DT, **kwargs})


@pytest.fixture
def storage() -> MagicMock:
    return MagicMock()


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _run(runner, storage, *args, **kwargs):
    """Invoke an app command with Storage mocked."""
    with patch.object(_demo_context_mod, "Storage", return_value=storage):
        return runner.invoke(app, list(args), **kwargs)


class TestListUsersCommand:
    def test_success_with_users(self, runner, storage):
        storage.get_users.return_value = [_user()]
        result = _run(runner, storage, "demo", "users", "list")
        assert result.exit_code == 0

    def test_empty_shows_no_dataset(self, runner, storage):
        storage.get_users.side_effect = [[], []]
        result = _run(runner, storage, "demo", "users", "list")
        assert result.exit_code == 0

    def test_json_output_includes_username(self, runner, storage):
        storage.get_users.return_value = [_user(username="carol")]
        result = _run(runner, storage, "--output-format", "json", "demo", "users", "list")
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["data"]["results"][0]["username"] == "carol"


class TestWhoamiCommand:
    def test_success_exits_zero(self, runner, storage):
        storage.get_user.return_value = _user()
        with patch.object(_users_iface_mod.os, "getenv", return_value="alice"):
            result = _run(runner, storage, "demo", "users", "whoami")
        assert result.exit_code == 0

    def test_json_output_shows_username(self, runner, storage):
        storage.get_user.return_value = _user(username="alice")
        with patch.object(_users_iface_mod.os, "getenv", return_value="alice"):
            result = _run(runner, storage, "--output-format", "json", "demo", "users", "whoami")
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["data"]["results"][0]["username"] == "alice"

    def test_creates_profile_when_user_absent(self, runner, storage):
        storage.get_user.return_value = None
        with patch.object(_users_iface_mod.os, "getenv", return_value="newperson"):
            result = _run(runner, storage, "demo", "users", "whoami")
        assert result.exit_code == 0
        storage.upsert_user.assert_called_once()
