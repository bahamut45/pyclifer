from pyclif import Response, command

from ....core.context import pass_cli_context
from ..interfaces import UsersInterface


@command()
@pass_cli_context
def list(ctx) -> Response:
    """List description."""
    return UsersInterface(ctx).respond("list")
