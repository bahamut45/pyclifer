from pyclif import Response, argument, command

from ....core.context import pass_demo_context
from ..interfaces import TaskInterface


@command()
@argument("task_id")
@pass_demo_context
def complete(ctx, task_id) -> Response:
    """Mark a task as done."""
    return TaskInterface(ctx).respond("complete_task", task_id=task_id)
