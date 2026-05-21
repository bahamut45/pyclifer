"""pyclif project add group <name> --app <app>."""

from pyclif import Response, argument, command, option, pass_context

from ...interfaces import ScaffoldingInterface


@command()
@argument("name")
@option("--app", "app_name", required=True, help="App that owns this group.")
@pass_context
def group_(ctx, name: str, app_name: str) -> Response:
    """Add a subgroup to an existing app."""
    return ScaffoldingInterface(ctx).respond("add_group", name, app_name)
