"""Core module for pyclifer — decorator-driven CLI framework.

Exports:
    app_group: Decorator for the main application entry point.
    group: Decorator for creating command subgroups.
    command: Decorator for creating commands.
    option: Decorator for creating options with global propagation support.
"""

from .classes import CustomConfigOption, PycliferGroup, PycliferOption
from .decorators import app_group, command, group, option, output_filter_option, returns_response

__all__ = [
    "app_group",
    "group",
    "command",
    "option",
    "output_filter_option",
    "returns_response",
    "PycliferGroup",
    "PycliferOption",
    "CustomConfigOption",
]
