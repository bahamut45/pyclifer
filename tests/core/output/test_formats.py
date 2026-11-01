"""Tests for the output format names."""

import pytest

from pyclifer.core.output.formats import OUTPUT_FORMATS, validate_output_format


class TestOutputFormats:
    """The single list of formats a pyclifer application can answer in."""

    def test_the_list_holds_the_six_formats_in_a_stable_order(self):
        assert OUTPUT_FORMATS == ("json", "yaml", "table", "rich", "raw", "text")

    @pytest.mark.parametrize("output_format", OUTPUT_FORMATS)
    def test_every_listed_format_is_accepted(self, output_format):
        validate_output_format(output_format)

    def test_an_unknown_format_is_rejected_with_the_valid_ones(self):
        with pytest.raises(ValueError, match=r"'xml'.*json, yaml, table, rich, raw, text"):
            validate_output_format("xml")

    def test_the_error_names_the_value_as_asked(self):
        with pytest.raises(ValueError, match="Unknown output_format_default 'xml'"):
            validate_output_format("xml", "output_format_default")
