"""Commands for the Tasks app."""

from .add import add
from .complete import complete
from .delete import delete
from .list import list
from .show import show
from .sync import sync

commands = [add, complete, delete, list, show, sync]
