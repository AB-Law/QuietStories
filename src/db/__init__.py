"""
Database package for QuietStories.

This package provides SQLite-based persistence for scenarios and sessions.
"""

from .manager import DatabaseManager

__all__ = ['DatabaseManager']
