from pyclif import Response, command

from ....core.context import pass_cli_context
from ..interfaces import TasksInterface


@command()
@pass_cli_context
def sync(ctx) -> Response:
    """Sync description."""
    return TasksInterface(ctx).respond("sync")
