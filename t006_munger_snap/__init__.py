"""Munger Snap utilities."""

from .logic import FilterResult, Snapshot, four_filters

__all__ = ["FilterResult", "Snapshot", "four_filters", "create_app"]


def create_app():
    """Factory wrapper that defers the Flask import."""
    from .app import create_app as _create_app

    return _create_app()
