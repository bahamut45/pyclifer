"""pyclifer project add integration <name>."""

from pyclifer import Response, argument, command, option, pass_context

from ...interfaces import ScaffoldingInterface


@command()
@argument("name")
@option(
    "--package", is_flag=True, default=False, help="Generate a package instead of a single file."
)
@pass_context
def integration(ctx, name: str, package: bool) -> Response:
    """Add an integration to the current project."""
    return ScaffoldingInterface(ctx).respond("add_integration", name, package=package)
