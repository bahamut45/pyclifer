from pyclif import group

from .commands import commands


@group()
def demo():
    """Demo group."""


for cmd in commands:
    demo.add_command(cmd)
