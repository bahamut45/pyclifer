"""Demo app group."""

from pyclif import group

from .commands import commands

subgroups = []


@group()
def demo():
    """Demo group."""


for grp in subgroups:
    demo.add_command(grp)

for cmd in commands:
    demo.add_command(cmd)
