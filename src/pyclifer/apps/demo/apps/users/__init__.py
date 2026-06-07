"""Users app group."""

from pyclifer import group

from .commands import commands

subgroups = []


@group()
def users():
    """Users group."""


for grp in subgroups:
    users.add_command(grp)

for cmd in commands:
    users.add_command(cmd)
