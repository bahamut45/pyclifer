"""Folder apps in cli"""

# Import each group here so cli.py can wire them with add_command.
# Updated automatically by `pyclif project add app`.
from .demo import demo
from .project import project

groups = [project, demo]
