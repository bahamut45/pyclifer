"""Pytest configuration for pyclifer tests."""

import os
from importlib.metadata import PackageNotFoundError, version
from unittest.mock import Mock

import pytest

from pyclifer.testing import cli_invoke, cli_runner  # noqa: F401 — re-exported pytest fixtures

DEPENDENCIES = [
    "click-extra",
    "rich-click",
    "pyyaml",
    "xmltodict",
]


# rich-click forces a colour terminal when one of these is set (GitHub Actions sets the last one),
# which puts ANSI codes in the middle of the text that tests compare. A test that wants colour
# sets the variable itself.
COLOUR_FORCING_VARIABLES = ("FORCE_COLOR", "PY_COLORS", "GITHUB_ACTIONS")


# noinspection PyUnusedLocal
def pytest_configure(config):
    """Make the environment independent of the machine, and display dependency versions."""
    for variable in COLOUR_FORCING_VARIABLES:
        os.environ.pop(variable, None)

    print("\n" + "=" * 70)
    print("Dependencies versions:")
    print("=" * 70)

    for dep in sorted(DEPENDENCIES):
        try:
            v = version(dep)
            print(f"  {dep}: {v}")
        except PackageNotFoundError:
            print(f"  {dep}: NOT INSTALLED")

    print("=" * 70 + "\n")


@pytest.fixture
def mock_click_context():
    """Provide a mock click context for tests."""
    context = Mock()
    context.find_root().info_name = "test-cli"
    return context


@pytest.fixture
def mock_formats():
    """Provide mock formats for testing."""
    return [
        Mock(value="toml"),
        Mock(value="yaml"),
        Mock(value="json"),
    ]
