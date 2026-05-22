from pyclif import Response, argument, command

from ....core.context import pass_demo_context
from ..interfaces import TaskInterface


@command()
@argument("task_id")
@pass_demo_context
def show(ctx, task_id) -> Response:
    """Show details of a specific task."""
    return TaskInterface(ctx).respond("show_task", task_id=task_id)
