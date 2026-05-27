"""Utility functions and classes for creating and formatting rich tables."""

import dataclasses
import datetime
from operator import attrgetter
from typing import Any

from rich import box
from rich.table import Column, Table


def convert_bool_to_emoji(value: object) -> str:
    """Convert a value to an emoji checkmark or cross.

    Args:
        value: The value to convert.

    Returns:
        Green checkmark for truthy values, red cross for falsy values.
    """
    return "[green]:heavy_check_mark:[/]" if value else "[red]:heavy_multiplication_x:[/]"


class CliTableColumn(Column):
    """Column definition for CLI tables with serialization support."""

    def to_dict(self) -> dict:
        """Convert the column object to a dictionary.

        Returns a dictionary of all non-private fields and their values,
        excluding fields that have default values.

        Returns:
            Dictionary representation of the column.
        """
        return dict(
            (f.name, attrgetter(f.name)(self))
            for f in dataclasses.fields(self)  # type: ignore
            if attrgetter(f.name)(self) != f.default and not f.name.startswith("_")
        )


class CliTable:
    """Create and manage tables for CLI output with custom styling.

    This class wraps the Rich library's Table to provide convenient methods
    for adding columns and rows with automatic formatting.
    """

    table_style = {
        "show_lines": True,
        "row_styles": ["none", "dim"],
        "border_style": "bright_blue",
        "header_style": "bold blue",
        "box": box.ROUNDED,
    }

    def __init__(
        self,
        fields: dict,
        rows: list | dict,
        table_style: dict | None = None,
        datetime_format: str = "%Y-%m-%d %H:%M",
        date_format: str = "%Y-%m-%d",
    ):
        """Initialize the CLI table with columns and rows.

        Args:
            fields: Dictionary of field names to CliTableColumn objects.
            rows: Single dictionary or list of dictionaries representing rows.
            table_style: Optional dictionary to override default table styling.
            datetime_format: strftime format string for datetime values.
            date_format: strftime format string for date values.
        """
        if isinstance(table_style, dict):
            self.table_style |= table_style
        self.datetime_format = datetime_format
        self.date_format = date_format
        # noinspection PyArgumentList
        self.table = Table(**self.table_style)
        self.update_columns(fields)
        self.update_rows(fields, rows)

    def __rich__(self) -> Table | str:
        """Return the table for rich rendering.

        Returns:
            The rich Table object or a message if no data exists.
        """
        return self.table if self.table.row_count != 0 else "[i]No dataset available.[/i]"

    def update_columns(self, fields: dict) -> None:
        """Add columns to the table from field definitions.

        Args:
            fields: Dictionary of field names to CliTableColumn objects.
        """
        for field in fields.values():
            self.table.add_column(**field.to_dict())

    def update_rows(self, fields: dict, rows: list | dict) -> None:
        """Add rows to the table.

        Accepts either a single dictionary or list of dictionaries representing
        rows. Each row is processed to extract values matching field definitions.

        Args:
            fields: Dictionary of field names to column definitions.
            rows: Single dictionary or list of dictionaries for rows.
        """
        if rows is not None:
            if isinstance(rows, dict):
                rows = [rows]
            for row in rows:
                columns = self._generate_columns(fields, row)
                self.table.add_row(*columns)

    def _generate_columns(self, fields: dict, row: dict) -> list:
        """Generate column values from a row and field definition.

        Handles nested relationships using dot notation (e.g., "relation.target").
        For dotted fields, extracts target values from each item in the relation
        list and joins them with commas.

        Args:
            fields: Dictionary of field names to column definitions.
            row: Dictionary representing a single row of data.

        Returns:
            list: List of formatted column values for the row.
        """
        columns = []
        for field in fields:
            if "." in field:
                relation, target = field.split(".")
                if row.get(relation):
                    # noinspection PyTypeChecker
                    row_field = [
                        self.__rich_field__(item.get(target, None)) for item in row.get(relation)
                    ]
                    columns.append(",".join(row_field))
                else:
                    columns.append("")
            else:
                columns.append(self.__rich_field__(row.get(field)))
        return columns

    def __rich_field__(self, field: Any) -> str | Any:
        """Format a field value for rich table output.

        Converts booleans to emoji representations, integers to strings,
        and None values to "N/A". Formats datetime and date values using
        the instance's datetime_format and date_format strings.

        Args:
            field: The field value to format.

        Returns:
            Formatted value suitable for table display.
        """
        if isinstance(field, bool):
            return convert_bool_to_emoji(field)
        if isinstance(field, int):
            return str(field)
        if isinstance(field, type(None)):
            return "N/A"
        if isinstance(field, datetime.datetime):
            return field.strftime(self.datetime_format)
        if isinstance(field, datetime.date):
            return field.strftime(self.date_format)
        return field


class ExceptionTable(CliTable):
    """Specialized table for displaying exception information.

    Displays error code, message, and traceback with red styling for
    exception visualization.
    """

    table_style = {
        "row_styles": ["none", "dim"],
        "border_style": "bright_red",
        "header_style": "bold red",
        "box": box.SQUARE_DOUBLE_HEAD,
    }

    fields = {
        "error_code": CliTableColumn(header="Error"),
        "message": CliTableColumn(header="Message"),
        "data": CliTableColumn(header="Traceback", justify="full"),
    }

    def __init__(self, columns: dict):
        """Initialize the exception table with error data.

        Args:
            columns: Dictionary containing error_code, message, and data keys.
        """
        super().__init__(fields=self.fields, rows=columns, table_style=self.table_style)
