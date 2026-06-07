"""Tests for HandleResponseMixin and _apply_handle_response_to_group."""

from unittest.mock import MagicMock, patch

import click

# noinspection PyProtectedMember
from pyclifer.core.mixins.response import (
    _PYCLIFER_RESPONSE_DECIDED,
    HandleResponseMixin,
    _apply_handle_response_to_group,
)


class _PlainGroup:
    """Minimal group that is NOT a HandleResponseMixin, used to test the isinstance branch."""

    def __init__(self):
        self.commands = {}


class _MixinGroup(HandleResponseMixin, click.Group):
    pass


class TestApplyHandleResponseToGroup:
    """Tests for _apply_handle_response_to_group."""

    def test_non_mixin_group_does_not_set_handle_response_by_default(self):
        """Groups that are not HandleResponseMixin are left untouched."""
        group = _PlainGroup()
        # Should not raise and must not add the attribute.
        _apply_handle_response_to_group(group)
        assert not hasattr(group, "handle_response_by_default")

    def test_nested_group_leaf_is_wrapped_via_recursion(self):
        """Recursion into a nested group wraps its leaf commands (lines 38-39)."""

        # noinspection PyMissingOrEmptyDocstring
        def leaf_callback():
            pass

        leaf_cmd = MagicMock()
        leaf_cmd.commands = None  # leaf
        leaf_cmd.callback = leaf_callback

        inner_group = MagicMock()
        inner_group.commands = {"leaf": leaf_cmd}  # non-None → treated as group

        outer = _PlainGroup()
        outer.commands = {"sub": inner_group}

        patch_target = "pyclifer.core.decorators.returns_response"
        with patch(patch_target, side_effect=lambda f: f) as mock_wrap:
            _apply_handle_response_to_group(outer)

        mock_wrap.assert_called_once_with(leaf_callback)

    def test_command_with_none_callback_is_skipped(self):
        """Commands whose callback is None are skipped without error."""
        cmd = MagicMock()
        cmd.commands = None  # leaf
        cmd.callback = None

        group = _PlainGroup()
        group.commands = {"noop": cmd}

        _apply_handle_response_to_group(group)
        # callback must remain None — not wrapped
        assert cmd.callback is None

    def test_already_decided_callback_is_not_rewrapped(self):
        """Commands marked _PYCLIFER_RESPONSE_DECIDED are skipped (lines 44-48)."""

        # noinspection PyMissingOrEmptyDocstring
        def my_callback():
            pass

        setattr(my_callback, _PYCLIFER_RESPONSE_DECIDED, True)

        cmd = MagicMock()
        cmd.commands = None
        cmd.callback = my_callback

        group = _PlainGroup()
        group.commands = {"decided": cmd}

        _apply_handle_response_to_group(group)
        # callback must be the original function, not a wrapped version
        assert cmd.callback is my_callback
