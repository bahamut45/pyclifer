"""Demo app context and pass decorator."""

from pyclif import BaseContext, make_pass_decorator

from .storage import Storage


class DemoContext(BaseContext):
    """Extended context carrying the active Storage instance."""

    def __init__(self) -> None:
        """Initialize context with a lazy Storage placeholder."""
        super().__init__()
        self._storage: Storage | None = None

    @property
    def storage(self) -> Storage:
        """Return the lazily initialized Storage instance.

        Returns:
            The shared Storage for this context.
        """
        if self._storage is None:
            self._storage = Storage()
        return self._storage


pass_demo_context = make_pass_decorator(DemoContext, ensure=True)
