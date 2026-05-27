"""Unit tests for the tables module in the output package."""

import datetime
import inspect

import pytest
from rich.table import Table

import pyclif.core.output.tables as tables_module
from pyclif.core.output.tables import (
    CliTable,
    CliTableColumn,
    ExceptionTable,
    convert_bool_to_emoji,
)


class TestUtilityFunctions:
    """Test suite for utility functions in the tables module."""

    def test_is_bool_is_removed(self) -> None:
        """is_bool was dead code — it must not be exported from the module."""
        assert not hasattr(tables_module, "is_bool"), (
            "is_bool should have been removed; it is always shadowed by bool() cast"
        )

    def test_convert_bool_to_emoji_true(self) -> None:
        """Test that True is converted to a green checkmark emoji."""
        result = convert_bool_to_emoji(True)
        assert result == "[green]:heavy_check_mark:[/]"

    def test_convert_bool_to_emoji_false(self) -> None:
        """Test that False is converted to a red cross emoji."""
        result = convert_bool_to_emoji(False)
        assert result == "[red]:heavy_multiplication_x:[/]"

    def test_convert_bool_to_emoji_returns_str(self) -> None:
        """convert_bool_to_emoji always returns str, never the original object."""
        assert isinstance(convert_bool_to_emoji(True), str)
        assert isinstance(convert_bool_to_emoji(False), str)


class TestCliTableColumn:
    """Test suite for the CliTableColumn class."""

    def test_to_dict_includes_only_set_values(self) -> None:
        """Test that to_dict returns a dictionary without default or private values."""
        column = CliTableColumn(header="Username", justify="center", style="blue")
        col_dict = column.to_dict()

        assert "header" in col_dict
        assert col_dict["header"] == "Username"
        assert "justify" in col_dict
        assert col_dict["justify"] == "center"
        assert "style" in col_dict
        assert col_dict["style"] == "blue"

        assert "no_wrap" not in col_dict
        assert not any(key.startswith("_") for key in col_dict)


