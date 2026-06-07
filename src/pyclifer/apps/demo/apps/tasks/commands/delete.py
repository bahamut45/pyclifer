from pyclifer import Abort, Response, argument, command, option

from ....core.context import pass_demo_context
from ..interfaces import TaskInterface


@command()
@argument("task_id")
@option("--yes", "-y", is_flag=True, default=False, help="Skip confirmation prompt.")
@pass_demo_context
def delete(ctx, task_id, yes) -> Response:
    """Delete a task permanently."""
    if not yes and not ctx.ask_confirmation(f"Delete task '{task_id}'?"):
        raise Abort()
    return TaskInterface(ctx).respond("delete_task", task_id=task_id)
