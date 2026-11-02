"""The test session does not inherit a colour setting from the machine."""

import os

import pytest

from tests.conftest import COLOUR_FORCING_VARIABLES


@pytest.mark.parametrize("variable", COLOUR_FORCING_VARIABLES)
def test_a_colour_forcing_variable_is_not_inherited(variable):
    """GitHub Actions sets GITHUB_ACTIONS, and rich-click then colours the captured output."""
    assert variable not in os.environ
