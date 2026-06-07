"""Pytest configuration for pyclifer tests."""

from importlib.metadata import PackageNotFoundError, version
from unittest.mock import Mock

import pytest

DEPENDENCIES = [
    "click-extra",
    "rich-click",
    "pyyaml",
    "xmltodict",
]


# noinspection PyUnusedLocal
def pytest_configure(config):
    """Displays dependency versions at startup."""
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
