from pyclif import Response, command

from ....core.context import pass_cli_context
from ..interfaces import UsersInterface


@command()
@pass_cli_context
def whoami(ctx) -> Response:
    """Whoami description."""
    return UsersInterface(ctx).respond("whoami")
