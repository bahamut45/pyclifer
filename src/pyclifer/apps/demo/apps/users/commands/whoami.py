from pyclifer import Response, command

from ....core.context import pass_demo_context
from ..interfaces import UserInterface


@command()
@pass_demo_context
def whoami(ctx) -> Response:
    """Show the current user profile."""
    return UserInterface(ctx).respond("whoami")
