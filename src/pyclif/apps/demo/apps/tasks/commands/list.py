from pyclif import (
    PaginatedResponse,
    Response,
    command,
    option,
    output_filter_option,
    pagination_options,
)

from ....core.constants import PRIORITY_CHOICE, STATUS_CHOICE
from ....core.context import pass_demo_context
from ..interfaces import TaskInterface


@command()
@pagination_options()
@output_filter_option()
@option("--status", type=STATUS_CHOICE, default=None, help="Filter by status.")
@option("--priority", type=PRIORITY_CHOICE, default=None, help="Filter by priority.")
@pass_demo_context
def list(ctx, status, priority) -> Response:
    """List all tasks with optional filtering and pagination."""
    response = TaskInterface(ctx).respond("list_tasks", status=status, priority=priority)
    page = ctx.click.meta.get("pyclif.page", 1)
    limit = ctx.click.meta.get("pyclif.limit", 20)
    results = response.data.get("results", [])
    total = len(results)
    start = (page - 1) * limit
    return PaginatedResponse(
        success=response.success,
        message=response.message,
        data={"results": results[start : start + limit]},
        error_code=response.error_code,
        renderer=response.renderer,
        page=page,
        limit=limit,
        total=total,
    )
