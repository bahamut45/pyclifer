"""Named exit codes with POSIX OS exit integration."""

_PROJECT_EXIT_CODE_MIN = 6
_PROJECT_EXIT_CODE_MAX = 125


class ExitCode:
    """Standard exit codes for pyclifer commands.

    Values are POSIX-safe (0-127) and serve as both the classification code
    in structured output (JSON, YAML) and the actual OS exit code.

    Projects register a subclass via @app_group(exit_codes_class=MyExitCode).
    Subclasses inherit all base codes and add project-specific ones in the
    6-125 range (0-5 are reserved for pyclifer, 126+ are reserved by the shell).

    Example:
        from pyclifer import ExitCode as _Base

        class ExitCode(_Base):
            QUOTA_EXCEEDED = 10
            RATE_LIMITED = 11
    """

    SUCCESS = 0
    ERROR = 1
    ALREADY_EXISTS = 2
    NOT_FOUND = 3
    PERMISSION_DENIED = 4
    INVALID_INPUT = 5


def validate_exit_codes_class(cls: type) -> None:
    """Raise ValueError if cls is not a valid ExitCode subclass.

    Args:
        cls: The class to validate.

    Raises:
        ValueError: When cls is not a subclass of ExitCode, or when it defines
            project-specific integer values outside the 6-125 range.
    """
    if not (isinstance(cls, type) and issubclass(cls, ExitCode)):
        raise ValueError(f"{cls!r} must be a subclass of ExitCode.")
    base_values = {v for k, v in vars(ExitCode).items() if not k.startswith("_")}
    invalid = {
        k: v
        for k, v in vars(cls).items()
        if not k.startswith("_")
        and isinstance(v, int)
        and v not in base_values
        and not (_PROJECT_EXIT_CODE_MIN <= v <= _PROJECT_EXIT_CODE_MAX)
    }
    if invalid:
        details = ", ".join(f"{k}={v}" for k, v in invalid.items())
        raise ValueError(
            f"Project exit code values must be in 6-125 (pyclifer uses 0-5, "
            f"shell reserves 126+). Invalid: {details}"
        )
