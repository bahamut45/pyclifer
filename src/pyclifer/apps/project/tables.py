"""Table definitions for project scaffolding output."""

from rich import box

from pyclifer import CliTable, CliTableColumn, Response


class ScaffoldingTable(CliTable):
    """Table displaying files created or modified by a scaffolding command."""

    _ACTION_LABEL = {
        "created": ":sparkles:  created",
        "modified": ":pencil2:  modified",
    }

    fields = {
        "file": CliTableColumn(header="File"),
        "action": CliTableColumn(header="Action", style="bold green"),
    }

    def __init__(self, response: Response):
        """Initialize the scaffolding table from a command response.

        Args:
            response: The scaffolding command response carrying a list of
                OperationResult under data["results"].
        """
        results = response.data.get("results", [])
        rows = []
        for r in results:
            if r.success:
                action_raw = r.data.get("action", "") if isinstance(r.data, dict) else ""
                rows.append(
                    {"file": r.item, "action": self._ACTION_LABEL.get(action_raw, action_raw)}
                )
            else:
                rows.append({"file": r.item, "action": f":x:  {r.message}"})

        succeeded = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)
        parts = []
        if succeeded:
            parts.append(f"{succeeded} file{'s' if succeeded != 1 else ''} touched")
        if failed:
            parts.append(f"{failed} error{'s' if failed != 1 else ''}")
        caption = ", ".join(parts) if parts else "nothing done"

        super().__init__(
            fields=self.fields,
            rows=rows,
            table_style={
                "title": response.message,
                "caption": caption,
                "show_lines": True,
                "box": box.ROUNDED,
            },
        )
