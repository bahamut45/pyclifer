"""BaseInterface — service layer base class for pyclifer applications."""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, ClassVar

from pyclifer.core.output.renderer import BaseRenderer

if TYPE_CHECKING:
    from pyclifer.core.output.responses import Response


class BaseInterface:
    """Base class for pyclifer service-layer interfaces.

    Subclass and declare a renderers dict to associate each method with its
    renderer. Call respond() from commands — it handles list vs generator
    detection, renderer selection, and Response construction automatically.

    Class attributes:
        renderers: Maps method names to renderer classes. Missing keys fall
            back to renderer_class.
        renderer_class: Default renderer is used when a method has no entry in
            renderers.

    Example:
        class ArticleInterface(BaseInterface):
            renderers = {
                "list": ArticleListRenderer,
                "create": ArticleCreateRenderer,
            }

            def list(self) -> list[OperationResult]:
                ...

            def create(self, title: str) -> list[OperationResult]:
                ...
    """

    renderers: ClassVar[dict[str, type[BaseRenderer]]] = {}
    renderer_class: ClassVar[type[BaseRenderer]] = BaseRenderer

    def __init__(self, ctx: object) -> None:
        """Store the CLI context for use in interface methods.

        Args:
            ctx: The pyclifer CLI context passed from the command.
        """
        self.ctx = ctx

    def respond(self, method_name: str, *args: object, **kwargs: object) -> Response:
        """Call a method and wrap its output in a Response with the right renderer.

        Auto-detects whether the method returns a list or a generator and
        picks from_results() vs from_stream() accordingly.

        An AttributeError raised by getattr is intentionally not caught —
        a wrong method_name is a programming error, not a business failure.

        Args:
            method_name: Name of an interface method to call.
            *args: Positional arguments forwarded to the method.
            **kwargs: Keyword arguments forwarded to the method.

        Returns:
            A Response ready for the framework to dispatch to the renderer.
        """
        # Lazy import — breaks the circular dependency between interfaces/base.py
        # and output/responses.py (Response imports nothing from interfaces, but
        # keeping this at module level would require responses.py to import
        # BaseInterface which would close the cycle).
        from pyclifer.core.output.responses import Response  # noqa: PLC0415

        method = getattr(self, method_name)
        renderer_cls = self.renderers.get(method_name, self.renderer_class)
        renderer = renderer_cls()
        result = method(*args, **kwargs)

        if inspect.isgenerator(result):
            return Response.from_stream(result, renderer=renderer)

        return Response.from_results(
            result,
            success_message=renderer.get_success_message(result),
            failure_message=renderer.get_failure_message(result),
            renderer=renderer,
        )
