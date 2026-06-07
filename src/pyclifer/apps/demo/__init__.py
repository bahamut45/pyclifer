"""Demo app group."""

from pyclifer import group

from .apps.tasks import tasks
from .apps.users import users
from .commands import commands
from .core.context import pass_demo_context
from .core.options import project_option

subgroups = [tasks, users]


@group()
@project_option
@pass_demo_context
def demo(ctx):
    """Demo task manager — reference implementation of all pyclifer features."""


for grp in subgroups:
    demo.add_command(grp)

for cmd in commands:
    demo.add_command(cmd)
