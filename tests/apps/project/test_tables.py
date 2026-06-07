"""Unit tests for ScaffoldingTable."""

from unittest.mock import MagicMock

from pyclifer import OperationResult
from pyclifer.apps.project.tables import ScaffoldingTable


def _make_response(results: list[OperationResult], message: str = "Project 'my-app' created."):
    """Build a mock Response carrying OperationResult entries."""
    response = MagicMock()
    response.message = message
    response.data = {"results": results}
    return response


class TestScaffoldingTable:
    """Test suite for ScaffoldingTable."""

    def test_created_action_has_sparkles(self) -> None:
        """Created files show the sparkles emoji label."""
        result = OperationResult.ok("a.py", data={"action": "created"})
        table = ScaffoldingTable(_make_response([result]))
        assert table.table.row_count == 1

    def test_modified_action_has_pencil(self) -> None:
        """Modified files show the pencil emoji label."""
        result = OperationResult.ok("a.py", data={"action": "modified"})
        table = ScaffoldingTable(_make_response([result]))
        assert table.table.row_count == 1

    def test_failed_result_shows_error_message(self) -> None:
        """Failed results show the error message in the action column."""
        result = OperationResult.error("a.py", "File already exists.", error_code=2)
        table = ScaffoldingTable(_make_response([result]))
        assert table.table.row_count == 1

    def test_title_from_response_message(self) -> None:
        """Table title matches the response message."""
        table = ScaffoldingTable(_make_response([], message="App 'repos' created."))
        assert table.table.title == "App 'repos' created."

    def test_caption_plural(self) -> None:
        """Caption uses plural form for more than one file."""
        results = [OperationResult.ok(f"f{i}.py", data={"action": "created"}) for i in range(3)]
        table = ScaffoldingTable(_make_response(results))
        assert table.table.caption == "3 files touched"

    def test_caption_singular(self) -> None:
        """Caption uses singular form for exactly one file."""
        result = OperationResult.ok("a.py", data={"action": "created"})
        table = ScaffoldingTable(_make_response([result]))
        assert table.table.caption == "1 file touched"

    def test_caption_shows_error_count(self) -> None:
        """Caption includes error count when some results failed."""
        results = [
            OperationResult.ok("a.py", data={"action": "created"}),
            OperationResult.error("b.py", "already exists", error_code=2),
        ]
        table = ScaffoldingTable(_make_response(results))
        assert "1 error" in table.table.caption

    def test_empty_results(self) -> None:
        """Empty results list produces a table with no rows."""
        table = ScaffoldingTable(_make_response([]))
        assert table.table.row_count == 0
