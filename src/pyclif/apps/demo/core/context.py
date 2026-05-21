"""Demo app context."""

from pyclif import BaseContext, make_pass_decorator


class DemoContext(BaseContext):
    """Extended context for the demo app."""


pass_cli_context = make_pass_decorator(DemoContext, ensure=True)
