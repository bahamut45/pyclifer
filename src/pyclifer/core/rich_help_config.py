"""Default configuration for rich-click in pyclifer."""

from rich_click import RichHelpConfiguration


def get_default_pyclif_rich_config() -> "RichHelpConfiguration | None":
    """Return the default rich-click configuration for pyclifer.

    This configuration can be customized based on project needs.

    Returns:
        Default rich-click configuration or None if rich-click is unavailable.
    """
    return RichHelpConfiguration(  # type: ignore
        # Pyclif custom styles
        style_option="bold blue",
        style_argument="bold blue",
        style_command="bold green",
        style_switch="bold cyan",
        style_usage="bold yellow",
        # Behaviors
        show_arguments=True,
        options_table_column_types=["required", "opt_short", "opt_long", "metavar", "help"],
        options_table_help_sections=["help", "deprecated", "envvar", "default", "required"],
        group_arguments_options=False,
        # Panels and tables
        style_options_panel_box="ROUNDED",
        style_commands_panel_box="ROUNDED",
        style_options_table_show_lines=False,
        style_commands_table_show_lines=False,
        # Custom text
        options_panel_title="Options",
        commands_panel_title="Commands",
        arguments_panel_title="Arguments",
        # Width and formatting
        max_width=100,
        text_markup="rich",
    )


def get_minimal_pyclif_rich_config() -> "RichHelpConfiguration | None":
    """Return a minimal rich-click configuration.

    Returns:
        Minimal rich-click configuration or None if rich-click is unavailable.
    """
    return RichHelpConfiguration(  # type: ignore
        style_option="cyan",
        style_command="green",
        show_arguments=False,
        text_markup="ansi",
    )


def get_verbose_pyclif_rich_config() -> "RichHelpConfiguration | None":
    """Return a verbose rich-click configuration.

    Returns:
        Verbose rich-click configuration or None if rich-click is unavailable.
    """
    return RichHelpConfiguration(  # type: ignore
        style_option="bold blue",
        style_command="bold green",
        show_arguments=True,
        options_table_column_types=["required", "opt_short", "opt_long", "metavar", "help"],
        options_table_help_sections=[
            "help",
            "deprecated",
            "envvar",
            "default",
            "required",
            "metavar",
        ],
        style_options_table_show_lines=True,
        text_markup="rich",
    )


# Predefined configurations
PYCLIFER_CONFIGS = {
    "default": get_default_pyclif_rich_config,
    "minimal": get_minimal_pyclif_rich_config,
    "verbose": get_verbose_pyclif_rich_config,
}


def get_rich_config(
    config_name_or_dict: "str | dict | RichHelpConfiguration | None",
) -> "RichHelpConfiguration | None":
    """Resolve rich-click configuration from different input types.

    Args:
        config_name_or_dict: Predefined config name, dict of options,
            RichHelpConfiguration instance, or None.

    Returns:
        Resolved rich-click configuration or None.

    Raises:
        ValueError: If the config name is unknown.
    """
    if config_name_or_dict is None:
        return PYCLIFER_CONFIGS["default"]()

    if isinstance(config_name_or_dict, str):
        # Predefined configuration
        if config_name_or_dict in PYCLIFER_CONFIGS:
            return PYCLIFER_CONFIGS[config_name_or_dict]()
        else:
            raise ValueError(
                f"Unknown configuration '{config_name_or_dict}'. "
                f"Available options: {list(PYCLIFER_CONFIGS.keys())}"
            )
    elif isinstance(config_name_or_dict, dict):
        # Configuration from a dictionary
        return RichHelpConfiguration(**config_name_or_dict)  # type: ignore
    else:
        # RichHelpConfiguration instance
        return config_name_or_dict
