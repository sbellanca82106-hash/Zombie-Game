"""Compatibility wrapper; connection.py is the canonical DB config."""

from connection import database_connect

__all__ = ["database_connect"]
