"""Shared constants and Click choice types for the demo app."""

from pyclif import Choice

PRIORITIES = ["low", "medium", "high"]
STATUSES = ["open", "in_progress", "done"]

PRIORITY_CHOICE = Choice(PRIORITIES)
STATUS_CHOICE = Choice(STATUSES)
