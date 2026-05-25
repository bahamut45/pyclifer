"""Tests for ExitCode and validate_exit_codes_class."""

import pytest

from pyclif.core.output.exit_codes import (
    _PROJECT_EXIT_CODE_MAX,
    _PROJECT_EXIT_CODE_MIN,
    ExitCode,
    validate_exit_codes_class,
)


class TestExitCodeValues:
    """Tests that ExitCode attributes equal their expected integer values."""

    def test_success_is_zero(self):
        assert ExitCode.SUCCESS == 0

    def test_error_is_one(self):
        assert ExitCode.ERROR == 1

    def test_already_exists_is_two(self):
        assert ExitCode.ALREADY_EXISTS == 2

    def test_not_found_is_three(self):
        assert ExitCode.NOT_FOUND == 3

    def test_permission_denied_is_four(self):
        assert ExitCode.PERMISSION_DENIED == 4

    def test_invalid_input_is_five(self):
        assert ExitCode.INVALID_INPUT == 5


class TestExitCodeSubclass:
    """Tests for ExitCode subclassing behaviour."""

    def test_subclass_inherits_base_codes(self):
        class MyExitCode(ExitCode):
            QUOTA_EXCEEDED = 10

        assert MyExitCode.SUCCESS == 0
        assert MyExitCode.ERROR == 1
        assert MyExitCode.NOT_FOUND == 3
        assert MyExitCode.QUOTA_EXCEEDED == 10

    def test_subclass_adds_project_codes(self):
        class MyExitCode(ExitCode):
            RATE_LIMITED = 11

        assert MyExitCode.RATE_LIMITED == 11


class TestValidateExitCodesClass:
    """Tests for validate_exit_codes_class."""

    def test_accepts_base_class(self):
        validate_exit_codes_class(ExitCode)

    def test_accepts_valid_subclass(self):
        class MyExitCode(ExitCode):
            QUOTA_EXCEEDED = 10

        validate_exit_codes_class(MyExitCode)

    def test_accepts_subclass_at_boundary_min(self):
        class MyExitCode(ExitCode):
            LOW = _PROJECT_EXIT_CODE_MIN

        validate_exit_codes_class(MyExitCode)

    def test_accepts_subclass_at_boundary_max(self):
        class MyExitCode(ExitCode):
            HIGH = _PROJECT_EXIT_CODE_MAX

        validate_exit_codes_class(MyExitCode)

    def test_raises_when_not_a_subclass(self):
        class Unrelated:
            pass

        with pytest.raises(ValueError, match="must be a subclass of ExitCode"):
            validate_exit_codes_class(Unrelated)

    def test_raises_when_not_a_class(self):
        with pytest.raises(ValueError, match="must be a subclass of ExitCode"):
            validate_exit_codes_class(42)  # type: ignore[arg-type]

    def test_raises_for_value_below_min(self):
        class MyExitCode(ExitCode):
            TOO_LOW = -1

        with pytest.raises(ValueError, match="TOO_LOW=-1"):
            validate_exit_codes_class(MyExitCode)

    def test_raises_for_value_above_max(self):
        class MyExitCode(ExitCode):
            TOO_HIGH = _PROJECT_EXIT_CODE_MAX + 1

        with pytest.raises(ValueError, match="TOO_HIGH=126"):
            validate_exit_codes_class(MyExitCode)

    def test_error_message_names_offending_code(self):
        class MyExitCode(ExitCode):
            SHELL_RESERVED = 127

        with pytest.raises(ValueError, match="SHELL_RESERVED=127"):
            validate_exit_codes_class(MyExitCode)

    def test_base_values_in_subclass_pass_unchanged(self):
        """Base ExitCode values (0-5) must not be flagged as out-of-range."""

        class MyExitCode(ExitCode):
            pass

        validate_exit_codes_class(MyExitCode)
