"""Tasks app group."""

from pyclif import group

from .commands import commands

subgroups = []


@group()
def tasks():
    """Tasks group."""


for grp in subgroups:
    tasks.add_command(grp)

for cmd in commands:
    tasks.add_command(cmd)
