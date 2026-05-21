from pyclif import Response, command

from ....core.context import pass_cli_context
from ..interfaces import TasksInterface


@command()
@pass_cli_context
def delete(ctx) -> Response:
    """Delete description."""
    return TasksInterface(ctx).respond("delete")
