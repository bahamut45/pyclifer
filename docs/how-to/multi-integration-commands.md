# Multi-integration Commands

Some commands coordinate two or more interfaces — for example, validating a user exists before
creating a task assigned to them, or provisioning a resource and immediately registering it
elsewhere.

The key is knowing when to call `respond()` and when to call an interface method directly.

## respond() vs direct method calls

`respond()` is a one-shot helper: one method, one renderer, one `Response`. When you need
results from several interfaces, call their methods directly — each returns a plain
`list[OperationResult]` — then aggregate with `Response.from_results()`.

```
respond("method")          →  calls method, wraps in Response, attaches renderer
interface.method()         →  just calls the method, returns list[OperationResult]
Response.from_results([])  →  builds a Response from a combined list
```

## Pattern 1 — Sequential with guard

Validate a precondition with the first interface. If it fails, return early without calling
the second interface.

**Scenario**: add a task and assign it to a user, but reject the command if the assignee does
not exist.

```python
# tasks/commands/add_assigned.py
from pyclif import Response, command, option
from ..context import pass_my_context
from ..interfaces import TaskInterface
from ...users.interfaces import UserInterface
from ...users.renderers import UserNotFoundRenderer


@command()
@option("--title", required=True, help="Task title.")
@option("--assignee", required=True, help="Username to assign the task to.")
@pass_my_context
def add_assigned(ctx, title: str, assignee: str) -> Response:
    """Add a task and assign it to an existing user."""
    # Step 1 — validate the assignee exists
    user_results = UserInterface(ctx).list_users()
    known = {r.item for r in user_results if r.success}
    if assignee not in known:
        return Response.from_results(
            [next(r for r in user_results if r.item == assignee or not r.success)],
            failure_message=f"User '{assignee}' not found.",
            renderer=UserNotFoundRenderer(),
        )

    # Step 2 — create the task (user is confirmed to exist)
    return TaskInterface(ctx).respond("add_task", title=title, assignee=assignee)
```

Call `interface.method()` directly to get the raw `list[OperationResult]` without building
a `Response`. Inspect the results, then decide whether to proceed or return early.

## Pattern 2 — Sequential with aggregation

Run both interfaces and combine their results into a single `Response` that reflects the
overall outcome.

**Scenario**: provision a new user — create the user record and immediately create a
welcome task assigned to them. Both operations appear in the final output.

```python
# users/commands/provision.py
from pyclif import Response, command, option
from ..context import pass_my_context
from ..interfaces import UserInterface
from ...tasks.interfaces import TaskInterface
from .renderers import ProvisionRenderer


@command()
@option("--username", required=True, help="New username.")
@option("--email", required=True, help="User e-mail address.")
@pass_my_context
def provision(ctx, username: str, email: str) -> Response:
    """Create a user and assign them a welcome task."""
    user_results = UserInterface(ctx).create_user(username=username, email=email)

    task_results = []
    if all(r.success for r in user_results):
        task_results = TaskInterface(ctx).add_task(
            title=f"Welcome, {username}!",
            assignee=username,
        )

    return Response.from_results(
        user_results + task_results,
        success_message=f"User '{username}' provisioned.",
        failure_message=f"Provisioning '{username}' failed.",
        renderer=ProvisionRenderer(),
    )
```

`Response.from_results()` sets `success=True` only if every result in the combined list
succeeded. `error_code` is taken from the first failure.

## Handling partial failures

When some operations succeed and others fail, `from_results()` marks the overall response as
failed but preserves all results in `data["results"]`. The renderer and output format both
receive the full list — the table will show successes and failures side by side.

```python
user_results = UserInterface(ctx).create_user(username=username, email=email)
task_results = TaskInterface(ctx).add_task(title="Welcome!", assignee=username)

all_results = user_results + task_results
# success=False if any result failed; error_code from first failure
return Response.from_results(all_results, renderer=ProvisionRenderer())
```

To stop on the first failure instead of continuing:

```python
user_results = UserInterface(ctx).create_user(username=username, email=email)
if not all(r.success for r in user_results):
    return Response.from_results(user_results, renderer=ProvisionRenderer())

task_results = TaskInterface(ctx).add_task(title="Welcome!", assignee=username)
return Response.from_results(user_results + task_results, renderer=ProvisionRenderer())
```

## Keeping the renderer separate

The renderer passed to `Response.from_results()` controls how the combined results are
displayed. Define one renderer per command rather than reusing a domain renderer:

```python
# users/renderers.py
from pyclif import BaseRenderer


class ProvisionRenderer(BaseRenderer):
    fields = ["item", "success", "message"]
    columns = ["item", "success", "message"]
    success_message = "Provisioning complete."
    failure_message = "Provisioning failed."
```

The `item` field on each `OperationResult` carries a human-readable identifier (username,
task ID, file path, …). Using `["item", "success", "message"]` as columns gives a readable
summary across heterogeneous results from different interfaces.

## Interfaces used in the examples

The demo app ships `TaskInterface` and `UserInterface` as independent building blocks:

- [`tasks/interfaces.py`](https://github.com/bahamut45/pyclif/blob/main/src/pyclif/apps/demo/apps/tasks/interfaces.py)
- [`users/interfaces.py`](https://github.com/bahamut45/pyclif/blob/main/src/pyclif/apps/demo/apps/users/interfaces.py)

## See also

- [Response Patterns](response-patterns.md) — the single-interface baseline
- [Error Handling](error-handling.md) — `OperationResult.error()` and failure patterns
- [API — Interfaces](../api/interfaces.md) — `respond()` and `from_results()` internals