"""Fixtures shared by the integration tests."""

import logging

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


def _all_loggers() -> list[logging.Logger]:
    """The root logger and every logger created so far."""
    names = list(logging.root.manager.loggerDict)
    return [logging.getLogger()] + [logging.getLogger(name) for name in names]


@pytest.fixture(autouse=True)
def restore_logging():
    """Give every test the logging configuration it found.

    Building an application configures loggers, which are global to the process. On the way
    out, every logger gets back exactly the handlers it had, and handlers a test added are closed.
    """
    original = {logger.name: list(logger.handlers) for logger in _all_loggers()}
    root_level = logging.getLogger().level
    yield
    for logger in _all_loggers():
        kept = original.get(logger.name, [])
        for handler in logger.handlers:
            if handler not in kept:
                handler.close()
        logger.handlers[:] = kept
    logging.getLogger().setLevel(root_level)
