"""Demo app group."""

from pyclif import group

from .apps.tasks import tasks
from .apps.users import users
from .commands import commands

subgroups = [tasks, users]


@group()
def demo():
    """Demo group."""


for grp in subgroups:
    demo.add_command(grp)

for cmd in commands:
    demo.add_command(cmd)
