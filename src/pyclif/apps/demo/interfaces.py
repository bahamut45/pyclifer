"""Renderer and interface for the Demo app."""

from pyclif import BaseInterface, BaseRenderer

from .models import Demo


class DemoRenderer(BaseRenderer):
    """Output renderer for Demo commands."""

    model_class = Demo
    columns = ["item", "success"]
    success_message = "Demo operation completed."
    failure_message = "Demo operation failed."


class DemoInterface(BaseInterface):
    """Interface for Demo business logic."""

    renderers = {
        # --- renderers --- (used by `pyclif project add command` — do not remove)
    }

    # --- commands --- (used by `pyclif project add command` — do not remove)
