"""pyclifer project add command <names…> --app <app>."""

from pyclifer import Response, argument, command, option, pass_context

from ...interfaces import ScaffoldingInterface


@command()
@argument("names", nargs=-1, required=True)
@option(
    "--app",
    "app_name",
    required=True,
    help="App that owns these commands. Use dotted notation for nested groups (e.g. demo.tasks).",
)
@pass_context
def command_(ctx, names: tuple[str, ...], app_name: str) -> Response:
    """Add one or more commands to an existing app."""
    return ScaffoldingInterface(ctx).respond("add_commands", names, app_name)
