from pyclif import DateTime, Response, command, option

from ....core.constants import PRIORITY_CHOICE
from ....core.context import pass_demo_context
from ..interfaces import TaskInterface


@command()
@option("--title", required=True, help="Task title.")
@option("--description", default="", help="Task description.")
@option("--priority", type=PRIORITY_CHOICE, default="medium", help="Task priority.")
@option("--due", type=DateTime(formats=["%Y-%m-%d"]), default=None, help="Due date (YYYY-MM-DD).")
@option("--tags", default="", help="Comma-separated list of tags.")
@option("--assignee", default="", help="Assignee username.")
@pass_demo_context
def add(ctx, title, description, priority, due, tags, assignee) -> Response:
    """Add a new task."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    return TaskInterface(ctx).respond(
        "add_task",
        title=title,
        description=description,
        priority=priority,
        due_date=due.date() if due else None,
        tags=tag_list,
        assignee=assignee,
    )
