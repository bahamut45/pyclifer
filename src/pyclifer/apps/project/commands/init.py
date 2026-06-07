"""pyclifer project init <name>."""

from pyclifer import Choice, Response, argument, command, option, pass_context

from ..interfaces import ScaffoldingInterface
from ..renderers import ScaffoldingRenderer


@command()
@argument("name")
@option(
    "--integrations",
    default="",
    help="Comma-separated integrations to scaffold (e.g. github,docker,slack).",
)
@option(
    "--package-manager",
    type=Choice(["uv", "poetry"], case_sensitive=False),
    default="uv",
    show_default=True,
    help="Package manager to target.",
)
@pass_context
def init(ctx, name: str, integrations: str, package_manager: str) -> Response:
    """Create a new pyclifer project skeleton."""

    def _stream():
        yield from ScaffoldingInterface(ctx).init_project(name, package_manager=package_manager)
        if integrations:
            from pathlib import Path  # noqa: PLC0415

            scoped = ScaffoldingInterface(ctx, root=Path(name))
            for integration in [i.strip() for i in integrations.split(",") if i.strip()]:
                yield from scoped.add_integration(integration)

    return Response.from_stream(_stream(), renderer=ScaffoldingRenderer(name=name))
