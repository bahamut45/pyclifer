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

    Building an application configures loggers, which are global to the process. Handlers a
    test added, on any logger, are removed and closed afterwards, so they never leak.
    """
    handlers = {logger.name: list(logger.handlers) for logger in _all_loggers()}
    root_level = logging.getLogger().level
    yield
    for logger in _all_loggers():
        for handler in list(logger.handlers):
            if handler not in handlers.get(logger.name, []):
                logger.removeHandler(handler)
                handler.close()
    logging.getLogger().setLevel(root_level)