class TestCliTable:
    """Test suite for the CliTable class."""

    @pytest.fixture
    def sample_fields(self) -> dict:
        """Provide a sample dictionary of field definitions.

        Returns:
            dict: A dictionary mapping field keys to CliTableColumn instances.
        """
        return {
            "id": CliTableColumn(header="ID"),
            "name": CliTableColumn(header="Name"),
            "active": CliTableColumn(header="Active Status"),
            "roles.name": CliTableColumn(header="Roles"),
        }

    def test_table_method_is_removed(self) -> None:
        """table() method shadows the self.table attribute — it must not exist on the class."""
        assert not inspect.isfunction(CliTable.__dict__.get("table")), (
            "table() method should be removed; it is unreachable after __init__ sets self.table"
        )

    def test_initialization(self, sample_fields: dict) -> None:
        """Test that CliTable initializes correctly with given styles and columns."""
        rows = [{"id": 1, "name": "Alice", "active": True}]
        custom_style = {"border_style": "red"}

        cli_table = CliTable(fields=sample_fields, rows=rows, table_style=custom_style)

        assert isinstance(cli_table.table, Table)
        assert cli_table.table.border_style == "red"
        assert len(cli_table.table.columns) == 4
        assert len(cli_table.table.rows) == 1

    def test_rich_property_with_data(self, sample_fields: dict) -> None:
        """Test that __rich__ returns the table instance when rows are present."""
        rows = [{"id": 1, "name": "Alice"}]
        cli_table = CliTable(fields=sample_fields, rows=rows)

        assert cli_table.__rich__() is cli_table.table

    def test_rich_property_without_data(self, sample_fields: dict) -> None:
        """Test that __rich__ returns a placeholder string when no rows exist."""
        cli_table = CliTable(fields=sample_fields, rows=[])

        assert cli_table.__rich__() == "[i]No dataset available.[/i]"

    def test_update_rows_with_none_is_noop(self, sample_fields: dict) -> None:
        """update_rows with rows=None skips row addition (127→exit)."""
        cli_table = CliTable(fields=sample_fields, rows=[])
        cli_table.update_rows(sample_fields, None)
        assert cli_table.table.row_count == 0

    def test_update_rows_with_single_dict(self, sample_fields: dict) -> None:
        """Test that update_rows correctly processes a single dictionary."""
        cli_table = CliTable(fields=sample_fields, rows=[])
        cli_table.update_rows(sample_fields, {"id": 2, "name": "Bob"})

        assert len(cli_table.table.rows) == 1

    def test_generate_columns_standard_fields(self, sample_fields: dict) -> None:
        """Test formatting of standard fields including booleans, integers, and strings."""
        cli_table = CliTable(fields=sample_fields, rows=[])
        row_data = {"id": 42, "name": "Charlie", "active": False}

        columns = cli_table._generate_columns(sample_fields, row_data)

        assert columns[0] == "42"
        assert columns[1] == "Charlie"
        assert columns[2] == "[red]:heavy_multiplication_x:[/]"
        assert columns[3] == ""

    def test_generate_columns_dotted_relation(self, sample_fields: dict) -> None:
        """Test formatting of nested list fields using dotted notation."""
        cli_table = CliTable(fields=sample_fields, rows=[])
        row_data = {
            "id": 1,
            "name": "Diana",
            "roles": [{"name": "Admin"}, {"name": "User"}, {"other": "value"}],
        }

        columns = cli_table._generate_columns(sample_fields, row_data)

        assert columns[3] == "Admin,User,N/A"

    def test_rich_field_formatting(self, sample_fields: dict) -> None:
        """Test the __rich_field__ instance method for all supported data types."""
        t = CliTable(fields=sample_fields, rows=[])
        assert t.__rich_field__(True) == "[green]:heavy_check_mark:[/]"
        assert t.__rich_field__(False) == "[red]:heavy_multiplication_x:[/]"
        assert t.__rich_field__(123) == "123"
        assert t.__rich_field__(None) == "N/A"
        assert t.__rich_field__("Plain String") == "Plain String"
        assert t.__rich_field__(datetime.datetime(2024, 6, 1, 14, 30)) == "2024-06-01 14:30"
        assert t.__rich_field__(datetime.date(2024, 6, 1)) == "2024-06-01"

    def test_rich_field_custom_formats(self, sample_fields: dict) -> None:
        """Test that datetime_format and date_format are honoured."""
        t = CliTable(
            fields=sample_fields,
            rows=[],
            datetime_format="%d/%m/%Y %H:%M",
            date_format="%d/%m/%Y",
        )
        assert t.__rich_field__(datetime.datetime(2024, 6, 1, 14, 30)) == "01/06/2024 14:30"
        assert t.__rich_field__(datetime.date(2024, 6, 1)) == "01/06/2024"


class TestExceptionTable:
    """Test suite for the ExceptionTable class."""

    def test_initialization_with_error_data(self) -> None:
        """Test that ExceptionTable initializes correctly with exception info."""
        error_data = {
            "error_code": "ConnectionError",
            "message": "Failed to connect to the server",
            "data": "Traceback details...",
        }

        exception_table = ExceptionTable(columns=error_data)

        assert isinstance(exception_table.table, Table)
        assert exception_table.table.border_style == "bright_red"

        columns = exception_table.table.columns
        assert len(columns) == 3
        assert columns[0].header == "Error"
        assert columns[1].header == "Message"
        assert columns[2].header == "Traceback"

        assert len(exception_table.table.rows) == 1

    def test_exception_table_handles_missing_fields(self) -> None:
        """Test ExceptionTable behavior when some fields are missing."""
        error_data = {
            "error_code": "ValueError",
        }

        exception_table = ExceptionTable(columns=error_data)

        assert len(exception_table.table.rows) == 1

        columns = exception_table._generate_columns(exception_table.fields, error_data)
        assert columns[0] == "ValueError"
        assert columns[1] == "N/A"
        assert columns[2] == "N/A"
