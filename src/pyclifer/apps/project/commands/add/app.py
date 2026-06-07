"""pyclifer project add app <name>."""

from pyclifer import Response, argument, command, option, pass_context

from ...interfaces import ScaffoldingInterface


@command()
@argument("name")
@option(
    "--no-group",
    "flat",
    is_flag=True,
    default=False,
    help="Expose commands directly on the root app without a @group layer.",
)
@option(
    "--with-core",
    "with_core",
    is_flag=True,
    default=False,
    help="Generate a core/ directory with context, constants, and options modules.",
)
@pass_context
def app(ctx, name: str, flat: bool, with_core: bool) -> Response:
    """Add an app to the current project."""
    return ScaffoldingInterface(ctx).respond("add_app", name, flat=flat, with_core=with_core)
