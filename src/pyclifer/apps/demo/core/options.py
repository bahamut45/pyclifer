"""Global CLI options shared across all demo subcommands."""

from pyclifer import option

project_option = option(
    "--project",
    default="default",
    help="Project namespace to operate in.",
    is_global=True,
    show_envvar=True,
    store_in_meta=True,
)
