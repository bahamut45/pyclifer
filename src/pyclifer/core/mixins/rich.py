"""Mixins for CLI context providing reusable functionalities."""

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.rule import Rule
from rich.status import Status


class RichHelpersMixin:
    """Provide rich console helper methods for CLI contexts.

    This mixin expects the inheriting class to have a 'console' attribute
    instantiated with a rich.console.Console object.
    """

    console: Console

    def rich_panel(
        self,
        text: Any,
        title: str | None = None,
        border_style: str | None = None,
        padding: tuple = (0, 1),
        console_print: bool = False,
        fit: bool = False,
    ) -> Panel:
        """Create a rich panel with the given formatting options.

        Args:
            text: The text content or renderable of the panel.
            title: The title of the panel.
            border_style: The border style of the panel.
            padding: The padding of the panel (top/bottom, left/right).
            console_print: If True, prints the panel directly to the console.
            fit: If True, the panel fits its contents.

        Returns:
            The rendered rich panel object.
        """
        panel_class = Panel.fit if fit else Panel
        panel_kwargs: dict[str, Any] = {"renderable": text, "title": title, "padding": padding}
        if border_style is not None:
            panel_kwargs["border_style"] = border_style
        renderer = panel_class(**panel_kwargs)
        if console_print:
            self.console.print(renderer)  # type: ignore
        return renderer

    def display_rule(self, title: str = "", style: str = "blue") -> None:
        """Display a horizontal rule with an optional title.

        Args:
            title: The text to display in the middle of the rule.
            style: The color and style of the rule.
        """
        self.console.print(Rule(title=title, style=style))  # type: ignore

    def show_status(self, message: str = "Processing...", spinner: str = "dots") -> Status:
        """Return a rich status context manager for long-running tasks.

        Args:
            message: The message to display next to the spinner.
            spinner: The type of spinner animation to use.

        Returns:
            Status: A context manager for the status.
        """
        return self.console.status(message, spinner=spinner)  # type: ignore

    def ask_user(
        self,
        question: str,
        default: str | None = None,
        choices: list[str] | None = None,
        password: bool = False,
    ) -> Any:
        """Prompt the user for input.

        Args:
            question: The prompt text to display.
            default: The default value if the user presses enter.
            choices: A list of valid choices to restrict input.
            password: If True, hides the user's input.

        Returns:
            The user's input.
        """
        return Prompt.ask(
            question, default=default, choices=choices, password=password, console=self.console
        )  # type: ignore

    def ask_confirmation(self, question: str, default: bool = False) -> bool:
        """Ask the user a yes or no confirmation question.

        Args:
            question: The prompt text to display.
            default: The default answer if the user presses enter.

        Returns:
            bool: True if the user confirmed, False otherwise.
        """
        return Confirm.ask(question, default=default, console=self.console)  # type: ignore
