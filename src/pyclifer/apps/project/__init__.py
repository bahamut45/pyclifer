"""Project scaffolding app — `pyclifer project` command group."""

from pyclifer import group

from .commands import commands


@group()
def project():
    """Scaffold and manage pyclifer projects."""


for command in commands:
    project.add_command(command)
