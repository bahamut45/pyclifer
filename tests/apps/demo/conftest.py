"""Shared fixtures for demo app tests."""

from __future__ import annotations

import importlib
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

_demo_context_mod = importlib.import_module("pyclif.apps.demo.core.context")


@pytest.fixture
def storage() -> MagicMock:
    """Return a fresh MagicMock pre-wired as a Storage instance."""
    return MagicMock()


@pytest.fixture
def runner() -> CliRunner:
    """Return a Click test runner."""
    return CliRunner()


@pytest.fixture
def demo_context_mod():
    """Expose the demo context module for patch.object calls."""
    return _demo_context_mod
