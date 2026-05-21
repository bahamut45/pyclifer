"""pyclif project add — subgroup for scaffolding additions."""

from pyclif import group

from .app import app
from .command import command_
from .group_cmd import group_
from .integration import integration


@group()
def add():
    """Add apps, commands, or integrations to the current project."""


add.add_command(app)
add.add_command(command_, name="command")
add.add_command(group_, name="group")
add.add_command(integration)
