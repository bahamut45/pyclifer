"""Fixtures shared by the integration tests."""

import pytest


@pytest.fixture(autouse=True)
def isolated_environment(tmp_path, monkeypatch):
    """Keep integration tests away from the real user and system configuration.

    Applications are built with the name cli, so a config file left in the user's own config
    directory would otherwise be loaded.
    """
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
