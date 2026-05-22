from pyclif import Response, command, output_filter_option

from ....core.context import pass_demo_context
from ..interfaces import UserInterface


@command()
@output_filter_option()
@pass_demo_context
def list(ctx) -> Response:
    """List all users."""
    return UserInterface(ctx).respond("list_users")
