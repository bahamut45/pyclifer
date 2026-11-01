"""Tests for BaseRenderer's handling of the shape of Response.data."""

from unittest.mock import MagicMock

import pytest

from pyclifer.core.output.renderer import BaseRenderer
from pyclifer.core.output.responses import OperationResult, PaginatedResponse, Response


class ItemRenderer(BaseRenderer):
    """Renderer with declared fields, so serialize() reads the results itself."""

    fields = ["item"]
    columns = ["item"]


def _list_response() -> Response:
    """A response whose data is a list, which BaseRenderer cannot read results from."""
    return PaginatedResponse(success=True, message="m", data=[{"a": 1}])


class TestDataShape:
    """A renderer that needs data["results"] says so when data is not a dict."""

    MESSAGE = r"data must be a dict with a 'results' key.*got list"

    def test_serialize_rejects_list_data(self):
        with pytest.raises(ValueError, match=self.MESSAGE):
            ItemRenderer().serialize(_list_response())

    def test_table_rejects_list_data(self):
        with pytest.raises(ValueError, match=self.MESSAGE):
            ItemRenderer().table(_list_response())

    def test_first_result_helper_rejects_list_data(self):
        with pytest.raises(ValueError, match=self.MESSAGE):
            ItemRenderer()._first_result(_list_response(), MagicMock())

    def test_message_names_the_expected_shape(self):
        with pytest.raises(ValueError, match=r"\{'results': \[\.\.\.\]\}"):
            ItemRenderer().table(_list_response())

    def test_dict_data_still_renders(self):
        response = Response(success=True, message="m", data={"results": [OperationResult.ok("a")]})
        assert ItemRenderer().serialize(response)["data"]["results"][0]["item"] == "a"
        assert ItemRenderer().table(response).table.row_count == 1

    def test_dict_data_without_results_renders_no_row(self):
        response = Response(success=True, message="m", data={})
        assert ItemRenderer().table(response).table.row_count == 0
