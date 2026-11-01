"""The output formats a pyclifer application can answer in."""

OUTPUT_FORMATS: tuple[str, ...] = ("json", "yaml", "table", "rich", "raw", "text")
"""Every valid output format, in the order the --output-format option lists them."""


def validate_output_format(output_format: str, name: str = "output format") -> None:
    """Raise ValueError if output_format is not one of the known formats.

    Args:
        output_format: The format name to check.
        name: How the value is called in the error message, for example the parameter name.

    Raises:
        ValueError: When the name is not in OUTPUT_FORMATS.
    """
    if output_format not in OUTPUT_FORMATS:
        valid = ", ".join(OUTPUT_FORMATS)
        raise ValueError(f"Unknown {name} '{output_format}'. Valid formats: {valid}")
