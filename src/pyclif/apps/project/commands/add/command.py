"""pyclif project add command <name> --app <app>."""

from pyclif import Response, argument, command, option, pass_context

from ...interfaces import ScaffoldingInterface


@command()
@argument("name")
@option(
    "--app",
    "app_name",
    required=True,
    help="App that owns this command. Use dotted notation for nested groups (e.g. demo.tasks).",
)
@pass_context
def command_(ctx, name: str, app_name: str) -> Response:
    """Add a command to an existing app."""
    return ScaffoldingInterface(ctx).respond("add_command", name, app_name)
