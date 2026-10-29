"""Compatibility wrapper: older scripts import database_connect from here.

It re-exports connection.database_connect so every script uses the same
defaults (including the password) instead of a second, different copy.
"""

from connection import database_connect

__all__ = ["database_connect"]
