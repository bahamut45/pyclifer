from pyclif import Response, command, option

from ....core.context import pass_demo_context
from ..interfaces import TaskInterface


@command()
@option(
    "--source",
    default="https://remote.example.com/tasks",
    help="URL of the remote task source. Supports embedded credentials.",
)
@pass_demo_context
def sync(ctx, source) -> Response:
    """Sync tasks from a remote source."""
    return TaskInterface(ctx).respond("sync_tasks", source=source)
